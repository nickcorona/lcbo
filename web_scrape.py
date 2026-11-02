import configparser
import os
import platform
import shutil
import tempfile
import time

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def web_scrape_lcbo_store_inventory():
    """Scrape the LCBO store inventory page and download the CSV file"""
    # Read the configuration file
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Get the store number
    store_number = config.get("DEFAULT", "store_number")

    # Centralize selectors
    SELECTORS = {
        "first_button": "#store_inventory_table > div.bootstrap-table > div.fixed-table-container > div.fixed-table-pagination > div.pull-left.pagination-detail > span.page-list > span > button > span.page-size",
        "second_button": "#store_inventory_table > div.bootstrap-table > div.fixed-table-container > div.fixed-table-pagination > div.pull-left.pagination-detail > span.page-list > span > ul > li:nth-child(4) > a",
        "third_button": "#store_inventory_table > div.bootstrap-table > div.fixed-table-toolbar > div.columns.columns-left.btn-group.pull-left > div.export.btn-group > button",
        "fourth_button": "#store_inventory_table > div.bootstrap-table > div.fixed-table-toolbar > div.columns.columns-left.btn-group.pull-left > div.export.btn-group.open > ul > li:nth-child(3) > a",
    }

    # Function to handle button click
    def click_button(wait, selector, max_attempts=3):
        for _ in range(max_attempts):
            try:
                button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                button.click()
                break
            except StaleElementReferenceException:
                continue

    # Bundled driver on Windows; elsewhere (CI) let Selenium find chromedriver
    if platform.system() == "Windows":
        webdriver_service = Service("chromedriver-win64/chromedriver.exe")
    else:
        webdriver_service = Service()

    # Download into an empty temp dir so we can't pick up an unrelated CSV
    download_dir = tempfile.mkdtemp()

    # Set Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,  # To auto download the file
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,  # To download pdf files
        },
    )
    driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)

    # Load webpage
    driver.get(f"https://lcbo.watch/store-inventory/{store_number}")

    # Wait for the page to load completely
    wait = WebDriverWait(driver, 20)

    # Click buttons
    click_button(wait, SELECTORS["first_button"])
    click_button(wait, SELECTORS["second_button"])
    click_button(wait, SELECTORS["third_button"])
    click_button(wait, SELECTORS["fourth_button"])

    # Wait for the download to complete
    csv_files = []
    for _ in range(60):
        csv_files = [f for f in os.listdir(download_dir) if f.endswith(".csv")]
        if csv_files:
            break
        time.sleep(1)
    if not csv_files:
        driver.quit()
        raise RuntimeError("Inventory CSV was not downloaded")

    # Overwrite the inventory file
    shutil.move(os.path.join(download_dir, csv_files[0]), "LCBO_store_inventory.csv")

    # Close the browser
    driver.quit()


if __name__ == "__main__":
    web_scrape_lcbo_store_inventory()
