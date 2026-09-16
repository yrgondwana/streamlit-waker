from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import os
import time

# Replace this with your actual Streamlit app URL
STREAMLIT_URL = os.environ.get(
    "STREAMLIT_APP_URL",
    "https://potential-winterkill-dashboard.streamlit.app/"
)

# Robust XPath: matches on ALL descendant text (., not text()) so it still
# finds the button even if Streamlit wraps the label in a nested <span>/<p>.
WAKE_BUTTON_XPATH = "//button[contains(., 'get this app back up')]"

# Streamlit tabs render as elements with role="tab". This matches any of
# them regardless of label text (emoji, wording changes, etc.) so it
# doesn't need updating if tab names change later.
TAB_XPATH = "//button[@role='tab']"

# The dashboard's landing page ("Overview") has no tabs — tabs only exist
# on the "DL Pipeline" and "Results" sidebar sections. This matches the
# sidebar navigation label for a section that does have tabs, so the
# waker actually has something to click once it gets there.
SIDEBAR_SECTION_XPATH = "//label[.//div[contains(text(), 'DL Pipeline')]]"


def wake_app(driver, wait):
    """Load the URL and click the sleep-screen wake button if present.
    Returns True if the app was asleep and we woke it, False if it was
    already awake."""
    driver.get(STREAMLIT_URL)
    print(f"Opened {STREAMLIT_URL}")
    print(f"Page title: {driver.title}")

    # Streamlit is a client-side rendered app: the initial HTML document
    # can finish loading (analytics scripts, boilerplate shell) before
    # the actual app content has mounted. Wait for either the real app
    # container OR the sleep-screen wake button before doing anything
    # else, so we don't mistake a still-loading page for either state.
    try:
        WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.XPATH, "//div[@data-testid='stAppViewContainer']")
            or d.find_elements(By.XPATH, WAKE_BUTTON_XPATH)
        )
    except TimeoutException:
        print("Neither the app content nor a wake button appeared in time.")
        print("--- Page HTML snippet for debugging ---")
        print(driver.page_source[:3000])
        return False

    try:
        button = wait.until(
            EC.element_to_be_clickable((By.XPATH, WAKE_BUTTON_XPATH))
        )
        print("Wake-up button found. Clicking...")
        button.click()

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

        return True

    except TimeoutException:
        print("No wake-up button found. Assuming app is already awake.")
        return False


def navigate_to_section_with_tabs(driver):
    """The landing page ("Overview") has no tabs. Click the "DL Pipeline"
    sidebar option so the page that actually has tabs is loaded, giving
    simulate_activity() something real to interact with."""
    try:
        section = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SIDEBAR_SECTION_XPATH))
        )
        driver.execute_script("arguments[0].click();", section)
        print("Clicked sidebar section: DL Pipeline")
        # Let the section's content (including its tabs) render.
        time.sleep(3)
        return True
    except TimeoutException:
        print("Could not find the 'DL Pipeline' sidebar option — staying on current page.")
        # Debug aid: dump the full page HTML so the XPath can be
        # corrected against the real DOM instead of guessed again.
        print("--- Full page HTML snippet for debugging ---")
        print(driver.page_source[:5000])
        return False


def simulate_activity(driver, wait):
    """Click through any visible tabs to mimic real user interaction,
    rather than just loading the page. This is meant to register as
    genuine usage rather than a bare bot pageview."""
    try:
        # Give the app a little extra time to finish rendering widgets
        # after boot/reboot, since tabs may mount slightly after the
        # main page shell does.
        tabs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.XPATH, TAB_XPATH))
        )
        print(f"Found {len(tabs)} tab(s) to interact with.")

        # Re-locate tabs before each click: clicking one can cause a
        # partial re-render, which would otherwise make earlier
        # references stale.
        tab_count = len(tabs)
        for i in range(tab_count):
            try:
                current_tabs = driver.find_elements(By.XPATH, TAB_XPATH)
                if i >= len(current_tabs):
                    break
                tab = current_tabs[i]
                label = tab.text.strip() or f"tab {i}"
                driver.execute_script("arguments[0].click();", tab)
                print(f"Clicked tab: {label}")
                # Small pause so the click registers as real dwell time,
                # not an instant machine-gun click-through.
                time.sleep(2)
            except Exception as e:
                print(f"Could not click tab {i}: {e}")

    except TimeoutException:
        print("No tabs found on this page — skipping tab interaction.")


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
        wait = WebDriverWait(driver, 20)

        was_asleep = wake_app(driver, wait)

        # If it was asleep, give the container a bit longer to fully
        # boot and render the real dashboard content before we try to
        # interact with it.
        if was_asleep:
            time.sleep(10)

        navigate_to_section_with_tabs(driver)
        simulate_activity(driver, wait)

    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)

    finally:
        driver.quit()
        print("Script finished.")


if __name__ == "__main__":
    main()
