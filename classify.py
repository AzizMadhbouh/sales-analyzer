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
    # Critical - must fix
    'security': 'Critical',
    'vulnerability': 'Critical',
    'cve': 'Critical',
    'unsafe': 'Critical',
    'hardcoded': 'Critical',

    # High - fix soon
    'deprecat': 'High',
    'removed': 'High',
    'end.of.life': 'High',
    'breaking': 'High',
    'incompatible': 'High',
    'memory': 'High',
    'overflow': 'High',
    'permission': 'High',

    # Medium - should fix
    'unstable': 'Medium',
    'performance': 'Medium',
    'slow': 'Medium',
    'timeout': 'Medium',
    'retry': 'Medium',
    'cache': 'Medium',
    'conflict': 'Medium',
    'override': 'Medium',
    'duplicate': 'Medium',

    # Low - nice to fix
    'unused': 'Low',
    'missing': 'Low',
    'empty': 'Low',
    'format': 'Low',
    'style': 'Low',
    'whitespace': 'Low',
    'comment': 'Low',
    'todo': 'Low',
    'fixme': 'Low',
    'info': 'Low',
    'notice': 'Low',
}


errors = []
for line in lines:
     if 'error' in line.lower() or 'failed' in line.lower() or re.search(r'[EFW]\d{3}', line):
        category = 'Unknown'
        for cat, keywords in categories.items():
            if any(kw.lower() in line.lower() for kw in keywords):
                category = cat
                break
        sev = severity.get(category, 'Low')
        errors.append({'category': category, 'severity': sev, 'line': line})
warnings = []
for line in lines:
    if 'warning' in line.lower() or 'warn' in line.lower():
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
        
        warnings.append({'category': category, 'severity': sev, 'line': line})


print(f"Total: {len(errors)} errors and {len(warnings)} warnings \n")

counts = Counter(e['category'] for e in errors)
for cat, count in counts.items():
    print(f"  {cat}: {count}")

print(f"\nError Details:")
for e in errors:
    print(f"  [{e['severity']}] [{e['category']}] {e['line']}")

print(f"\nWarning Details:")
for w in warnings:
    print(f"  [{w['severity']}] [{w['category']}] {w['line']}")