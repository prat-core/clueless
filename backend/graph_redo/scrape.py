from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import os

def open_firefox_with_profile():
    """
    Opens Firefox using Selenium with the default user profile to preserve
    logged-in websites and user cookies.
    """
    options = Options()

    # Use the specific Firefox profile to preserve cookies and sessions
    # Firefox profiles are typically stored in ~/.mozilla/firefox/
    profile_path = os.path.expanduser("~/.mozilla/firefox")
    specific_profile = os.path.join(profile_path, "708iiqgx.Prat")

    # Use the specific profile directory
    if os.path.exists(specific_profile):
        options.add_argument(f"-profile")
        options.add_argument(specific_profile)

    # Create Firefox driver with the profile
    driver = webdriver.Firefox(options=options)

    return driver

if __name__ == "__main__":
    # Example usage
    browser = open_firefox_with_profile()
    browser.get("https://modal.com/notebooks/pratyaksh-mishra22/")
    input("Press Enter to close the browser...")
    browser.quit()