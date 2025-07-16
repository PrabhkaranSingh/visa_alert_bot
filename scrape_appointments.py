import os
import time
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 1) Load credentials & PROFILE_ID
#    .env must include:
#      VISA_USER=youremail@example.com
#      VISA_PASS=YourPassword
#      PROFILE_ID=69145711
load_dotenv()
USER       = os.getenv("VISA_USER")
PASS       = os.getenv("VISA_PASS")
PROFILE_ID = os.getenv("PROFILE_ID")

def login(driver, wait):
    # Navigate to the sign-in page
    driver.get("https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
    time.sleep(1)

    # If the form isn't there yet, click the "Sign In" splash link
    try:
        wait.until(EC.presence_of_element_located((By.ID, "user_email")))
    except TimeoutException:
        splash = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Sign In")))
        splash.click()
        time.sleep(1)

    # Fill email & password
    wait.until(EC.presence_of_element_located((By.ID, "user_email"))).send_keys(USER)
    driver.find_element(By.ID, "user_password").send_keys(PASS)

    # Tick the privacy‐policy checkbox by setting .checked = true
    try:
        chk = wait.until(EC.presence_of_element_located((By.ID, "policy_confirmed")))
        driver.execute_script("arguments[0].checked = true;", chk)
        print("✔️ Policy checkbox set")
    except TimeoutException:
        print("⚠️ Policy checkbox not found; maybe already accepted")

    # Submit the form
    driver.find_element(By.NAME, "commit").click()
    time.sleep(5)

def get_earliest_appointment():
    # 2) Chrome setup
    opts = Options()
    # opts.add_argument("--headless")   # ← comment out to watch, uncomment to run headless
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1200,800")

    service = Service("chromedriver.exe")
    driver  = webdriver.Chrome(service=service, options=opts)
    wait    = WebDriverWait(driver, 20)

    try:
        # 3) Log in
        login(driver, wait)
        print("✅ Logged in →", driver.current_url)

        # 4) Jump to your appointment calendar page
        appointment_url = f"https://ais.usvisa-info.com/en-ca/niv/schedule/{PROFILE_ID}/appointment"
        driver.get(appointment_url)
        time.sleep(2)
        print("🔗 Navigated to →", driver.current_url)

        # 5) Open the date‐picker
        wait.until(EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_date")))
        cal_icon = driver.find_element(
            By.CSS_SELECTOR,
            "#appointments_consulate_appointment_date_input a"
        )
        driver.execute_script("arguments[0].click();", cal_icon)

        # 6) Wait for the calendar table
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-calendar")))
        print("📅 Calendar rendered")

        # 7) Page through up to 24 months, collect all <a> day links
        all_dates = []
        for _ in range(24):
            # Read current header (e.g. "March 2027")
            title = driver.find_element(By.CLASS_NAME, "ui-datepicker-title").text
            month_str, year_str = title.split()
            month = datetime.strptime(month_str, "%B").month
            year  = int(year_str)

            # Parse every <a> in the calendar
            table = driver.find_element(By.CLASS_NAME, "ui-datepicker-calendar")
            for link in table.find_elements(By.TAG_NAME, "a"):
                day = int(link.text)
                all_dates.append(datetime(year, month, day))

            # Click “Next” if not disabled
            nxt = driver.find_element(By.CLASS_NAME, "ui-datepicker-next")
            if "ui-state-disabled" in nxt.get_attribute("class"):
                break
            driver.execute_script("arguments[0].click();", nxt)
            time.sleep(0.5)

        return min(all_dates) if all_dates else None

    finally:
        driver.quit()

if __name__ == "__main__":
    earlier = get_earliest_appointment()
    if earlier:
        print("🎯 Earliest open appointment:", earlier.strftime("%Y-%m-%d"))
    else:
        print("ℹ️ No open appointments found.")