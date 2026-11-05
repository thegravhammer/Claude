import datetime
import sys

import pandas as pd
from numbers_parser import Document


def load_gladiator(path: str) -> pd.DataFrame:
    """Load the 'Gas Stops' table of the Jeep Gladiator (2020) sheet as a DataFrame."""
    table = Document(path).sheets["Jeep Gladiator (2020)"].tables["Gas Stops"]
    rows = table.rows(values_only=True)
    header = [h for h in rows[0] if h]  # drop the unnamed trailing column
    df = pd.DataFrame([r[: len(header)] for r in rows[1:]], columns=header)

    # Drop empty rows at the bottom of the table
    df = df.dropna(how="all")

    # Cells formatted as durations in Numbers (row of 2025-08-12) can't be read as numbers
    num_cols = ["Mileage", "Volume (Gal)", "Octane", "Price", "Total", "Filled to"]
    for c in num_cols:
        df[c] = pd.to_numeric(
            df[c].map(lambda v: None if isinstance(v, datetime.timedelta) else v),
            errors="coerce",
        )

    df["Date"] = pd.to_datetime(df["Date"])
    # One odometer reading (2024-04-07, Blue Springs MO) holds 43.84, the fill-up total, not a mileage
    df.loc[df["Mileage"] % 1 != 0, "Mileage"] = pd.NA
    df["Mileage"] = df["Mileage"].astype("Int64")
    df["Octane"] = df["Octane"].astype("Int64")
    for c in ["Location", "Type of Miles"]:
        df[c] = (
            df[c].str.replace(r"\s+", " ", regex=True).str.strip().replace("", pd.NA)
        )
    return df.reset_index(drop=True)


if __name__ == "__main__":
    df = load_gladiator(sys.argv[1])
    pd.set_option("display.width", 200, "display.max_columns", 20, "display.max_colwidth", 40)
    df.info()
    print()
    print(df.head(10))
    print()
    print(df.describe())
