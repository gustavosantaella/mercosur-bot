import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src import config

options = webdriver.ChromeOptions()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=options)

try:
    driver.get("https://clientsapp.mercosur.com.ve/login")
    wait = WebDriverWait(driver, 15)

    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")

    email_field.send_keys(config.MERCOSUR_EMAIL)
    password_field.send_keys(config.MERCOSUR_PASSWORD)

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    time.sleep(5)
    
    # Check all network performance logs
    logs = driver.get_log('performance')
    print(f"Total CDP logs captured: {len(logs)}")
    
    api_requests = []
    for entry in logs:
        try:
            msg = json.loads(entry['message'])['message']
            if msg['method'] == 'Network.requestWillBeSent':
                url = msg['params']['request']['url']
                if 'cm.mercosur.com.ve' in url:
                    api_requests.append({
                        'method': msg['params']['request']['method'],
                        'url': url,
                        'postData': msg['params']['request'].get('postData')
                    })
        except Exception:
            pass

    print("\n================ ALL API REQUESTS TO cm.mercosur.com.ve ================")
    for req in api_requests:
        print(f"{req['method']} {req['url']} -> postData: {req['postData']}")

finally:
    driver.quit()
