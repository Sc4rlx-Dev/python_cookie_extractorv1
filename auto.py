import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 🔹 CONFIGURATION
# ==========================================

# 🔴 PASTE YOUR DISCORD WEBHOOK URL HERE 👇
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 🔹 HELPER FUNCTIONS
# ==========================================

def send_to_discord(file_path):
    """Sends the saved file to the Discord Webhook."""
    if not os.path.exists(file_path):
        print(f"[!] File not found: {file_path}")
        return

    print(f"\n[🚀] Sending {file_path} to Discord...")
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                WEBHOOK_URL,
                files={"file": (file_path, f)},
                data={"content": "🍪 **New Cookie Generated!**"}
            )
        
        if response.status_code in [200, 204]:
            print("   [✔] Sent to Discord successfully!")
        else:
            print(f"   [!] Failed to send. Status: {response.status_code}")
            print(f"   [!] Response: {response.text}")

    except Exception as e:
        print(f"   [!] Error sending to Discord: {e}")

def setup_driver():
    options = Options()
    # options.add_argument("--headless=new") # Uncomment for invisible mode
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized") 
    driver = webdriver.Chrome(options=options)
    return driver

def click_element(driver, wait, text_identifier, step_name):
    """Robust clicker with error handling."""
    print(f"[*] Step: {step_name}...")
    try:
        xpath = f"//*[contains(text(), '{text_identifier}')]"
        
        # 1. Wait for presence
        element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        
        # 2. Scroll into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
        time.sleep(1.5)
        
        # 3. Wait for clickable
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        
        # 4. Click (Try standard, fallback to JS)
        try:
            element.click()
        except:
            driver.execute_script("arguments[0].click();", element)
            
        print(f"   >>> Clicked: '{text_identifier}'")
        return True
        
    except Exception as e:
        print(f"[!] Failed at step '{step_name}': {e}")
        driver.save_screenshot(f"debug_{step_name.replace(' ','_')}.png")
        return False

# ==========================================
# 🔹 CORE LOGIC
# ==========================================

def extract_initial_data(page1, page2):
    """Gets the password and initial safelink."""
    try:
        # Password
        r1 = requests.get(page1, headers=HEADERS)
        s1 = BeautifulSoup(r1.text, "html.parser")
        pass_row = s1.find("td", string="Password")
        password = pass_row.find_next_sibling("td").text.strip() if pass_row else None

        # SafeLink
        r2 = requests.get(page2, headers=HEADERS)
        s2 = BeautifulSoup(r2.text, "html.parser")
        link_tag = s2.find("a", string=lambda t: t and "Click Here" in t)
        safelink = urljoin(page2, link_tag["href"]) if link_tag else None

        return password, safelink
    except Exception as e:
        print(f"[!] Extraction Error: {e}")
        return None, None

def unlock_and_save(driver, password):
    """Unlocks the paste, saves cookie.txt, and triggers Discord upload."""
    wait = WebDriverWait(driver, 15)
    print("\n[🔐] Locked Paste Found. Attempting to unlock...")

    try:
        # Enter Password
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))).send_keys(password)
        
        # Click Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        print("   >>> Unlocked.")

        # Extract Variable
        time.sleep(2)
        cookie_text = driver.execute_script("return (typeof content !== 'undefined') ? content : null;")
        
        if not cookie_text:
            # Fallback for textarea
            try:
                cookie_text = driver.find_element(By.TAG_NAME, "textarea").get_attribute("value")
            except:
                print("   [!] Could not find content. Check debug_unlock_fail.png")
                driver.save_screenshot("debug_unlock_fail.png")
                return

        # Save to file
        filename = "cookie.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(cookie_text)
        print(f"\n[✔] SUCCESS! Cookie saved to {filename}")

        # --- SEND TO DISCORD ---
        send_to_discord(filename)

    except Exception as e:
        print(f"[❌] Error unlocking: {e}")
        driver.save_screenshot("debug_unlock_error.png")

# ==========================================
# 🔹 MAIN EXECUTION
# ==========================================

def main():
    page1 = "https://www.techedubyte.com/chatgpt-internal-server-error/"
    page2 = "https://www.techedubyte.com/chatgpt-premium-account-cookies/"

    print("--- 🚀 STARTING AUTOMATION ---")
    password, safelink = extract_initial_data(page1, page2)
    
    if not password or not safelink:
        print("❌ Failed to fetch initial data.")
        return

    print(f"🔐 PASSWORD: {password}")
    print(f"🔗 SAFELINK: {safelink}\n")

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    try:
        print(f"[+] Opening Browser...")
        driver.get(safelink)

        # 5-Step Sequence
        steps = [
            ("IM NOT ROBOT", "1-Captcha"),
            ("CLICK HERE FOR GENERATE LINK", "2-GenLink1"),
            ("Continue", "3-Continue"),
            ("CLICK HERE FOR GENERATE LINK", "4-GenLink2"),
            ("DOWNLOAD LINK", "5-Download")
        ]

        for text, name in steps:
            if "paste.techedubyte.com" in driver.current_url:
                print("   [!] Early redirect detected.")
                break

            if not click_element(driver, wait, text, name):
                print("❌ Step failed. Exiting.")
                return

            if "GENERATE LINK" in text:
                print("   ... Waiting 15s for timer ...")
                time.sleep(15)

        # Final Redirect
        print("[*] Waiting for final page...")
        try:
            wait.until(lambda d: "paste.techedubyte.com" in d.current_url)
            unlock_and_save(driver, password)
        except:
            print("[!] Timed out waiting for final redirect.")
            driver.save_screenshot("debug_timeout.png")

    finally:
        print("[*] Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()