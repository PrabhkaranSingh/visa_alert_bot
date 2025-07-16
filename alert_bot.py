import os
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from bs4 import BeautifulSoup
from telegram import Bot
import schedule

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ---- CONFIG ----
DEBUG = True    # ← set False to go headless again
load_dotenv()
BOT_TOKEN  = os.getenv("BOT_TOKEN")
CHAT_ID    = os.getenv("CHAT_ID")
USER       = os.getenv("VISA_USER")
PASS       = os.getenv("VISA_PASS")
PROFILE_ID = os.getenv("PROFILE_ID")  # e.g. 69145711

async def send_telegram(msg: str):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)

def get_earliest_appointment() -> datetime | None:
    print("🔍 Starting scrape…")
    # 1) Chrome setup
    chrome_opts = Options()
    if not DEBUG:
        chrome_opts.add_argument("--headless")
    else:
        print("🐞 DEBUG mode → headful browser (you’ll see it pop up)")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1200,800")

    service = Service("chromedriver.exe")
    driver  = webdriver.Chrome(service=service, options=chrome_opts)
    wait    = WebDriverWait(driver, 20)

    try:
        # --- LOGIN FLOW ---
        print("1) Opening sign_in page…")
        driver.get("https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
        time.sleep(1)

        # click splash if needed
        try:
            print("2) Waiting for email field…")
            wait.until(EC.presence_of_element_located((By.ID, "user_email")))
        except TimeoutException:
            print("   → splash still up; clicking Sign In link")
            splash = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Sign In")))
            splash.click()
            time.sleep(1)

        print("3) Filling credentials…")
        wait.until(EC.presence_of_element_located((By.ID, "user_email"))).send_keys(USER)
        driver.find_element(By.ID, "user_password").send_keys(PASS)

        print("4) Ticking privacy-policy…")
        try:
            chk = wait.until(EC.presence_of_element_located((By.ID, "policy_confirmed")))
            driver.execute_script("arguments[0].checked = true;", chk)
        except TimeoutException:
            print("   → checkbox not found; maybe already accepted")

        print("5) Submitting login form…")
        driver.find_element(By.NAME, "commit").click()
        time.sleep(4)
        print("   → post-login URL:", driver.current_url)

        # --- NAVIGATE TO CALENDAR ---
        print("6) Navigating to appointment page…")
        appt_url = f"https://ais.usvisa-info.com/en-ca/niv/schedule/{PROFILE_ID}/appointment"
        driver.get(appt_url)
        time.sleep(2)
        print("   → appointment URL:", driver.current_url)

        # wait for date input
        print("7) Waiting for date input…")
        wait.until(EC.presence_of_element_located((By.ID, "appointments_consulate_appointment_date")))
        print("   → date input visible")

        # open the picker
        print("8) Clicking calendar icon…")
        cal_icon = driver.find_element(
            By.CSS_SELECTOR,
            "#appointments_consulate_appointment_date_input a"
        )
        driver.execute_script("arguments[0].click();", cal_icon)

        # wait for widget
        print("9) Waiting for date-picker table…")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ui-datepicker-calendar")))
        print("   → calendar rendered")

        # --- SCRAPE DATES ---
        print("10) Scraping clickable days…")
        found = []
        for month_index in range(24):
            header = driver.find_element(By.CLASS_NAME, "ui-datepicker-title").text
            m_str, y_str = header.split()
            month = datetime.strptime(m_str, "%B").month
            year  = int(y_str)

            table = driver.find_element(By.CLASS_NAME, "ui-datepicker-calendar")
            for link in table.find_elements(By.TAG_NAME, "a"):
                day = int(link.text)
                found.append(datetime(year, month, day))

            # next month
            nxt = driver.find_element(By.CLASS_NAME, "ui-datepicker-next")
            if "ui-state-disabled" in nxt.get_attribute("class"):
                break
            driver.execute_script("arguments[0].click();", nxt)
            time.sleep(0.3)

        earliest = min(found) if found else None
        print("🔚 Scrape done. Earliest:", earliest)
        return earliest

    finally:
        driver.quit()

# ---- STATE & JOB ----
last_seen: datetime | None = None

def job():
    global last_seen
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Job triggered…")
    try:
        earliest = get_earliest_appointment()
    except Exception as e:
        print("🚨 scrape error:", repr(e))
        return

    if earliest:
        if not last_seen or earliest < last_seen:
            last_seen = earliest
            msg = f"🗓️ New earliest visa appointment: {earliest:%Y-%m-%d}"
            print("✉️ Sending alert:", msg)
            asyncio.run(send_telegram(msg))
        else:
            print("   no earlier date than", last_seen.date())
    else:
        print("   no open appointments found")

# ---- SCHEDULER ----
print("🚀 Visa Alert Bot starting. DEBUG =", DEBUG)
schedule.every(30).minutes.do(job)
job()  # initial run

while True:
    schedule.run_pending()
    time.sleep(5)