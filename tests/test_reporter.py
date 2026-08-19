from src.reporter import generate_csv_report, generate_text_report


class TestGenerateTextReport:
    """Tests for generate_text_report."""

    def test_report_contains_header(self, cleaned_data):
        """Report should contain the header."""
        report = generate_text_report(cleaned_data)

        assert "SALES REPORT" in report

    def test_report_contains_summary(self, cleaned_data):
        """Report should contain summary stats."""
        report = generate_text_report(cleaned_data)

        assert "Total Revenue" in report
        assert "Total Orders" in report
        assert "Avg Order Value" in report

    def test_report_contains_top_products(self, cleaned_data):
        """Report should list top products."""
        report = generate_text_report(cleaned_data)

        assert "Top" in report
        assert "Widget" in report

    def test_report_contains_daily_sales(self, cleaned_data):
        """Report should show daily sales."""
        report = generate_text_report(cleaned_data)

        assert "Daily Sales" in report
        assert "2026-01-15" in report

    def test_report_order_count(self, cleaned_data):
        """Report should show correct order count."""
        report = generate_text_report(cleaned_data)

        assert "4" in report  # 4 orders in cleaned_data

    def test_report_empty_data(self, empty_data):
        """Should handle empty data gracefully."""
        report = generate_text_report(empty_data)

        assert "SALES REPORT" in report
        assert "Total Orders:     0" in report


class TestGenerateCSVReport:
    """Tests for generate_csv_report."""

    def test_creates_csv_file(self, cleaned_data, tmp_path):
        """Should create a CSV file."""
        output = tmp_path / "report.csv"

        generate_csv_report(cleaned_data, str(output))

        assert output.exists()

    def test_csv_has_revenue_column(self, cleaned_data, tmp_path):
        """Output CSV should include revenue column."""
        output = tmp_path / "report.csv"

        generate_csv_report(cleaned_data, str(output))

        content = output.read_text()
        assert "revenue" in content

    def test_csv_row_count(self, cleaned_data, tmp_path):
        """Output CSV should have same rows as input + header."""
        output = tmp_path / "report.csv"

        generate_csv_report(cleaned_data, str(output))

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 5  # header + 4 data rows

    def test_csv_revenue_calculation(self, single_row, tmp_path):
        """Revenue should be quantity * price."""
        output = tmp_path / "report.csv"

        generate_csv_report(single_row, str(output))

        content = output.read_text()
        assert "299.9" in content
