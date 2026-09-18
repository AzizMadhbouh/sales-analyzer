import csv
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CI_REPAIR = os.path.join(os.environ.get("TEMP", "/tmp"), "ci_repair_real_lines.csv")
OUT_CSV = os.path.join(ROOT, "pipeline-dataset", "train.csv")

KEEP = {"Test", "Lint", "Security", "Build", "Runtime", "Network", "Configuration", "API", "Dependencies"}

PREFIX_RE = re.compile(r"^\s*(?:[\w./\\-]+):\d+(?::\d+)?:\s*([A-Z])\d{3,4}(?::|\s)", re.IGNORECASE)
PYLINT_SUFFIX = re.compile(r"\([a-z0-9-]+\)\s*$", re.IGNORECASE)
BANDIT_SEV = re.compile(r"Severity:\s*(Low|Medium|High)", re.IGNORECASE)
SEVERITY_PREFIX = {"F": "Critical", "E": "High", "W": "Medium", "C": "Low", "R": "Medium"}
FLAKE8_MAP = {"F": "High", "E": "Medium", "W": "Low", "C": "Medium"}


def severity_from_bandit(line):
    m = BANDIT_SEV.search(line)
    if m:
        return m.group(1).capitalize()
    return "Low"


def classify_confident(line):
    """Returns (category, severity, component) or None when no tool-format
    signature matches. Does NOT emit the default Runtime fallback."""
    l = line.strip().lower()

    if line.lstrip().startswith(">> Issue:") or "Severity:" in line or "hardcoded_password" in line.lower():
        return ("Security", severity_from_bandit(line), "Application")

    m = re.search(r"error:\s+(.+?)(?:\s+\[[a-z-]+\])?$", line)
    if m and (re.search(r"\[[a-z-]+\]\s*$", line) or "No module named" not in line) and "::" not in line:
        if "error:" in l and re.search(r"\b(error|error:)\b.*\[[a-z-]+\]", line):
            return ("Lint", "High", "Application")

    pm = PREFIX_RE.search(line)
    if pm:
        code = pm.group(1).upper()
        if PYLINT_SUFFIX.search(line):
            return ("Lint", SEVERITY_PREFIX.get(code, "Medium"), "Application")
        return ("Lint", FLAKE8_MAP.get(code, "Medium"), "Application")

    if re.search(r"error (CS|TS)\d{3,4}|\.c(?:pp)?:\d+:\d+:\s*error|error:[^\n]*\bat\b", line, re.IGNORECASE):
        return ("Build", "High", "Application")
    if re.search(r"make: \*\*\*|rake aborted|npm ERR|webpack.*failed|build failed|exit status 1\b|Could not resolve", line, re.IGNORECASE):
        return ("Build", "High", "Application")

    if re.search(r"FAILED|AssertionError|assert |expected .* to (eq|be|equal)|panicked at|Test suite failed|Failures:|1\) Failed|Failed asserting", line, re.IGNORECASE):
        if "AssertionError" in l or "assert " in l or "panicked" in l:
            return ("Test", "High", "Application")
        return ("Test", "Medium", "Application")

    if re.search(r"No module named|ImportError|ModuleNotFoundError|externally-managed-environment|Failed to (install|resolve) (dep|package)|pip install.*(error|failed)", line, re.IGNORECASE):
        if "No module named" in l or "ModuleNotFound" in l:
            return ("Runtime", "High", "Application")
        return ("Dependencies", "High", "Application")

    if re.search(r"\b(TypeError|ValueError|RuntimeError|KeyError|AttributeError|IndexError|NullPointer|RuntimeException|Exception in thread)\b", line):
        return ("Runtime", "High", "Application")

    if re.search(r"timeout|timed? out|connection (refused|reset|closed)|could not resolve host|dns|tls|x509|network", line, re.IGNORECASE):
        return ("Network", "Medium", "Network")

    if re.search(r"config|environment variable|env var|\.env|not configured|missing.*(key|setting)", line, re.IGNORECASE):
        return ("Configuration", "Medium", "Application")

    return None


def main():
    with open(SRC_CI_REPAIR, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        raw = [row for row in reader]

    classified = []
    for row in raw:
        msg = row[0]
        lab = classify_confident(msg)
        if lab is not None:
            classified.append((msg, lab[0], lab[1], lab[2]))

    print(f"raw lines: {len(raw)}")
    print(f"confidently classified: {len(classified)}")
    from collections import Counter
    print("categories:", dict(Counter(x[1] for x in classified)))

    keep = [r for r in classified if r[1] in KEEP]
    print(f"in keep-set: {len(keep)}")

    seen = set()
    deduped = []
    for r in keep:
        if r[0] in seen:
            continue
        seen.add(r[0])
        deduped.append(r)
    print(f"deduped within source: {len(deduped)}")

    import pandas as pd
    existing = pd.read_csv(OUT_CSV, encoding="utf-8-sig")
    existing_msgs = set(existing["error_message"].str.lower())
    new_rows = [r for r in deduped if r[0].lower() not in existing_msgs]
    print(f"not already in train.csv: {len(new_rows)}")

    new_df = pd.DataFrame(new_rows, columns=["error_message", "category", "severity", "component"])
    out = pd.concat([existing, new_df], ignore_index=True)
    print(f"\nold rows: {len(existing)}  ->  new rows: {len(out)}")
    print("category counts:\n", out["category"].value_counts().sort_index().to_string())
    out.to_csv(OUT_CSV, index=False)
    print(f"\nwritten: {OUT_CSV}")


if __name__ == "__main__":
    main()