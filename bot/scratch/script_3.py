import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src import config

options = webdriver.ChromeOptions()
options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
options.add_argument("--start-maximized")
options.add_argument('--headless=1')

print("Launching Chrome Browser for Mercosur Shopping Cart Flow...")
driver = webdriver.Chrome(options=options)

def get_network_payloads():
    logs = driver.get_log('performance')
    payloads = []
    for entry in logs:
        try:
            message = json.loads(entry['message'])['message']
            if message['method'] == 'Network.requestWillBeSent':
                req = message['params']['request']
                url = req.get('url', '')
                if '/portal/ordenes' in url and req.get('method') == 'POST':
                    payloads.append({
                        'url': url,
                        'headers': req.get('headers'),
                        'postData': req.get('postData')
                    })
        except Exception:
            pass
    return payloads

try:
    driver.get("https://clientsapp.mercosur.com.ve/login")
    wait = WebDriverWait(driver, 15)

    print("Logging in...")
    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")

    email_field.send_keys(config.MERCOSUR_EMAIL)
    password_field.send_keys(config.MERCOSUR_PASSWORD)

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    time.sleep(5)
    print("LoggedIn. Navigating to Mercado tab...")
    
    # Click Mercado
    mercado_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'mercado')] | //button[contains(., 'Mercado')]")))
    mercado_link.click()
    time.sleep(5)

    # Click BNC stock button
    all_btns = driver.find_elements(By.TAG_NAME, "button")
    bnc_btns = [b for b in all_btns if "BNC" in b.text]
    if bnc_btns:
        driver.execute_script("arguments[0].click();", bnc_btns[0])
        time.sleep(4)

    # Click Comprar
    all_btns_after = driver.find_elements(By.TAG_NAME, "button")
    for b in all_btns_after:
        if "comprar" in b.text.lower():
            driver.execute_script("arguments[0].click();", b)
            break
    time.sleep(3)

    # Fill quantity & price
    cantidad_inp = driver.find_element(By.ID, "cantidad")
    precio_inp = driver.find_element(By.ID, "precio")
    
    cantidad_inp.clear()
    cantidad_inp.send_keys("1")
    precio_inp.clear()
    precio_inp.send_keys("235.00")
    print("Entered quantity 1 and price 235.00!")

    time.sleep(2)
    # Click "Agregar al carrito"
    cart_add_btn = driver.find_elements(By.XPATH, "//button[contains(., 'Agregar al carrito')]")
    if cart_add_btn:
        print("Clicking 'Agregar al carrito'...")
        driver.execute_script("arguments[0].click();", cart_add_btn[0])
        time.sleep(3)

    # Click Cart Icon Button (top bar cart icon or button with badge)
    print("Clicking Cart Icon...")
    cart_icon = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'carrito') or contains(@href, 'carrito')] | //a[contains(@href, 'carrito')] | //button[child::svg and contains(., '1')] | //button[text()='1' or text()='2' or text()='3']")
    if cart_icon:
        print("Cart icon text:", cart_icon[0].text)
        driver.execute_script("arguments[0].click();", cart_icon[0])
        time.sleep(4)

    # Inspect Cart Drawer elements
    print("Inspecting Cart Drawer...")
    cart_inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in cart_inputs:
        inp_type = inp.get_attribute('type')
        print(f"  Cart input type={inp_type}, id={inp.get_attribute('id')}, name={inp.get_attribute('name')}")
        if inp_type == 'checkbox':
            print("  --> Clicking Cart Declaration Checkbox!")
            driver.execute_script("arguments[0].click();", inp)
        elif inp_type == 'password' or 'clave' in (inp.get_attribute('name') or '').lower() or 'pin' in (inp.get_attribute('name') or '').lower():
            inp.send_keys(config.MERCOSUR_CLAVE_OPERACIONES)
            print("  --> Entered PIN 131100!")

    cart_btns = driver.find_elements(By.TAG_NAME, "button")
    for b in cart_btns:
        txt = b.text.strip()
        if txt and b.is_displayed():
            print(f"  Cart button: '{txt}'")

    # Click Process / Send orders button in cart
    process_btns = [b for b in cart_btns if any(kw in b.text.upper() for kw in ['PROCESAR', 'ENVIAR', 'CONFIRMAR', 'CREAR', 'EJECUTAR'])]
    if process_btns:
        print("Clicking Process Orders button:", process_btns[0].text)
        driver.execute_script("arguments[0].click();", process_btns[0])
        time.sleep(5)

    captured = get_network_payloads()
    print("\n================ INTERCEPTED NETWORK POST PAYLOADS ================")
    print(json.dumps(captured, indent=2))

finally:
    print("Closing browser in 10s...")
    time.sleep(10)
    driver.quit()
