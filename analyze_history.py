import os
import json
import re
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict
import psycopg2

def get_db():
    return psycopg2.connect(
        host="localhost", database="buildhistory",
        user="builduser", password="buildpass"
    )


DATA_DIR = Path("build_history")


def parse_report(text):
    """Parse analysis-report.txt into structured data."""
    errors = []
    warnings = []
    error_count = 0
    warning_count = 0

    section = None
    for line in text.split("\n"):
        line = line.strip()

        if line.startswith("Errors:"):
            error_count = int(line.split(":")[1].strip())
            section = None
        elif line.startswith("Warnings:"):
            warning_count = int(line.split(":")[1].strip())
            section = None
        elif line.startswith("Error Details:"):
            section = "errors"
        elif line.startswith("Warning Details:"):
            section = "warnings"
        elif line.startswith("[") and section:
            match = re.match(r"\[(\w+)\]\s+\[(\w+)\]\s+(.*)", line)
            if match:
                entry = {
                    "severity": match.group(1),
                    "category": match.group(2),
                    "line": match.group(3)
                }
                if section == "errors":
                    errors.append(entry)
                else:
                    warnings.append(entry)

    return {
        "error_count": error_count,
        "warning_count": warning_count,
        "errors": errors,
        "warnings": warnings
    }

def save_build_to_db(build_id, data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO builds (build_id, timestamp, error_count, warning_count) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT (build_id) DO NOTHING",
        (data["build_id"], data["timestamp"], data["error_count"], data["warning_count"])
    )
    for entry in data["errors"] + data["warnings"]:
        cur.execute(
            "INSERT INTO build_issues (build_id, severity, category, line, is_error) "
            "VALUES (%s, %s, %s, %s, %s)",
            (build_id, entry["severity"], entry["category"], entry["line"],
             entry["category"] in BUILD_BREAKING)
        )
    conn.commit()
    conn.close()


def load_all_builds():
    """Load all saved builds from build_history/."""
    builds = []
    if not DATA_DIR.exists():
        return builds

    for path in sorted(DATA_DIR.glob("build_*.json")):
        with open(path) as f:
            builds.append(json.load(f))

    return builds


def detect_patterns(builds):
    """Find patterns across all builds.

    Returns:
        recurring: issues that appear in 2+ builds
        hotspots: files with most issues
        trends: error/warning counts over time
    """
    if not builds:
        return {}, {}, {}


    issue_history = defaultdict(list) 
    file_issues = defaultdict(int)     
    error_trend = []
    warning_trend = []

    for build in builds:
        bid = build["build_id"]
        error_trend.append(build["error_count"])
        warning_trend.append(build["warning_count"])

        for entry in build["errors"] + build["warnings"]:
            line = entry["line"]
            issue_history[line].append(bid)


            file_match = re.match(r"([\w/]+\.py)", line)
            if file_match:
                file_issues[file_match.group(1)] += 1


    recurring = {
        line: builds
        for line, builds in issue_history.items()
        if len(builds) >= 2
    }


    hotspots = dict(sorted(file_issues.items(), key=lambda x: -x[1])[:5])


    trend = "stable"
    if len(error_trend) >= 2:
        recent = error_trend[-1]
        earlier = error_trend[0]
        if recent > earlier * 1.5:
            trend = "increasing"
        elif recent < earlier * 0.5:
            trend = "decreasing"

    return recurring, hotspots, trend


SEVERITY_WEIGHT = {
    "Critical": 5,
    "High": 4,
    "Medium": 3,
    "Low": 1,
}


BUILD_BREAKING = {"Types", "Tests", "Dependencies", "Git", "Docker", "Network"}


