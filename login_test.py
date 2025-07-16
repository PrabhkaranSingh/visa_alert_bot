import os
import time
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Load credentials
load_dotenv()
USER = os.getenv("VISA_USER")
PASS = os.getenv("VISA_PASS")

# 2. Configure Chrome
chrome_opts = Options()
# chrome_opts.add_argument("--headless")  # comment out if you want to see the browser
chrome_opts.add_argument("--disable-gpu")
chrome_opts.add_argument("--no-sandbox")

service = Service("chromedriver.exe")
driver  = webdriver.Chrome(service=service, options=chrome_opts)
wait    = WebDriverWait(driver, 15)

try:
    # 3. Go to splash & click “Sign In”
    driver.get("https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
    if "Sign in or Create an Account" in driver.title:
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Sign In"))).click()
        time.sleep(2)

    # 4. Fill in email & password
    wait.until(EC.presence_of_element_located((By.ID, "user_email"))).send_keys(USER)
    driver.find_element(By.ID, "user_password").send_keys(PASS)

    # 5. Wait for the policy checkbox to exist
    box = wait.until(EC.presence_of_element_located((By.ID, "policy_confirmed")))
    print("Checkbox found on page:", box.is_displayed(), box.is_enabled())

    # 6. Scroll into view & click via JS
    driver.execute_script("""
        arguments[0].scrollIntoView({block: 'center'});
        arguments[0].click();
    """, box)
    print("Checkbox clicked via JS")

    # 7. DEBUG: print current URL & form snippet before submit
    print("URL just before submit:", driver.current_url)
    form_html = driver.find_element(By.TAG_NAME, "form").get_attribute("outerHTML")
    print("Form HTML snippet:", form_html[:500].replace("\n", " "))

    # 8. Submit the form
    driver.find_element(By.NAME, "commit").click()

    # 9. Wait and print result
    time.sleep(5)
    print("After submit → URL:", driver.current_url)
    print("Page title:", driver.title)

finally:
    driver.quit()