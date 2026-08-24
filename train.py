from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import pickle

training_data = {
    "Types": [
        "TypeError: unsupported operand type(s) for +: 'float' and 'NoneType'",
        "TypeError: argument of type 'NoneType' is not iterable",
        "TypeError: 'NoneType' object is not subscriptable",
        "TypeError: can only concatenate str (not 'int') to str",
        "NameError: name 'data' is not defined",
        "NameError: name 'result' is not defined",
        "ValueError: could not convert string to float",
        "ValueError: invalid literal for int() with base 10",
        "ValueError: too many values to unpack",
        "KeyError: 'product'",
        "KeyError: 'price'",
        "IndexError: list index out of range",
        "AttributeError: 'NoneType' object has no attribute 'get'",
    ],
    "Tests": [
        "FAILED tests/test_analyzer.py::TestCalculateTotalSales::test_total_sales_basic",
        "FAILED tests/test_analyzer.py::TestCalculateAverageOrderValue::test_average_basic",
        "FAILED tests/test_reporter.py::TestGenerateTextReport::test_report_contains_header",
        "FAILED tests/test_data_loader.py::TestLoadCSV::test_load_valid_csv",
        "tests/test_analyzer.py::test_average FAILED",
        "tests/test_analyzer.py::test_total_sales FAILED",
        "7 failed, 30 passed in 0.35s",
    ],
    "Dependencies": [
        "ModuleNotFoundError: No module named 'pandas'",
        "ModuleNotFoundError: No module named 'numpy'",
        "ModuleNotFoundError: No module named 'requests'",
        "ImportError: cannot import name 'DataFrame' from 'pandas'",
        "ImportError: cannot import name 'json' from 'requests'",
        "No module named 'tensorflow'",
        "No module named 'sklearn'",
        "WARNING: Dependency 'requests' is deprecated, use 'httpx'",
        "WARNING: Dependency 'optparse' is deprecated",
        "WARNING: 'datetime.datetime.utcnow' is deprecated",
        "WARNING: Using deprecated API",
        "WARNING: Package 'urllib3' has a new version, upgrade recommended",
        "WARNING: 'collections.abc' will be removed in Python 3.12",
    ],
    "Permissions": [
        "permission denied: '/var/jenkins_home'",
        "Permission denied: '/usr/local/bin/docker'",
        "Permission denied: '/root/.ssh/authorized_keys'",
        "EACCES: permission denied, open '/etc/config'",
    ],
    "Linting": [
        "E302 expected 2 blank lines, found 1",
        "E501 line too long (95 > 79 characters)",
        "E501 line too long (120 > 79 characters)",
        "F401 'os' imported but unused",
        "F401 'json' imported but unused",
        "F841 local variable 'e' is assigned to but never used",
        "W291 trailing whitespace",
        "W292 no newline at end of file",
        "W503 line break before binary operator",
        "src/analyzer.py:1:1: F401 'os' imported but unused",
        "src/analyzer.py:2:1: F401 'json' imported but unused",
        "src/analyzer.py:81:5: F841 local variable 'z' is assigned to but never used",
        "src/analyzer.py:1:0: W0611: Unused import os (unused-import)",
        "src/analyzer.py:3:0: W0611: Unused import time (unused-import)",
        "src/analyzer.py:81:4: W0612: Unused variable 'z' (unused-variable)",
        "src/data_loader.py:12:7: C0117: Consider changing unnecessary-negation",
        "src/reporter.py:54:4: C0415: Import outside toplevel (import-outside-toplevel)",
    ],
    "Security": [
        "WARNING: hardcoded password found in config.py",
        "WARNING: Security vulnerability detected in requests",
        "WARNING: hard-coded password: 'admin123'",
        "B105 hard-coded password string",
        "B106 hardcoded_password_string",
        "WARNING: unsafe deserialization in main.py",
        "WARNING: SQL injection risk in query.py",
        "WARNING: insecure HTTP connection detected",
        "WARNING: sensitive data exposed in logs",
    ],
    "Performance": [
        "WARNING: Test timeout approaching, consider optimizing",
        "WARNING: slow query detected in database.py",
        "WARNING: memory usage above 80%",
        "WARNING: cache directory full",
        "WARNING: N+1 query detected in repository.py",
        "WARNING: large file upload may cause timeout",
        "WARNING: response time exceeded threshold",
    ],
    "Code Quality": [
        "WARNING: Unused import 'os' in src/analyzer.py",
        "WARNING: Unused variable 'x' in main.py",
        "WARNING: Missing docstring in calculate_total_sales",
        "WARNING: duplicate key in dictionary",
        "WARNING: complex function detected in analyzer.py",
        "WARNING: code duplication found in utils.py",
        "WARNING: magic number 42 in calculation",
        "WARNING: deeply nested code in process.py",
        "src/analyzer.py:9:1: W0511: TODO: Refactor this function (fixme)",
        "src/analyzer.py:10:1: W0511: FIXME: Remove hardcoded values (fixme)",
        "src/data_loader.py:1:0: C0114: Missing module docstring (missing-module-docstring)",
        "src/reporter.py:1:0: C0114: Missing module docstring (missing-module-docstring)",
        "src/analyzer.py:1:0: C0114: Missing module docstring (missing-module-docstring)",
    ],
    "Git": [
        "ERROR: git clone failed",
        "ERROR: not in a git directory",
        "fatal: not a git repository",
        "ERROR: Could not resolve host: github.com",
        "WARNING: git branch has diverged from remote",
        "WARNING: uncommitted changes in working directory",
    ],
    "Docker": [
        "docker: Error response from daemon: driver failed",
        "docker: Error response from daemon: container not found",
        "Cannot connect to the Docker daemon",
    ],
    "Network": [
        "ERROR: Connection refused",
        "ERROR: Connection timed out",
        "ERROR: Could not resolve host",
        "requests.exceptions.ConnectionError",
        "WARNING: retrying connection after timeout",
        "WARNING: slow response from server",
        "WARNING: DNS resolution slow",
        "WARNING: SSL certificate expiring soon",
    ],
}

category_to_severity = {
    "Types": "High",
    "Tests": "High",
    "Dependencies": "Critical",
    "Permissions": "Critical",
    "Linting": "Low",
    "Security": "Critical",
    "Performance": "Medium",
    "Code Quality": "Low",
    "Git": "Critical",
    "Docker": "High",
    "Network": "High",
}

texts = []
category_labels = []
severity_labels = []

for category, examples in training_data.items():
    for text in examples:
        texts.append(text)
        category_labels.append(category)
        severity_labels.append(category_to_severity[category])

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

category_model = MultinomialNB()
category_model.fit(X, category_labels)

severity_model = MultinomialNB()
severity_model.fit(X, severity_labels)

with open('category_model.pkl', 'wb') as f:
    pickle.dump((vectorizer, category_model), f)

with open('severity_model.pkl', 'wb') as f:
    pickle.dump((vectorizer, severity_model), f)

print(f"Models trained on {len(texts)} examples!")
