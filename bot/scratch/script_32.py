import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src import config

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

try:
    print("1. Logging in...")
    driver.get("https://clientsapp.mercosur.com.ve/login")
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
    email_field.send_keys(config.MERCOSUR_EMAIL)
    password_field.send_keys(config.MERCOSUR_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)

    print("2. Navigating to Mercado...")
    driver.get("https://clientsapp.mercosur.com.ve/dashboard/mercado")
    time.sleep(4)

    print("3. Selecting BNC...")
    stock_btns = [b for b in driver.find_elements(By.TAG_NAME, "button") if "BNC" in b.text.upper()]
    if stock_btns:
        driver.execute_script("arguments[0].click();", stock_btns[0])
        time.sleep(4)

    print("4. Clicking Comprar...")
    for b in driver.find_elements(By.TAG_NAME, "button"):
        if "comprar" in b.text.lower():
            driver.execute_script("arguments[0].click();", b)
            break
    time.sleep(3)

    print("5. Filling quantity=1, price=235.00...")
    cantidad_inp = wait.until(EC.presence_of_element_located((By.ID, "cantidad")))
    precio_inp = driver.find_element(By.ID, "precio")
    cantidad_inp.clear()
    cantidad_inp.send_keys("1")
    precio_inp.clear()
    precio_inp.send_keys("235.00")
    time.sleep(2)

    print("\n================ BUTTONS IN PURCHASE FORM DRAWER ================")
    form_btns = driver.find_elements(By.TAG_NAME, "button")
    for i, b in enumerate(form_btns):
        if b.is_displayed() and b.text.strip():
            print(f"  Button [{i}]: text='{b.text.strip()}'")

    print("\n6. Clicking ACEPTAR inside purchase form drawer...")
    aceptar_btn = [b for b in form_btns if b.text.strip().upper() == "ACEPTAR"]
    if aceptar_btn:
        print("Found ACEPTAR button! Clicking...")
        driver.execute_script("arguments[0].click();", aceptar_btn[0])
        time.sleep(4)

    print("\n================ STEP 2: CONFIRMATION DRAWER ELEMENTS ================")
    step2_inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"Total inputs step 2: {len(step2_inputs)}")
    for i, inp in enumerate(step2_inputs):
        print(f"  Input [{i}]: type='{inp.get_attribute('type')}' | id='{inp.get_attribute('id')}' | name='{inp.get_attribute('name')}' | placeholder='{inp.get_attribute('placeholder')}'")

    step2_btns = driver.find_elements(By.TAG_NAME, "button")
    print(f"Total buttons step 2: {len(step2_btns)}")
    for i, b in enumerate(step2_btns):
        if b.is_displayed() and b.text.strip():
            print(f"  Button [{i}]: text='{b.text.strip()}' | disabled={b.get_attribute('disabled')}")

    # Check declaration checkboxes in step 2
    checkboxes = [i for i in step2_inputs if i.get_attribute('type') == 'checkbox'] + driver.find_elements(By.XPATH, "//button[@role='checkbox']")
    print(f"Checkboxes found step 2: {len(checkboxes)}")
    for cb in checkboxes:
        print("  --> Clicking Checkbox!")
        driver.execute_script("arguments[0].click();", cb)
        time.sleep(1)

    # Enter PIN step 2
    for inp in step2_inputs:
        if inp.get_attribute('type') == 'password' or 'clave' in (inp.get_attribute('name') or '').lower() or 'pin' in (inp.get_attribute('name') or '').lower():
            print("  --> Entering PIN 131100!")
            inp.send_keys("131100")
            time.sleep(1)

    # Check final submit button in step 2
    step2_btns_after = driver.find_elements(By.TAG_NAME, "button")
    print("\nButtons after entering PIN & checkbox:")
    for i, b in enumerate(step2_btns_after):
        if b.is_displayed() and b.text.strip():
            print(f"  Button [{i}]: text='{b.text.strip()}' | disabled={b.get_attribute('disabled')}")
            if any(kw in b.text.upper() for kw in ['CONFIRMAR', 'ENVIAR', 'CREAR', 'PROCESAR', 'ACEPTAR']):
                if b.text.strip().upper() != "ACEPTAR": # prevent re-clicking step 1 button
                    print(f"  --> TARGET FINAL SUBMIT BUTTON: '{b.text.strip()}'")

    time.sleep(8)

finally:
    driver.quit()
