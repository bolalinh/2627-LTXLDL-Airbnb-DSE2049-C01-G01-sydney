
import tempfile
from pathlib import Path

import pandas as pd

# Import these functions from your qa.py module.
# Adjust the import path to match your project.
from src.qa import add, write_reports


def test_qa_report():

    report = []

    # Test 1: Old add() call using record_id.
    add(
        report,
        "WARNING",
        "2026-06-16",
        "listings.csv",
        "price_missing",
        "Missing value in price.",
        report_level="RECORD_LEVEL",
        record_id="1001",
    )

    # Test 2: New add() call using listing_id and price.
    add(
        report,
        "WARNING",
        "2026-06-16",
        "listings.csv",
        "price_iqr_outliers_sample",
        "Price exceeds IQR upper bound.",
        report_level="RECORD_LEVEL",
        date="2026-06-16",
        listing_id="1002",
        price=15000,
    )

    # Test 3: CHECK_LEVEL summary.
    add(
        report,
        "WARNING",
        "2026-06-16",
        "listings.csv",
        "price_missing",
        "10 listings missing price.",
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        output_path = write_reports(
            report,
            Path(temp_dir)
        )

        df = pd.read_csv(
            output_path,
            dtype=str,
            keep_default_na=False
        )

        print("\n=== TEST RESULT ===")
        print(df.to_string(index=False))

        # Check new columns.
        required_columns = [
            "snapshot",
            "date",
            "listing_id",
            "price",
            "flag",
            "severity",
            "message",
        ]

        for column in required_columns:
            assert column in df.columns, (
                f"Missing column: {column}"
            )

        # Check backward compatibility.
        assert df.loc[0, "listing_id"] == "1001"

        # Check new record-level fields.
        assert df.loc[1, "listing_id"] == "1002"
        assert df.loc[1, "price"] == "15000"
        assert df.loc[1, "date"] == "2026-06-16"

        # Check flag mapping.
        assert df.loc[0, "flag"] == "MISSING_PRICE"
        assert df.loc[1, "flag"] == "PRICE_OUTLIER"

        # Check summary rows.
        summary = df[df["report_level"] == "CHECK_LEVEL"]

        assert len(summary) == 1
        assert summary.iloc[0]["listing_id"] == ""
        assert summary.iloc[0]["price"] == ""

        print("\nALL TESTS PASSED!")


if __name__ == "__main__":
    test_qa_report()
