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
warnings = []
seen = set()
for line in lines:
    stripped = line.strip()
    if is_noise(stripped):
        continue
    key = get_dedup_key(stripped)
    if key in seen:
        continue
    seen.add(key)
    is_error = 'error' in stripped.lower() or 'failed' in stripped.lower() or re.search(r'[EFW]\d{3}', stripped)
    is_warning = 'warning' in stripped.lower() or 'warn' in stripped.lower()
    if is_error or is_warning:
        category, severity = predict(stripped)
        entry = {'category': category, 'severity': severity, 'line': stripped}
        if is_warning and not is_error:
            warnings.append(entry)
        else:
            errors.append(entry)

counts_errors = Counter(e['category'] for e in errors)
counts_warnings = Counter(w['category'] for w in warnings)

print(f"Errors: {len(errors)}")
for cat, count in counts_errors.items():
    print(f"  {cat}: {count}")

print(f"\nWarnings: {len(warnings)}")
for cat, count in counts_warnings.items():
    print(f"  {cat}: {count}")

if errors:
    print(f"\nError Details:")
    for e in errors:
        print(f"  [{e['severity']}] [{e['category']}] {e['line']}")

if warnings:
    print(f"\nWarning Details:")
    for w in warnings:
        print(f"  [{w['severity']}] [{w['category']}] {w['line']}")
