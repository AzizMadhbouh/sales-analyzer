import csv
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.environ.get("TEMP", "/tmp"), "veloren_real_lines.csv")
TRAIN = os.path.join(ROOT, "pipeline-dataset", "train.csv")

MAP = {
    "git_transient_error":                ("Repository", "High", "GitHub"),
    "runner_pod_waiting_timeout":         ("CI Orchestration", "Medium", "Kubernetes"),
    "runner_image_pull_failure":          ("Image Management", "High", "Docker"),
    "container_registry_server_error":    ("Container Runtime", "High", "Docker"),
    "host_resolution_failure":            ("Network", "Medium", "Network"),
    "remote_call_timeout":                ("Network", "Medium", "Network"),
    "helm_resource_error":                ("Configuration", "High", "Kubernetes"),
    "job_execution_timeout":              ("CI Orchestration", "Medium", "Jenkins"),
    "dependency_installation_failure":    ("Dependencies", "High", "Application"),
    "misconfigured_env_variable":         ("Configuration", "Medium", "Application"),
    "external_file_invalid_format":       ("Configuration", "Medium", "Application"),
    "api_gateway_deployment_error":       ("API", "High", "Application"),
}

SELF_DESCRIBING = {
    "git_transient_error",
    "runner_pod_waiting_timeout",
    "runner_image_pull_failure",
    "host_resolution_failure",
    "container_registry_server_error",
    "helm_resource_error",
    "remote_call_timeout",
    "job_execution_timeout",
}

NORM_HASH = re.compile(r"\b[0-9a-f]{8,}\b")
NORM_NUM = re.compile(r"[:\d.,/]+")

# A pod-waiting line is CI/k8s infrastructure, not a git failure even if the
# log mentions gitlab. Exclude them from git-driven categories.
POD_LINE = re.compile(r"(?i)waiting for pod .*status is pending|unschedulable|insufficient cpu")


def added_rows():
    with open(SRC, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        raw = [row for row in reader]
    mapped, seen = [], set()
    for msg, fs_cat in raw:
        if fs_cat not in SELF_DESCRIBING:
            continue
        if fs_cat == "git_transient_error" and POD_LINE.search(msg):
            continue
        lab = MAP.get(fs_cat)
        if lab is None:
            continue
        key = NORM_HASH.sub("H", NORM_NUM.sub("N", msg))
        if msg in seen or key in seen:
            continue
        seen.add(msg)
        seen.add(key)
        mapped.append((msg, lab[0], lab[1], lab[2]))
    return mapped


def main():
    good = added_rows()
    print("corrected addition rows:", len(good))
    print("by category:", dict(Counter(x[1] for x in good)))

    import pandas as pd
    curr = pd.read_csv(TRAIN, encoding="utf-8-sig")

    # remove whatever the previous merge added: any row whose message is in the
    # (uncorrected) harvest, then re-add the corrected rows.
    with open(SRC, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        harv = {row[0] for row in reader if row[1] in SELF_DESCRIBING}
    dropped = curr[~curr["error_message"].isin(harv)]
    print(f"after removing previous harvest rows: {len(dropped)}")

    good_msgs = {r[0].lower() for r in good}
    new_rows = [r for r in good if r[0].lower() not in dropped["error_message"].str.lower().tolist()]
    new_df = pd.DataFrame(new_rows, columns=["error_message", "category", "severity", "component"])
    out = pd.concat([dropped, new_df], ignore_index=True)
    print(f"final rows: {len(out)}")
    print("new cat delta:\n", new_df["category"].value_counts().sort_index().to_string())
    out.to_csv(TRAIN, index=False)
    print("written:", TRAIN)


if __name__ == "__main__":
    main()