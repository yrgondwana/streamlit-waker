import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os

# Replace this with your actual Streamlit app URL
STREAMLIT_URL = os.environ.get(
    "STREAMLIT_APP_URL",
    "https://potential-winterkill-dashboard.streamlit.app/"
)

# Robust XPath: matches on ALL descendant text (., not text()) so it still
# finds the button even if Streamlit wraps the label in a nested <span>/<p>.
WAKE_BUTTON_XPATH = "//button[contains(., 'get this app back up')]"

# Any real Streamlit app renders this container. Its presence is how we
# tell "genuinely loaded the real app" apart from a generic/blocked shell
# page — which is the exact false-positive the previous script suffered
# from ("no wake button found" being wrongly read as "already awake").
APP_CONTAINER_XPATH = "//div[@data-testid='stAppViewContainer']"


def main():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # undetected-chromedriver manages its own patched driver binary, so
    # no Service/ChromeDriverManager setup is needed here — that's the
    # main structural difference from the previous script.
    driver = uc.Chrome(options=options)

    try:
        driver.get(STREAMLIT_URL)
        print(f"Opened {STREAMLIT_URL}")
        print(f"Page title: {driver.title}")

        wait = WebDriverWait(driver, 20)

        # Wait for EITHER the real app content or the wake button —
        # whichever shows up first. If neither does, we know we hit the
        # generic/blocked shell rather than assuming "already awake".
        try:
            wait.until(
                lambda d: d.find_elements(By.XPATH, APP_CONTAINER_XPATH)
                or d.find_elements(By.XPATH, WAKE_BUTTON_XPATH)
            )
        except TimeoutException:
            print("Neither app content nor wake button appeared — likely hit a blocked/generic shell.")
            print("--- Page source snippet for debugging ---")
            print(driver.page_source[:2000])
            exit(1)

        wake_buttons = driver.find_elements(By.XPATH, WAKE_BUTTON_XPATH)
        if wake_buttons:
            print("Wake-up button found. Clicking...")
            wake_buttons[0].click()

            try:
                wait.until(
                    EC.invisibility_of_element_located((By.XPATH, WAKE_BUTTON_XPATH))
                )
                print("Button clicked and disappeared (app is waking up)")
            except TimeoutException:
                print("Button was clicked but did NOT disappear (possible failure)")
                print("--- Page source snippet for debugging ---")
                print(driver.page_source[:2000])
                exit(1)
        else:
            print("No wake-up button found, and real app content is present — app is already awake.")

    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)

    finally:
        driver.quit()
        print("Script finished.")


if __name__ == "__main__":
    main()
