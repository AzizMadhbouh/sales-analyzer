import json
import os
import re
import urllib.error
import urllib.request

SEVERITY_LEVELS = ("Low", "Medium", "High", "Critical")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
PROVIDER = os.environ.get("SEVERITY_LLM_PROVIDER", "ollama")  # ollama | gemini | none | auto

_POLICY_PATH = os.path.join(os.path.dirname(__file__), "severity_policy.json")
_POLICY = json.load(open(_POLICY_PATH, encoding="utf-8"))
_ROOT_CAUSE_BASELINES = _POLICY["root_cause_baselines"]
_PYLINT_MAP = _POLICY["tool_codes"]["pylint"]
_FLAKE8_MAP = _POLICY["tool_codes"]["flake8"]
_DOWNGRADE_SIGNALS = tuple(_POLICY["signals"]["downgrade"].keys())
_UPGRADE_SIGNALS = tuple(_POLICY["signals"]["upgrade"].keys())
_SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

_BANDIT_SEV = re.compile(r"Severity:\s*(Low|Medium|High|Undefined)", re.IGNORECASE)
_PREFIX_RE = re.compile(r"^\s*(?:[\w./\\-]+):\d+(?::\d+)?:\s*([A-Z])\d{3,4}(?::|\s)", re.IGNORECASE)
_PYLINT_SUFFIX = re.compile(r"\([a-z0-9-]+\)\s*$", re.IGNORECASE)

_SYSTEM_PROMPT = (
    "You score the operational severity of a CI/CD build job that failed."
    " You receive the predicted ROOT CAUSE plus a block of evidence log lines."
    " Return ONLY a JSON object with two keys:\n"
    '  {"severity": "Low"|"Medium"|"High"|"Critical", "reason": "<one short sentence>"}\n'
    "Rubric:\n"
    '- Low: cosmetic/warning-level issue, build continues; e.g. lint style notes, deprecation, flaky retry.\n'
    '- Medium: partial failure or transient problem that blocks a step but not the whole system; '
    "e.g. test flake, timeout with retry, warning that needs attention.\n"
    '- High: a real failure requiring a fix; e.g. compile/test/build failure, dependency install error, '
    "deployment error, auth/permission failure.\n"
    '- Critical: outage, security breach, data loss, production impact, leaked secret, disk full, '
    "fatal/crash of the whole pipeline or service.\n"
    "When in doubt prefer the boundary that the log text itself shows."
)


def _tool_severity(line):
    m = _BANDIT_SEV.search(line)
    if m:
        s = m.group(1).capitalize()
        return 'Medium' if s == 'Undefined' else s
    if line.lstrip().startswith('>> Issue:'):
        return 'Low'
    m = _PREFIX_RE.search(line)
    if m:
        code = m.group(1).upper()
        table = _PYLINT_MAP if _PYLINT_SUFFIX.search(line) else _FLAKE8_MAP
        return table.get(code)
    return None


def policy_severity(root_cause, text):
    """Deterministic fallback: tool code > upgrade/downgrade signal > root-cause baseline.
    `text` is the flattened evidence block (or a single line)."""
    tool = _tool_severity(text)
    if tool:
        return tool
    lower = text.lower()
    baseline = _ROOT_CAUSE_BASELINES.get(root_cause, "Medium")
    if any(s in lower for s in _UPGRADE_SIGNALS):
        return "Critical"
    if any(s in lower for s in _DOWNGRADE_SIGNALS):
        lowered = "Medium" if _SEVERITY_RANK[baseline] > _SEVERITY_RANK["Medium"] else baseline
        return lowered
    return baseline


def _user_text(root_cause, evidence):
    return f"root cause: {root_cause}\n\nevidence log lines:\n{evidence}"


def _gemini_body(root_cause, evidence, force_json):
    cfg = {"temperature": 0, "maxOutputTokens": 200}
    if force_json:
        cfg["responseMimeType"] = "application/json"
    return {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": _user_text(root_cause, evidence)}]}],
        "generationConfig": cfg,
    }


def _call_gemini(root_cause, evidence, api_key, model, timeout):
    url = f"{GEMINI_URL}/{model}:generateContent?key={api_key}"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(_gemini_body(root_cause, evidence, True)).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code != 400:  # 400: model may not support JSON mode -> retry without it
            raise
        req = urllib.request.Request(
            url,
            data=json.dumps(_gemini_body(root_cause, evidence, False)).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    candidates = data.get("candidates", []) or []
    if not candidates:
        raise RuntimeError("no candidates: " + json.dumps(data)[:200])
    return "".join(p.get("text", "") for p in candidates[0]["content"]["parts"])


def _parse_severity(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None, None
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        m = re.search(r'"(severity)"\s*:\s*"(\w+)"', text)
        if not m:
            return None, None
        return m.group(2), None
    sev = obj.get("severity")
    return (sev, obj.get("reason")) if sev in SEVERITY_LEVELS else (None, obj.get("reason"))


def _ollama_up(host, timeout=1.5):
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _call_ollama(root_cause, evidence, model, timeout):
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_text(root_cause, evidence)},
        ],
    }
    req = urllib.request.Request(
        OLLAMA_HOST + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["message"]["content"]


def _try_llm(root_cause, evidence, timeout):
    """Try providers in order, raising on total failure. Returns (severity, reason, provider)."""
    provider = PROVIDER
    if provider == "none":
        raise RuntimeError("SEVERITY_LLM_PROVIDER=none (disabled)")
    if provider == "ollama":
        return *_parse_severity(_call_ollama(root_cause, evidence, OLLAMA_MODEL, timeout)), "ollama"
    if provider == "gemini":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set")
        return *_parse_severity(_call_gemini(root_cause, evidence, key, GEMINI_MODEL, timeout)), "gemini"
    # auto: local Ollama first (free, no rate limits), then Gemini free tier, then policy
    if _ollama_up(OLLAMA_HOST):
        return *_parse_severity(_call_ollama(root_cause, evidence, OLLAMA_MODEL, timeout)), "ollama"
    if os.environ.get("GEMINI_API_KEY"):
        key = os.environ["GEMINI_API_KEY"]
        return *_parse_severity(_call_gemini(root_cause, evidence, key, GEMINI_MODEL, timeout)), "gemini"
    raise RuntimeError("no LLM available (no Ollama, no GEMINI_API_KEY)")


def classify_severity(root_cause, evidence, api_key=None, model=None, timeout=120):
    """LLM severity (local Ollama first = free, unlimited; Gemini free tier optional),
    deterministic policy as final fallback. Returns (severity, source, reason).
    `root_cause` is the predicted root cause; `evidence` a text block of error lines."""
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
    if model:
        os.environ["OLLAMA_MODEL"] = model
        os.environ["GEMINI_MODEL"] = model
    try:
        sev, reason, provider = _try_llm(root_cause, evidence, timeout)
        if sev is not None:
            return sev, provider, reason or ""
        return policy_severity(root_cause, evidence), "policy", "unparseable LLM output"
    except Exception as e:
        return policy_severity(root_cause, evidence), "policy", f"llm error: {type(e).__name__}: {e}"