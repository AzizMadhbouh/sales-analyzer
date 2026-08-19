import pytest
from src.analyzer import (
    calculate_average_order_value,
    calculate_total_sales,
    get_daily_sales,
    get_quantity_by_product,
    get_top_products,
)


class TestCalculateTotalSales:
    """Tests for calculate_total_sales."""

    def test_total_sales_basic(self, cleaned_data):
        """Should calculate total revenue correctly."""
        total = calculate_total_sales(cleaned_data)

        # 10*29.99 + 5*49.99 + 8*29.99 + 3*99.99
        expected = 299.90 + 249.95 + 239.92 + 299.97
        assert total == round(expected, 2)

    def test_total_sales_single_row(self, single_row):
        """Should calculate total for single transaction."""
        total = calculate_total_sales(single_row)

        assert total == 299.90

    def test_total_sales_empty(self, empty_data):
        """Should return 0 for empty data."""
        total = calculate_total_sales(empty_data)

        assert total == 0.0


class TestCalculateAverageOrderValue:
    """Tests for calculate_average_order_value."""

    def test_average_basic(self, cleaned_data):
        """Should calculate average order value."""
        avg = calculate_average_order_value(cleaned_data)

        assert avg > 0
        assert isinstance(avg, float)

    def test_average_empty(self, empty_data):
        """Should return 0 for empty data."""
        avg = calculate_average_order_value(empty_data)

        assert avg == 0.0

    def test_average_single_row(self, single_row):
        """Should return the value of the single order."""
        avg = calculate_average_order_value(single_row)

        assert avg == 299.90


class TestGetTopProducts:
    """Tests for get_top_products."""

    def test_top_products_default(self, cleaned_data):
        """Should return top 3 products by default."""
        top = get_top_products(cleaned_data)

        assert len(top) <= 3
        assert isinstance(top, list)
        assert isinstance(top[0], tuple)

    def test_top_products_sorted_desc(self, cleaned_data):
        """Should be sorted by revenue descending."""
        top = get_top_products(cleaned_data)

        revenues = [rev for _, rev in top]
        assert revenues == sorted(revenues, reverse=True)

    def test_top_products_custom_n(self, cleaned_data):
        """Should respect custom n parameter."""
        top = get_top_products(cleaned_data, n=1)

        assert len(top) == 1

    def test_top_products_empty(self, empty_data):
        """Should return empty list for empty data."""
        top = get_top_products(empty_data)

        assert top == []


class TestGetDailySales:
    """Tests for get_daily_sales."""

    def test_daily_sales_basic(self, cleaned_data):
        """Should group sales by date."""
        daily = get_daily_sales(cleaned_data)

        assert isinstance(daily, dict)
        assert "2026-01-15" in daily
        assert "2026-01-16" in daily

    def test_daily_sales_sorted(self, cleaned_data):
        """Should be sorted by date."""
        daily = get_daily_sales(cleaned_data)

        dates = list(daily.keys())
        assert dates == sorted(dates)

    def test_daily_sales_values(self, cleaned_data):
        """Should calculate correct daily totals."""
        daily = get_daily_sales(cleaned_data)

        # 2026-01-15: 10*29.99 + 5*49.99 = 549.85
        assert daily["2026-01-15"] == 549.85

    def test_daily_sales_empty(self, empty_data):
        """Should return empty dict for empty data."""
        daily = get_daily_sales(empty_data)

        assert daily == {}


class TestGetQuantityByProduct:
    """Tests for get_quantity_by_product."""

    def test_quantity_basic(self, cleaned_data):
        """Should sum quantities per product."""
        quantities = get_quantity_by_product(cleaned_data)

        assert quantities["Widget A"] == 18  # 10 + 8
        assert quantities["Widget B"] == 5
        assert quantities["Widget C"] == 3

    def test_quantity_sorted(self, cleaned_data):
        """Should be sorted alphabetically."""
        quantities = get_quantity_by_product(cleaned_data)

        keys = list(quantities.keys())
        assert keys == sorted(keys)

    def test_quantity_empty(self, empty_data):
        """Should return empty dict for empty data."""
        quantities = get_quantity_by_product(empty_data)

        assert quantities == {}
