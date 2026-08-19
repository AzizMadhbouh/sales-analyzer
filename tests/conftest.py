"""Pytest configuration and shared fixtures."""
import pytest
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture
def sample_csv_path():
    """Path to the sample sales CSV file."""
    return str(DATA_DIR / "sample_sales.csv")


@pytest.fixture
def sample_data():
    """Sample sales data as list of dictionaries."""
    return [
        {"date": "2026-01-15", "product": "Widget A", "quantity": "10", "price": "29.99"},
        {"date": "2026-01-15", "product": "Widget B", "quantity": "5", "price": "49.99"},
        {"date": "2026-01-16", "product": "Widget A", "quantity": "8", "price": "29.99"},
        {"date": "2026-01-16", "product": "Widget C", "quantity": "3", "price": "99.99"},
    ]


@pytest.fixture
def cleaned_data():
    """Cleaned sales data with proper types."""
    return [
        {"date": "2026-01-15", "product": "Widget A", "quantity": 10, "price": 29.99},
        {"date": "2026-01-15", "product": "Widget B", "quantity": 5, "price": 49.99},
        {"date": "2026-01-16", "product": "Widget A", "quantity": 8, "price": 29.99},
        {"date": "2026-01-16", "product": "Widget C", "quantity": 3, "price": 99.99},
    ]


@pytest.fixture
def single_row():
    """Single row of sales data."""
    return [
        {"date": "2026-01-15", "product": "Widget A", "quantity": 10, "price": 29.99},
    ]


@pytest.fixture
def empty_data():
    """Empty dataset."""
    return []
