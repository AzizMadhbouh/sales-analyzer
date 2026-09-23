"""Feed ALL Jenkins builds (past + present) into Postgres for Grafana.

Pulls each build's metadata (build.xml) and archived output (build-output.log,
falling back to the console log) from the `jenkins` container running in WSL2,
parses per-tool issues with severity, and upserts into the `builds` and
`build_issues` tables.

Usage:
    python feed_jenkins_builds.py                     # all builds
    python feed_jenkins_builds.py --since 30          # only build >= 30
    python feed_jenkins_builds.py --clear             # delete rows first
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

from analyze_history import ensure_schema, get_db_conn
from ml.severity_llm import classify_severity
from ml.rootcause_model import extract_evidence_lines
from ml.category_model import predict_category

WSL_DISTRO = "Ubuntu"
CONTAINER = "jenkins"
JOB_BUILDS = "/var/jenkins_home/jobs/sales-analyzer/builds"

SEVERITY_POLICY = {
    "pylint": {"F": "Critical", "E": "High", "W": "Medium", "C": "Low", "R": "Medium"},
    "flake8": {"E": "Medium", "W": "Low", "F": "Medium", "C": "Low"},
}
ERROR_LEVELS = {"High", "Critical"}

FLAKE8_RE = re.compile(r"^([^:]+):\d+:\d+:\s+([A-Z]\d{3})\s+(.*)$")
PYLINT_RE = re.compile(r"^([^:]+):\d+:\d+:\s+([A-Z]\d{4}):\s+(.*)\)\s*$")
MYPY_RE = re.compile(r"^([^:]+):\d+:\s+(error|note|warning):\s+(.*)$")
PYTEST_FAIL_RE = re.compile(r"^(tests?/[^\s:]+(?:::[^ ]+)+)\s+FAILED\s+\[")
BLACK_RE = re.compile(r"^would reformat\s+(.+)$")
BANDIT_ISSUE_RE = re.compile(r"^>> Issue:\s+\[([A-Z]\d+:\w+)\]\s*(.*)$")
BANDIT_SEVERITY_RE = re.compile(r"^Severity:\s*(Low|Medium|High|Undefined)")
BANDIT_LOCATION_RE = re.compile(r"^Location:\s*(.+)$")

BANDIT_CONTINUATION = ("Severity:", "Confidence:", "CWE:", "More Info:", "Location:")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def wsl_run(*args):
    r = subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "--", "docker", "exec", CONTAINER, *args],
        capture_output=True,
    )
    return r.returncode, r.stdout


def list_builds():
    rc, out = wsl_run("bash", "-c", f"ls -1 {JOB_BUILDS}")
    if rc != 0:
        print(f"FATAL: cannot list builds: {out.decode()!r}", file=sys.stderr)
        sys.exit(1)
    nums = sorted(int(n) for n in out.decode().split() if n.isdigit())
    return nums


def fetch_build(n):
    """Return (meta_text, log_text). Falls back to the console log."""
    base = f"{JOB_BUILDS}/{n}"
    script = (
        f"cat {base}/build.xml; echo '=====LOG====='; "
        f"cat {base}/archive/build-output.log 2>/dev/null || cat {base}/log 2>/dev/null"
    )
    rc, out = wsl_run("sh", "-c", script)
    if rc != 0:
        return None, None
    text = out.decode("utf-8", errors="replace")
    if "=====LOG=====" not in text:
        return text, ""
    meta, _, log = text.partition("=====LOG=====")
    return meta, log


def parse_meta(meta):
    m_ts = re.search(r"<startTime>(\d+)</startTime>", meta)
    m_res = re.search(r"<result>([A-Z_]+)</result>", meta)
    ts = datetime.fromtimestamp(int(m_ts.group(1)) / 1000, tz=timezone.utc) if m_ts else datetime.now(tz=timezone.utc)
    result = m_res.group(1) if m_res else None
    return ts, result


def classify_line(line, pending_bandit):
    """Returns (issue dict or None, updated pending_bandit)."""
    issue = None

    if line.startswith(">>"):
        m = BANDIT_ISSUE_RE.match(line)
        if m:
            return None, {"code": m.group(1), "msg": m.group(2).strip(), "sev": None, "loc": None}
        return None, pending_bandit

    if pending_bandit is not None:
        m = BANDIT_SEVERITY_RE.match(line)
        if m:
            pending_bandit["sev"] = "Medium" if m.group(1) == "Undefined" else m.group(1)
            return None, pending_bandit
        m = BANDIT_LOCATION_RE.match(line)
        if m:
            pending_bandit["loc"] = m.group(1).strip()
            sev = pending_bandit["sev"] or "Medium"
            code = pending_bandit["code"]
            line_txt = f"{code}: {pending_bandit['msg']}  ->  {pending_bandit['loc']}"
            issue = {"severity": sev, "category": "bandit", "line": line_txt, "is_error": sev in ERROR_LEVELS}
            return issue, None
        if line.strip() and not any(line.startswith(p) for p in BANDIT_CONTINUATION):
            return None, None
        return None, pending_bandit

    if line.startswith("would reformat"):
        m = BLACK_RE.match(line)
        if m:
            return {"severity": "Medium", "category": "black", "line": m.group(1), "is_error": False}, None

    m = MYPY_RE.match(line)
    if m:
        kind = m.group(2)
        if kind == "error":
            sev, err = "High", True
        else:
            sev, err = "Low", False
        return {"severity": sev, "category": "mypy", "line": line.strip(), "is_error": err}, None

    m = PYLINT_RE.match(line)
    if m:
        sev = SEVERITY_POLICY["pylint"].get(m.group(2)[0], "Medium")
        return {"severity": sev, "category": "pylint", "line": line.strip(), "is_error": sev in ERROR_LEVELS}, None

    m = FLAKE8_RE.match(line)
    if m:
        sev = SEVERITY_POLICY["flake8"].get(m.group(2)[0], "Medium")
        return {"severity": sev, "category": "flake8", "line": line.strip(), "is_error": sev in ERROR_LEVELS}, None

    m = PYTEST_FAIL_RE.match(line)
    if m:
        return {"severity": "High", "category": "test", "line": line.strip(), "is_error": True}, None

    return None, pending_bandit


def parse_log(log_text):
    issues = []
    pending = None
    for raw in log_text.splitlines():
        line = ANSI_RE.sub("", raw).rstrip()
        if not line.strip():
            pending = None
            continue
        issue, pending = classify_line(line, pending)
        if issue:
            issues.append(issue)
            pending = None

    errors = [i for i in issues if i["is_error"]]
    warnings = [i for i in issues if not i["is_error"]]
    return {"error_count": len(errors), "warning_count": len(warnings), "errors": errors, "warnings": warnings}


def ingest_build(cur, n, require_complete=True, llm=True):
    """Fetch one build from Jenkins and upsert it into Postgres. Returns True if data was written."""
    meta, log = fetch_build(n)
    if meta is None or not log.strip():
        return False
    ts, result = parse_meta(meta)
    if require_complete and (result is None or "<completed>true" not in meta):
        return False
    parsed = parse_log(log)
    is_clean = (
        result == "SUCCESS"
        and parsed["error_count"] == 0
        and parsed["warning_count"] == 0
    )
    _, evidence = extract_evidence_lines(log)
    if not evidence:
        evidence = "\n".join(
            i["line"] for i in parsed["errors"] + parsed["warnings"]
        )
    if is_clean:
        category = "clean"
    elif evidence:
        category, _, _ = predict_category(evidence)
    else:
        category, _, _ = predict_category(log[-10000:])
    cur.execute("DELETE FROM build_issues WHERE build_id = %s", (n,))
    cur.execute(
        "INSERT INTO builds (build_id, timestamp, error_count, warning_count, trend, result) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (build_id) DO UPDATE SET "
        "timestamp = EXCLUDED.timestamp, error_count = EXCLUDED.error_count, "
        "warning_count = EXCLUDED.warning_count, result = EXCLUDED.result",
        (n, ts, parsed["error_count"], parsed["warning_count"], "", result),
    )
    cur.execute(
        "UPDATE builds SET category = %s WHERE build_id = %s",
        (category, n),
    )
    for e in parsed["errors"]:
        cur.execute(
            "INSERT INTO build_issues (build_id, timestamp, severity, category, line, is_error) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (n, ts, e["severity"], e["category"], e["line"], True),
        )
    for w in parsed["warnings"]:
        cur.execute(
            "INSERT INTO build_issues (build_id, timestamp, severity, category, line, is_error) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (n, ts, w["severity"], w["category"], w["line"], False),
        )
    if llm:
        cur.execute("SELECT llm_severity FROM builds WHERE build_id = %s", (n,))
        if cur.fetchone()[0] is None:
            if is_clean:
                sev, source, reason = "Low", "policy", "Clean build: 0 errors, 0 warnings, all tests pass"
            else:
                sev, source, reason = classify_severity(
                    category, evidence, fallback_policy=False
                )
            if sev is not None:
                cur.execute(
                    "UPDATE builds SET llm_severity = %s, severity_source = %s, severity_reason = %s "
                    "WHERE build_id = %s",
                    (sev, source, reason, n),
                )
    return True


def max_build_in_db(cur):
    cur.execute("SELECT COALESCE(MAX(build_id), 0) FROM builds")
    return cur.fetchone()[0]


def ingest_many(cur, builds, verbose=True, llm=True):
    written = 0
    for n in builds:
        ok = ingest_build(cur, n, llm=llm)
        if verbose and ok:
            print(f"  {n}: ingested", flush=True)
        cur.connection.commit()
        written += int(ok)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=0)
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--no-llm", action="store_true", help="skip LLM severity (rule-based only)")
    args = ap.parse_args()

    builds = [n for n in list_builds() if n >= args.since]
    print(f"Found {len(builds)} builds ({builds[0]}..{builds[-1]})")

    ensure_schema()
    conn = get_db_conn()
    cur = conn.cursor()

    if args.clear:
        cur.execute("DELETE FROM build_issues")
        cur.execute("DELETE FROM builds")
        conn.commit()
        print("Cleared existing rows.")

    written = ingest_many(cur, builds, llm=not args.no_llm)
    conn.commit()
    conn.close()
    print(f"Done. {written}/{len(builds)} builds ingested.")


if __name__ == "__main__":
    main()