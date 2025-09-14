#!/usr/bin/env python3
"""
Simple Firefox launcher using Selenium with default profile
"""

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
import time
import sys
import os


def launch_firefox_default_profile():
    """
    Launch Firefox using Selenium with the default profile
    """
    try:
        # Create Firefox options
        options = Options()
        
        # Use default profile (Firefox will use the default profile if none specified)
        # Alternatively, you can specify a profile path:
        # firefox_options.add_argument('-profile')
        # firefox_options.add_argument('/path/to/your/profile')

            # Use specific Firefox profile to preserve cookies and sessions
        profile_path = os.path.expanduser("/Users/ritesh/Library/Application Support/Firefox/Profiles/")
        specific_profile = os.path.join(profile_path, "ra0lmepf.default-release")

        if os.path.exists(specific_profile):
            options.add_argument("-profile")
            options.add_argument(specific_profile)

        # Create Firefox driver with profile
        self.selenium_driver = webdriver.Firefox(options=options)
        
        # Initialize the Firefox driver
        print("Launching Firefox with default profile...")
        driver = webdriver.Firefox(options=firefox_options)
        
        # Navigate to a default page (optional)
        driver.get("https://modal.com/apps/ritesh3280-1/main")
        
        print("Firefox launched successfully!")
        print("Browser will stay open. Press Ctrl+C to close.")
        
        # Keep the browser open until user interrupts
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nClosing Firefox...")
            driver.quit()
            print("Firefox closed.")
            
    except Exception as e:
        print(f"Error launching Firefox: {e}")
        print("Make sure you have:")
        print("1. Firefox installed")
        print("2. geckodriver installed and in PATH")
        print("3. selenium package installed: pip install selenium")
        sys.exit(1)


if __name__ == "__main__":
    launch_firefox_default_profile()
