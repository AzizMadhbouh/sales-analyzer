import csv
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.environ.get("TEMP", "/tmp"), "veloren_real_lines.csv")
OUT_CSV = os.path.join(ROOT, "pipeline-dataset", "train.csv")

# FlakeStorm/Veloren job-level category -> (our_category, severity, component)
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

# Only self-describing categories whose lines literally state the root cause.
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


def main():
    with open(SRC, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        raw = [row for row in reader]

    mapped = []
    seen = set()
    for msg, fs_cat in raw:
        if fs_cat not in SELF_DESCRIBING:
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

    print(f"raw self-describing lines: {len(mapped)}")
    print("mapped categories:", dict(Counter(x[1] for x in mapped)))

    import pandas as pd
    existing = pd.read_csv(OUT_CSV, encoding="utf-8-sig")
    existing_msgs = set(existing["error_message"].str.lower())
    new_rows = [r for r in mapped if r[0].lower() not in existing_msgs]
    print(f"not already in train.csv: {len(new_rows)}")

    new_df = pd.DataFrame(new_rows, columns=["error_message", "category", "severity", "component"])
    out = pd.concat([existing, new_df], ignore_index=True)
    print(f"\nold rows: {len(existing)}  ->  new rows: {len(out)}")
    print("new-category delta:\n", new_df["category"].value_counts().sort_index().to_string())
    out.to_csv(OUT_CSV, index=False)
    print(f"\nwritten: {OUT_CSV}")


if __name__ == "__main__":
    main()