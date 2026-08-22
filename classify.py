import re
import sys

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

errors = []
for line in lines:
    if 'error' in line.lower() or 'failed' in line.lower():
        category = 'Unknown'
        for cat, keywords in categories.items():
            if any(kw.lower() in line.lower() for kw in keywords):
                category = cat
                break
        errors.append({'category': category, 'line': line})

print(f"Total: {len(errors)} errors\n")
from collections import Counter
counts = Counter(e['category'] for e in errors)
for cat, count in counts.items():
    print(f"  {cat}: {count}")

print(f"\nDetails:")
for e in errors:
    print(f"  [{e['category']}] {e['line']}")