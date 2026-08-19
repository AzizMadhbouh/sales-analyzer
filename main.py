import sys
from pathlib import Path

from src.data_loader import load_csv, validate_sales_data
from src.reporter import generate_csv_report, generate_text_report

def main():
    # Define paths
    base_dir = Path(__file__).resolve().parent
    data_path = base_dir / "data" / "sample_sales.csv"
    output_path = base_dir / "data" / "sales_report_summary.csv"

    print(f"Loading data from: {data_path}")
    try:
        raw_data = load_csv(str(data_path))
    except FileNotFoundError:
        print(f"Error: Could not find '{data_path}'", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("Validating and cleaning sales data...")
    try:
        cleaned_data = validate_sales_data(raw_data)
    except ValueError as e:
        print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nGenerating report summary...\n")
    report_text = generate_text_report(cleaned_data)
    print(report_text)

    print(f"\nExporting detailed report to: {output_path}")
    generate_csv_report(cleaned_data, str(output_path))
    print("Done!")

if __name__ == "__main__":
    main()
