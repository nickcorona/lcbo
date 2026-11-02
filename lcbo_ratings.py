import json
import pandas as pd

MIN_RATING = 3.5  # Don't recommend anything rated below this
BASELINE_RATING = 3.0  # Rating treated as zero quality premium
TOP_N = 3  # Recommendations per category


def load_config():
    with open("config.json") as config_file:
        config = json.load(config_file)
    return config["beer_dict"]


def load_and_prepare_data(beer_dict):
    # Load the inventory data
    df = pd.read_csv("LCBO_store_inventory.csv")

    # Extract can and Size information
    df[["Quantity", "Size"]] = df["Format"].str.extract(
        r"(?:(\d+)?\s*x\s*)?(\d+ mL.*)", expand=True
    )

    # Clean up the cans column
    df["Quantity"] = df["Quantity"].str.extract(r"(\d+)").fillna(1).astype(float)

    # Clean up the Size column
    df["Size"] = df["Size"].str.extract(r"(\d+)").fillna(df["Quantity"]).astype(int)

    # Calculate total volume
    df["Volume"] = df["Quantity"] * df["Size"]

    # Clean up the Price column and convert it to float
    df["Price"] = df["Price"].str.replace("$", "").str.split("\n").str[0].astype(float)

    # Calculate price per volume
    df["dollar_per_volume"] = df["Price"] / df["Volume"]

    # Extract ratings and convert them to float
    df["Rating"] = df["Rating"].str.split("/5").str[0].fillna(0).astype(float)

    # Apply a minimum rating threshold
    df = df[df["Rating"] >= MIN_RATING]

    # Value = rating points above a baseline, per dollar per mL. Untappd ratings
    # are compressed (median ~3.4, 95th pct ~4.0), so Rating**2 / price let a
    # cheap 3.5 beat a 4.2 at a small premium. Measuring quality as distance
    # above a "drinkable but nothing special" baseline makes rating gaps count.
    df["value"] = (df["Rating"] - BASELINE_RATING) / df["dollar_per_volume"]

    # Map beer types to categories
    df["Category"] = df["Style"].apply(
        lambda x: next((k for k, v in beer_dict.items() if x in v), "Other")
    )

    return df


def lcbo_ratings():
    """Process and rate the beers"""
    beer_dict = load_config()
    df = load_and_prepare_data(beer_dict)

    # One row per beer: keep the format (single, 4-pack, 6-pack...) with the
    # best value so the same beer can't take several slots in a category
    df = df.sort_values(["value", "Rating"], ascending=False)
    df = df.drop_duplicates(subset="Name", keep="first")

    # Top N per category, ranked 1..N
    df = df.sort_values(["Category", "value", "Rating"], ascending=[True, False, False])
    df = df.groupby("Category").head(TOP_N)
    df["Rank"] = df.groupby("Category").cumcount() + 1
    df = df.set_index(["Category", "Rank"])
    df.index.names = [None, None]

    # Filter the DataFrame to include only the necessary columns
    df = df[["Name", "Rating", "Price", "Quantity"]]
    df.to_csv("LCBO_best_value.csv")
    print(df)


if __name__ == "__main__":
    lcbo_ratings()
