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

    print("6. Clicking Agregar al carrito...")
    cart_add_btn = driver.find_elements(By.XPATH, "//button[contains(., 'Agregar al carrito') or contains(., 'ACEPTAR')]")
    if cart_add_btn:
        driver.execute_script("arguments[0].click();", cart_add_btn[0])
        time.sleep(3)

    print("7. Opening Cart...")
    cart_icon = driver.find_elements(By.XPATH, "//button[contains(., 'Carrito') or text()='1' or text()='2' or text()='3'] | //a[contains(@href, 'carrito')]")
    if cart_icon:
        driver.execute_script("arguments[0].click();", cart_icon[0])
        time.sleep(4)

    print("\n================ INSPECTING CART DRAWER ELEMENTS ================")
    # Find all elements inside drawer/modal
    drawers = driver.find_elements(By.XPATH, "//div[@role='dialog'] | //div[contains(@class, 'drawer')] | //aside | //div[contains(@class, 'sheet')]")
    print(f"Drawers/Sheets found: {len(drawers)}")

    # Check ALL buttons on page now
    all_btns = driver.find_elements(By.TAG_NAME, "button")
    print(f"Total buttons found: {len(all_btns)}")
    for i, b in enumerate(all_btns):
        if b.is_displayed() and b.text.strip():
            print(f"  Button [{i}]: text='{b.text.strip()}' | disabled={b.get_attribute('disabled')} | class='{b.get_attribute('class')}'")

    # Check ALL checkboxes & password inputs
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"Total inputs found: {len(inputs)}")
    for i, inp in enumerate(inputs):
        print(f"  Input [{i}]: type='{inp.get_attribute('type')}' | id='{inp.get_attribute('id')}' | name='{inp.get_attribute('name')}' | placeholder='{inp.get_attribute('placeholder')}'")

    # Click declaration checkbox
    for inp in inputs:
        if inp.get_attribute('type') == 'checkbox' and not inp.is_selected():
            print("--> Clicking Checkbox!")
            driver.execute_script("arguments[0].click();", inp)
            time.sleep(1)

    # Enter PIN
    for inp in inputs:
        if inp.get_attribute('type') == 'password' or 'clave' in (inp.get_attribute('name') or '').lower():
            print("--> Entering PIN 131100!")
            inp.send_keys("131100")
            time.sleep(1)

    print("\n================ BUTTONS AFTER CHECKBOX & PIN ================")
    all_btns_after = driver.find_elements(By.TAG_NAME, "button")
    for i, b in enumerate(all_btns_after):
        if b.is_displayed() and b.text.strip():
            print(f"  Button [{i}]: text='{b.text.strip()}' | disabled={b.get_attribute('disabled')}")

    # Check Chrome CDP logs to see if POST /portal/ordenes is triggered when clicking buttons
    time.sleep(10)

finally:
    driver.quit()
