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
    ],
    "Security": [
        "WARNING: hardcoded password found in config.py",
        "WARNING: Security vulnerability detected in requests",
        "WARNING: hard-coded password: 'admin123'",
        "B105 hard-coded password string",
        "B106 hardcoded_password_string",
        "WARNING: unsafe deserialization in main.py",
    ],
    "Performance": [
        "WARNING: Test timeout approaching, consider optimizing",
        "WARNING: slow query detected in database.py",
        "WARNING: memory usage above 80%",
        "WARNING: cache directory full",
    ],
    "Code Quality": [
        "WARNING: Unused import 'os' in src/analyzer.py",
        "WARNING: Unused variable 'x' in main.py",
        "WARNING: Missing docstring in calculate_total_sales",
        "WARNING: duplicate key in dictionary",
    ],
    "Git": [
        "ERROR: git clone failed",
        "ERROR: not in a git directory",
        "fatal: not a git repository",
        "ERROR: Could not resolve host: github.com",
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
