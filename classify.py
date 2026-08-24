import re
import sys
from collections import Counter

log = open(sys.argv[1], encoding='utf-8-sig').read()
lines = log.split('\n')

categories = {
    'Tests': ['FAILED', 'AssertionError', 'assert'],
    'Dependencies': ['ModuleNotFoundError', 'ImportError', 'No module named'],
    'Git': ['git', 'not in a git directory', 'clone'],
    'Docker': ['docker', 'container', 'daemon'],
    'Permissions': ['permission denied', 'access denied'],
    'Linting': ['E302', 'E501', 'F401', 'W291'],
    'Types': ['TypeError', 'incompatible'],
}

severity = {
    'Dependencies': 'Critical',
    'Git': 'Critical',
    'Docker': 'High',
    'Permissions': 'Critical',
    'Tests': 'High',
    'Types': 'High',
    'Linting': 'Low',
}

warning_categories = {
    'Security': ['security', 'vulnerability', 'cve', 'unsafe', 'hardcoded'],
    'Dependencies': ['deprecat', 'removed', 'end.of.life', 'breaking', 'incompatible'],
    'Performance': ['slow', 'timeout', 'memory', 'overflow'],
    'Code Quality': ['unused', 'missing', 'empty', 'duplicate'],
    'Style': ['format', 'style', 'whitespace', 'comment'],
    'TODOs': ['todo', 'fixme', 'hack'],
}

warning_severity = {
    'security': 'Critical',
    'vulnerability': 'Critical',
    'cve': 'Critical',
    'unsafe': 'Critical',
    'hardcoded': 'Critical',
    'deprecat': 'High',
    'removed': 'High',
    'memory': 'High',
    'overflow': 'High',
    'unstable': 'Medium',
    'performance': 'Medium',
    'slow': 'Medium',
    'timeout': 'Medium',
    'duplicate': 'Medium',
    'unused': 'Low',
    'missing': 'Low',
    'empty': 'Low',
    'format': 'Low',
    'style': 'Low',
    'whitespace': 'Low',
    'todo': 'Low',
    'fixme': 'Low',
}


def is_noise(line):
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith('[Pipeline]'):
        return True
    if stripped.startswith('Running on'):
        return True
    if stripped.startswith('Obtained'):
        return True
    if stripped.startswith('Started by'):
        return True
    if stripped.startswith('Finished:'):
        return True
    if stripped.startswith('Total:'):
        return True
    if stripped.startswith('Error Details:'):
        return True
    if stripped.startswith('Warning Details:'):
        return True
    if stripped.startswith('[') and ']' in stripped[:20]:
        return True
    if re.match(r'  \[', stripped):
        return True
    if stripped.startswith('Passed in branch') or stripped.startswith('Failed in branch'):
        return True
    if '=== ' in stripped and ' ===' in stripped:
        return True
    if re.match(r'\d+ passed', stripped):
        return True
    if stripped.startswith('WARNING: pytest cache'):
        return True
    if stripped.startswith('WARNING: Fictional'):
        return True
    return False


def classify_error(line):
    category = 'Unknown'
    for cat, keywords in categories.items():
        if any(kw.lower() in line.lower() for kw in keywords):
            category = cat
            break
    sev = severity.get(category, 'Low')
    return category, sev


def classify_warning(line):
    category = 'General'
    for cat, keywords in warning_categories.items():
        if any(kw in line.lower() for kw in keywords):
            category = cat
            break
    sev = 'Low'
    for keyword, level in warning_severity.items():
        if keyword in line.lower():
            sev = level
            break
    return category, sev


errors = []
seen_errors = set()
for line in lines:
    if is_noise(line):
        continue
    if 'error' in line.lower() or 'failed' in line.lower() or re.search(r'[EFW]\d{3}', line):
        key = line.strip()
        if key in seen_errors:
            continue
        seen_errors.add(key)
        category, sev = classify_error(line)
        errors.append({'category': category, 'severity': sev, 'line': line.strip()})

warnings = []
seen_warnings = set()
for line in lines:
    if is_noise(line):
        continue
    if 'warning' in line.lower() or 'warn' in line.lower():
        key = line.strip()
        if key in seen_warnings:
            continue
        seen_warnings.add(key)
        category, sev = classify_warning(line)
        warnings.append({'category': category, 'severity': sev, 'line': line.strip()})

print(f"Total: {len(errors)} errors and {len(warnings)} warnings\n")

if errors:
    counts = Counter(e['category'] for e in errors)
    print("Error Summary:")
    for cat, count in counts.items():
        print(f"  {cat}: {count}")
    print(f"\nError Details:")
    for e in errors:
        print(f"  [{e['severity']}] [{e['category']}] {e['line']}")

if warnings:
    counts = Counter(w['category'] for w in warnings)
    print(f"\nWarning Summary:")
    for cat, count in counts.items():
        print(f"  {cat}: {count}")
    print(f"\nWarning Details:")
    for w in warnings:
        print(f"  [{w['severity']}] [{w['category']}] {w['line']}")

if not errors and not warnings:
    print("Build is clean!")
