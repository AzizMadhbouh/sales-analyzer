"""Build pipeline-dataset/jenkins_outputs_dataset.csv from REAL Jenkins logs.

Segments each jenkins_output_*.txt into its per-tool output blocks (mypy,
bandit, pylint, ruff, pytest) using markers found in the actual text, and labels
each with its tool. Whole logs with no failures become pass_clean. Nothing here
is synthetic: every training row is a real block cut from a real log.
"""
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
OUT = os.path.join(BASE, "pipeline-dataset", "jenkins_outputs_dataset.csv")

RE_BANDIT_START = re.compile(r"^\[main\]\s+INFO\s+running on Python")
RE_BANDIT_END = re.compile(r"^Files skipped \(")
RE_MYPY_ERR = re.compile(r":\s*error:")
RE_MYPY_SUM = re.compile(r"^Found \d+ error")
RE_PYLINT_START = re.compile(r"^\*+\s*Module ")
RE_PYLINT_END = re.compile(r"rated at [\d.]+/10")
RE_RUFF_START = re.compile(r"^(All done!|9 files would be left unchanged\.|Success: no issues found)")
RE_TEST_START = re.compile(r"^=+ test session starts =+")


def segment(block_lines):
    """Return dict labels -> list of 'text' snippets for one file's lines."""
    bandit_start = next((i for i, l in enumerate(block_lines) if RE_BANDIT_START.search(l)), None)
    bandit_end = next((i for i, l in enumerate(block_lines) if RE_BANDIT_END.search(l)), None)

    mypy_start = next((i for i, l in enumerate(block_lines) if RE_MYPY_ERR.search(l)), None)
    mypy_end = None
    if mypy_start is not None:
        mypy_end = next(
            (i for i in range(mypy_start, len(block_lines)) if RE_MYPY_SUM.search(block_lines[i])),
            mypy_start,
        )

    pylint_start = next((i for i, l in enumerate(block_lines) if RE_PYLINT_START.search(l)), None)
    pylint_end = None
    if pylint_start is not None:
        pylint_end = next(
            (i for i in range(pylint_start, len(block_lines)) if RE_PYLINT_END.search(block_lines[i])),
            pylint_start,
        )

    test_start = next((i for i, l in enumerate(block_lines) if RE_TEST_START.search(l)), None)

    out = {}

    def cut(a, b):
        return "\n".join(block_lines[a:b]) if b is not None else None

    # ruff: leading block before mypy/bandit; or whole file if only ruff present
    lead_end = min([i for i in (mypy_start, bandit_start, test_start) if i is not None] or [len(block_lines)])
    if lead_end > 0:
        ruff = cut(0, lead_end)
        if ruff and (RE_RUFF_START.search(ruff) or "would be left unchanged" in ruff or "All done!" in ruff):
            out.setdefault("ruff", []).append(ruff)

    if mypy_start is not None:
        mypy = cut(mypy_start, (mypy_end or len(block_lines)) + 1)
        if mypy and ": error:" in mypy:
            out.setdefault("mypy", []).append(mypy)

    if bandit_start is not None:
        end = bandit_start + 1 if bandit_end is None else bandit_end + 1
        bandit = cut(bandit_start, end)
        if bandit and bandit.lstrip().startswith("[main]"):
            out.setdefault("bandit", []).append(bandit)

    if pylint_start is not None:
        end = pylint_start + 1 if pylint_end is None else pylint_end + 1
        pylint = cut(pylint_start, end)
        if pylint and RE_PYLINT_START.search(pylint):
            out.setdefault("pylint", []).append(pylint)

    if test_start is not None:
        pytest = cut(test_start, len(block_lines))
        if pytest and "FAILED" in pytest:
            out.setdefault("test_failure", []).append(pytest)

    return out


def main():
    rows = []
    files = sorted(f for f in os.listdir(BASE) if re.fullmatch(r"jenkins_output_\d+\.txt", f))
    for fn in files:
        text = open(os.path.join(BASE, fn), encoding="utf-8", errors="replace").read()
        lines = text.splitlines()
        for label, chunks in segment(lines).items():
            for chunk in chunks:
                rows.append({"logs": chunk, "category": label, "split": "train"})

    # whole-log rows: green pipelines and the git checkout failure (real, unsegmented)
    whole = {
        "jenkins_output_2.txt": "pass_clean",
        "jenkins_output_3.txt": "pass_clean",
        "jenkins_output_8.txt": "pass_clean",
        "jenkins_output_7.txt": "ci_config_git",
    }
    for fn, label in whole.items():
        text = open(os.path.join(BASE, fn), encoding="utf-8", errors="replace").read()
        rows.append({"logs": text.strip(), "category": label, "split": "train"})

    df = pd.DataFrame(rows)
    df["logs"] = df["logs"].str.strip()
    df = df[(df["logs"] != "")].drop_duplicates(subset=["logs"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False)
    print("wrote", OUT, "| rows:", len(df))
    print(df.groupby(["split", "category"]).size().to_string())
    print("label counts:", df["category"].value_counts().to_dict())


if __name__ == "__main__":
    sys.exit(main())