import pickle
import re
import sys
from collections import Counter

# Load models
with open('category_model.pkl', 'rb') as f:
    vectorizer, category_model = pickle.load(f)

with open('severity_model.pkl', 'rb') as f:
    _, severity_model = pickle.load(f)


def predict(line):
    X = vectorizer.transform([line])
    category = category_model.predict(X)[0]
    severity = severity_model.predict(X)[0]
    return category, severity


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
    if re.match(r'^\s*\[', stripped):
        return True
    if stripped.startswith('Passed in branch') or stripped.startswith('Failed in branch'):
        return True
    if '=== ' in stripped and ' ===' in stripped:
        return True
    if re.match(r'\d+ passed', stripped):
        return True
    if stripped.startswith('WARNING: pytest cache'):
        return True
    if stripped.startswith('ERROR: script returned'):
        return True
    if 'Summary:' in stripped or 'Details:' in stripped:
        return True
    if stripped.startswith('Build is clean'):
        return True
    if re.match(r'^\s*\d+ (error|warning)', stripped):
        return True
    if re.match(r'^\[', stripped):
        return True
    if re.match(r'^Total:', stripped):
        return True
    if stripped.startswith('Build is clean'):
        return True
    return False


def get_dedup_key(line):
    return line.strip()


with open(sys.argv[1], encoding='utf-8-sig') as f:
    lines = f.readlines()

errors = []
seen = set()
for line in lines:
    stripped = line.strip()
    if is_noise(stripped):
        continue
    if 'error' in stripped.lower() or 'failed' in stripped.lower() or 'warning' in stripped.lower() or re.search(r'[EFW]\d{3}', stripped):
        key = get_dedup_key(stripped)
        if key in seen:
            continue
        seen.add(key)
        category, severity = predict(stripped)
        errors.append({'category': category, 'severity': severity, 'line': stripped})

counts = Counter(e['category'] for e in errors)
print(f"Total: {len(errors)} issues\n")
for cat, count in counts.items():
    print(f"  {cat}: {count}")

print(f"\nDetails:")
for e in errors:
    print(f"  [{e['severity']}] [{e['category']}] {e['line']}")
