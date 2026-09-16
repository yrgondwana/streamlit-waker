from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import os

# Replace this with your actual Streamlit app URL
STREAMLIT_URL = os.environ.get(
    "STREAMLIT_APP_URL",
    "https://potential-winterkill-dashboard.streamlit.app/"
)

# Robust XPath: matches on ALL descendant text (., not text()) so it still
# finds the button even if Streamlit wraps the label in a nested <span>/<p>.
# Also matches on a shorter, stable substring ("get this app back up")
# so it survives minor copy changes (e.g. added "!" or emoji).
WAKE_BUTTON_XPATH = "//button[contains(., 'get this app back up')]"


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(STREAMLIT_URL)
        print(f"Opened {STREAMLIT_URL}")
        print(f"Page title: {driver.title}")

        # Give the page a moment to fully render before we start polling,
        # since Streamlit's sleep/wake screen can take a beat to mount.
        wait = WebDriverWait(driver, 20)

        try:
            # Look for the wake-up button
            button = wait.until(
                EC.element_to_be_clickable((By.XPATH, WAKE_BUTTON_XPATH))
            )
            print("Wake-up button found. Clicking...")
            button.click()

            # After clicking, check if it disappears
            try:
                wait.until(
                    EC.invisibility_of_element_located((By.XPATH, WAKE_BUTTON_XPATH))
                )
                print("Button clicked and disappeared (app should be waking up)")
            except TimeoutException:
                print("Button was clicked but did NOT disappear (possible failure)")
                # Debug aid: dump a snippet of the page source so failures are
                # diagnosable from the Actions log instead of a silent guess.
                print("--- Page source snippet for debugging ---")
                print(driver.page_source[:2000])
                exit(1)

        except TimeoutException:
            # No button at all -> app is assumed to be awake.
            # Print a page source snippet here too, since a mismatched XPath
            # would ALSO land in this branch and look identical to "already awake".
            print("No wake-up button found. Assuming app is already awake.")
            print("--- Page source snippet (for verifying assumption) ---")
            print(driver.page_source[:1000])

    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)

    finally:
        driver.quit()
        print("Script finished.")


if __name__ == "__main__":
    main()
