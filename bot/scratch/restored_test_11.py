import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src import config

def execute_selenium_order(symbol: str, quantity: int, price: float, pin: str = config.MERCOSUR_CLAVE_OPERACIONES):
    """
    Executes a complete buy order via Selenium automation on Mercosur Casa de Bolsa portal.
    Handles login, stock selection, form filling, cart submission, declaration checkbox, and PIN entry.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    print(f"[SeleniumTrader] Starting Chrome browser to submit order: COMPRA {quantity} {symbol} @ {price:.2f} VES...")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    try:
        # 1. Login
        print("[SeleniumTrader] 1. Navigating to Mercosur login page...")
        driver.get("https://clientsapp.mercosur.com.ve/login")

        email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")

        email_field.send_keys(config.MERCOSUR_EMAIL)
        password_field.send_keys(config.MERCOSUR_PASSWORD)

        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        print("[SeleniumTrader] Login submitted. Waiting for dashboard...")
        time.sleep(5)

        # 2. Go to Mercado
        print("[SeleniumTrader] 2. Navigating to Mercado tab...")
        mercado_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'mercado')] | //button[contains(., 'Mercado')]")))
        mercado_link.click()
        time.sleep(5)

        # 3. Select Stock
        print(f"[SeleniumTrader] 3. Selecting stock tile '{symbol}'...")
        all_btns = driver.find_elements(By.TAG_NAME, "button")
        stock_btns = [b for b in all_btns if symbol.upper() in b.text.upper()]
        if stock_btns:
            driver.execute_script("arguments[0].click();", stock_btns[0])
            time.sleep(4)

        # 4. Click Comprar
        print("[SeleniumTrader] 4. Opening purchase form (Comprar)...")
        all_btns_after = driver.find_elements(By.TAG_NAME, "button")
        for b in all_btns_after:
            if "comprar" in b.text.lower():
                driver.execute_script("arguments[0].click();", b)
                break
        time.sleep(3)

        # 5. Fill Quantity & Price
        print(f"[SeleniumTrader] 5. Entering quantity={quantity}, price={price:.2f}...")
        cantidad_inp = wait.until(EC.presence_of_element_located((By.ID, "cantidad")))
        precio_inp = driver.find_element(By.ID, "precio")

        cantidad_inp.clear()
        cantidad_inp.send_keys(str(quantity))
        precio_inp.clear()
        precio_inp.send_keys(f"{price:.2f}")
        time.sleep(2)

        # 6. Click "Agregar al carrito" or "ACEPTAR"
        print("[SeleniumTrader] 6. Adding order item to cart...")
        cart_add_btn = driver.find_elements(By.XPATH, "//button[contains(., 'Agregar al carrito') or contains(., 'ACEPTAR')]")
        if cart_add_btn:
            driver.execute_script("arguments[0].click();", cart_add_btn[0])
            time.sleep(3)

        # 7. Open Cart Drawer
        print("[SeleniumTrader] 7. Opening Shopping Cart...")
        cart_icon = driver.find_elements(By.XPATH, "//button[contains(., 'Carrito') or text()='1' or text()='2' or text()='3'] | //a[contains(@href, 'carrito')]")
        if cart_icon:
            driver.execute_script("arguments[0].click();", cart_icon[0])
            time.sleep(4)

        # 8. Check all Declaration Checkboxes in Cart
        print("[SeleniumTrader] 8. Locating and checking Declaración Jurada checkbox...")
        checkboxes = driver.find_elements(By.XPATH, "//input[@type='checkbox'] | //button[@role='checkbox']")
        print(f"[SeleniumTrader] Checkboxes found: {len(checkboxes)}")
        for cb in checkboxes:
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
                print("  --> Checked declaration box!")

        # 9. Enter PIN
        print("[SeleniumTrader] 9. Entering Clave de Operaciones PIN...")
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        for inp in all_inputs:
            if inp.get_attribute('type') == 'password' or 'clave' in (inp.get_attribute('name') or '').lower() or 'pin' in (inp.get_attribute('name') or '').lower():
                inp.send_keys(pin)
                print("  --> PIN entered successfully!")

        # 10. Click Final Confirm / Process Order Button
        print("[SeleniumTrader] 10. Submitting order to Mercosur Casa de Bolsa...")
        cart_btns = driver.find_elements(By.TAG_NAME, "button")
        process_btns = [b for b in cart_btns if any(kw in b.text.upper() for kw in ['PROCESAR', 'ENVIAR', 'CONFIRMAR', 'CREAR', 'EJECUTAR'])]
        if process_btns:
            print("Clicking process button:", process_btns[0].text)
            driver.execute_script("arguments[0].click();", process_btns[0])
            time.sleep(6)

        print("[SeleniumTrader] 🎉 Order execution completed successfully!")
        return {"success": True, "message": "Order processed via Selenium automation."}

    except Exception as e:
        print(f"[SeleniumTrader] ❌ Error during Selenium order execution: {e}")
        return {"success": False, "error": str(e)}
    finally:
        time.sleep(10)
        driver.quit()

if __name__ == "__main__":
    execute_selenium_order("BNC", 1, 235.00)
