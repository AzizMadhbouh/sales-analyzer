import pytest
from src.data_loader import load_csv, validate_sales_data


class TestLoadCSV:
    """Tests for the load_csv function."""

    def test_load_valid_csv(self, sample_csv_path):
        """Should load CSV file and return list of dicts."""
        data = load_csv(sample_csv_path)

        assert isinstance(data, list)
        assert len(data) == 10
        assert "date" in data[0]
        assert "product" in data[0]
        assert "quantity" in data[0]
        assert "price" in data[0]

    def test_load_nonexistent_file(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_csv("nonexistent.csv")

    def test_load_non_csv_file(self, tmp_path):
        """Should raise ValueError for non-CSV files."""
        txt_file = tmp_path / "data.txt"
        txt_file.write_text("hello")

        with pytest.raises(ValueError):
            load_csv(str(txt_file))

    def test_csv_row_count(self, sample_csv_path):
        """Should load all rows from CSV."""
        data = load_csv(sample_csv_path)

        assert len(data) == 10

    def test_csv_values_are_strings(self, sample_csv_path):
        """CSV loader returns raw string values."""
        data = load_csv(sample_csv_path)

        assert isinstance(data[0]["quantity"], str)
        assert isinstance(data[0]["price"], str)


class TestValidateSalesData:
    """Tests for the validate_sales_data function."""

    def test_validate_valid_data(self, sample_data):
        """Should clean and return validated data."""
        result = validate_sales_data(sample_data)

        assert len(result) == 4
        assert result[0]["quantity"] == 10
        assert result[0]["price"] == 29.99

    def test_validate_empty_data(self):
        """Should raise ValueError for empty data."""
        with pytest.raises(ValueError, match="empty"):
            validate_sales_data([])

    def test_validate_missing_columns(self):
        """Should raise ValueError for missing required columns."""
        bad_data = [{"date": "2026-01-15", "product": "Widget"}]

        with pytest.raises(ValueError, match="Missing required columns"):
            validate_sales_data(bad_data)

    def test_validate_converts_types(self, sample_data):
        """Should convert quantity to int and price to float."""
        result = validate_sales_data(sample_data)

        assert isinstance(result[0]["quantity"], int)
        assert isinstance(result[0]["price"], float)

    def test_validate_skips_bad_rows(self):
        """Should skip rows with invalid data."""
        mixed_data = [
            {
                "date": "2026-01-15",
                "product": "Widget A",
                "quantity": "10",
                "price": "29.99",
            },
            {
                "date": "2026-01-15",
                "product": "Widget B",
                "quantity": "invalid",
                "price": "49.99",
            },
            {
                "date": "2026-01-15",
                "product": "Widget C",
                "quantity": "5",
                "price": "99.99",
            },
        ]

        result = validate_sales_data(mixed_data)

        assert len(result) == 2