def score_issue(issue, frequency, age_builds):
    """Calculate priority score for an issue.

    Rules:
    1. Build-breaking errors get a HUGE bonus (they block deploys)
    2. More frequent = more urgent
    3. Higher severity = more urgent
    4. Older issue (appears across many builds) = more urgent

    score = build_bonus + (severity × 3) + (frequency × 2) + (age × 1)
    """
    build_bonus = 1000 if issue["category"] in BUILD_BREAKING else 0
    severity = SEVERITY_WEIGHT.get(issue["severity"], 1)
    score = build_bonus + (severity * 3) + (frequency * 2) + (age_builds * 1)
    return score


def analyze_all():
    """Main entry point: load all builds, detect patterns, rank issues."""
    builds = load_all_builds()
    if not builds:
        print("No builds found. Run: python analyze_history.py --save <path>")
        return

    recurring, hotspots, trend = detect_patterns(builds)
    total_builds = len(builds)


    issue_stats = defaultdict(lambda: {"errors": 0, "warnings": 0, "builds": set()})
    for build in builds:
        for entry in build["errors"]:
            line = entry["line"]
            issue_stats[line]["errors"] += 1
            issue_stats[line]["builds"].add(build["build_id"])
        for entry in build["warnings"]:
            line = entry["line"]
            issue_stats[line]["warnings"] += 1
            issue_stats[line]["builds"].add(build["build_id"])

  
    scored = []
    for line, stats in issue_stats.items():
  
        for build in reversed(builds):
            issue = next(
                (e for e in build["errors"] + build["warnings"] if e["line"] == line),
                None
            )
            if issue:
                break

        if issue is None:
            continue

        frequency = stats["errors"] + stats["warnings"]
        age = len(stats["builds"])
        score = score_issue(issue, frequency, age)

        scored.append({
            "line": line,
            "category": issue["category"],
            "severity": issue["severity"],
            "frequency": frequency,
            "builds_affected": age,
            "score": score,
            "is_error": issue["category"] in BUILD_BREAKING
        })

    scored.sort(key=lambda x: -x["score"])

    report = []
    report.append("=" * 60)
    report.append("     BUILD HISTORY ANALYSIS REPORT")
    report.append("=" * 60)
    report.append(f"\nTotal builds analyzed: {total_builds}")
    report.append(f"Error trend: {trend}")

    total_errors = sum(b["error_count"] for b in builds)
    total_warnings = sum(b["warning_count"] for b in builds)
    report.append(f"Total errors: {total_errors}")
    report.append(f"Total warnings: {total_warnings}")

    if hotspots:
        report.append("\n--- HOTSPOT FILES (most issues) ---")
        for file, count in hotspots.items():
            report.append(f"  {file}: {count} issues")

    if recurring:
        report.append(f"\n--- RECURRING ISSUES ({len(recurring)} appear in 2+ builds) ---")
        for line, blds in list(recurring.items())[:5]:
            report.append(f"  [{len(blds)} builds] {line[:70]}")

    report.append("\n--- PRIORITIZED ISSUES (highest priority first) ---")
    for i, issue in enumerate(scored[:15], 1):
        prefix = "ERROR" if issue["is_error"] else "WARN "
        report.append(
            f"  {i}. [{prefix}] [score={issue['score']}] "
            f"[{issue['severity']}/{issue['category']}] "
            f"freq={issue['frequency']}, builds={issue['builds_affected']}\n"
            f"     {issue['line'][:75]}"
        )

    report.append("\n--- PRIORITY CLASSIFICATION ---")
    report.append("  Priority 1: Fix immediately (build-breaking errors)")
    report.append("  Priority 2: Fix this sprint (security issues)")
    report.append("  Priority 3: Fix when possible (recurring warnings)")
    report.append("  Priority 4: Ignore/fix opportunistically (one-time)")

    output = "\n".join(report)
    print(output)

    with open("history-report.txt", "w") as f:
        f.write(output)
    print("\nSaved to history-report.txt")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        build_id = int(sys.argv[2])
        report_path = sys.argv[3]
        save_build_to_db(build_id, report_path)
    else:
        analyze_all()
