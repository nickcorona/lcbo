import logging

import dotenv

from lcbo_ratings import lcbo_ratings
from web_scrape import web_scrape_lcbo_store_inventory


def run_all_processes():
    # Load environment variables
    dotenv.load_dotenv()

    # Refresh inventory. If the scrape breaks (site down, layout change), keep
    # ranking the last good CSV so the site still updates with any code changes.
    try:
        web_scrape_lcbo_store_inventory()
    except Exception:
        logging.exception("Inventory scrape failed, using existing LCBO_store_inventory.csv")

    # Process and rate the beers
    lcbo_ratings()


if __name__ == "__main__":
    run_all_processes()
