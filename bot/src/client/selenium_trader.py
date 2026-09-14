import time
import json
import logging
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from src import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _dump_buttons(driver, label=""):
    """Print all visible buttons for debugging."""
    btns = driver.find_elements(By.TAG_NAME, "button")
    print(f"\n  [DEBUG] {label} — {len(btns)} buttons total:")
    for i, b in enumerate(btns):
        try:
            if b.is_displayed():
                cls = (b.get_attribute('class') or '')[:60]
                print(f"    [{i}] '{b.text.strip()}' | disabled={b.get_attribute('disabled')} | class={cls}")
        except Exception:
            pass


def _dump_inputs(driver, label=""):
    """Print all input fields for debugging."""
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"\n  [DEBUG] {label} — {len(inputs)} inputs:")
    for i, inp in enumerate(inputs):
        try:
            print(f"    [{i}] type={inp.get_attribute('type')} | id={inp.get_attribute('id')} "
                  f"| name={inp.get_attribute('name')} | placeholder={inp.get_attribute('placeholder')}")
        except Exception:
            pass


def _get_captured_order_posts(driver):
    """Return list of POST /portal/ordenes requests captured via Chrome performance logs."""
    try:
        logs = driver.get_log('performance')
        posts = []
        for entry in logs:
            try:
                msg = json.loads(entry['message'])['message']
                if msg.get('method') == 'Network.requestWillBeSent':
                    req = msg['params']['request']
                    if '/portal/ordenes' in req.get('url', '') and req.get('method') == 'POST':
                        posts.append({'url': req.get('url'), 'postData': req.get('postData')})
            except Exception:
                pass
        return posts
    except Exception:
        return []


def _safe_click(driver, element, label="element"):
    """Scroll into view then click (normal, then JS fallback)."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.3)
        element.click()
        print(f"  [OK] Clicked {label}")
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            print(f"  [OK] Clicked {label} (JS fallback)")
        except Exception as e:
            print(f"  [!!] Could not click {label}: {e}")


def _clear_and_type(driver, element, value: str):
    """Reliably clear a field and type a new value."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    time.sleep(0.2)
    element.click()
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.DELETE)
    element.clear()
    time.sleep(0.2)
    element.send_keys(str(value))
    time.sleep(0.3)


def _find_otp_inputs(elements, pin_length=6):
    """
    From a list of input elements, find OTP-style digit boxes using multiple
    detection strategies. Returns a list of exactly pin_length inputs, or [].
    """
    # Strategy A: inputs with maxlength=1 (most common OTP pattern)
    maxlen1 = [
        inp for inp in elements
        if inp.get_attribute('maxlength') == '1'
        and inp.is_displayed()
        and inp.get_attribute('id') not in ('cantidad', 'precio')
    ]
    if len(maxlen1) == pin_length:
        return maxlen1

    # Strategy B: inputs with data-index or data-id attribute (React OTP libs)
    data_idx = [
        inp for inp in elements
        if (inp.get_attribute('data-index') is not None
            or inp.get_attribute('data-id') is not None)
        and inp.is_displayed()
    ]
    if len(data_idx) == pin_length:
        return data_idx

    # Strategy C: inputs with inputmode='numeric' and no id/name (generic OTP)
    numeric_mode = [
        inp for inp in elements
        if inp.get_attribute('inputmode') == 'numeric'
        and inp.is_displayed()
        and inp.get_attribute('id') not in ('cantidad', 'precio')
    ]
    if len(numeric_mode) == pin_length:
        return numeric_mode

    # Strategy D: inputs with autocomplete containing 'one-time-code'
    otc = [
        inp for inp in elements
        if 'one-time' in (inp.get_attribute('autocomplete') or '').lower()
        and inp.is_displayed()
    ]
    if len(otc) == pin_length:
        return otc

    # Strategy E (original): text/tel/number inputs with empty id, name, placeholder
    empty_attr = [
        inp for inp in elements
        if inp.get_attribute('type') in ('text', 'tel', 'number', 'password')
        and not (inp.get_attribute('id') or '').strip()
        and not (inp.get_attribute('name') or '').strip()
        and not (inp.get_attribute('placeholder') or '').strip()
        and inp.is_displayed()
        and inp.get_attribute('id') not in ('cantidad', 'precio')
    ]
    if len(empty_attr) >= pin_length:
        return empty_attr[:pin_length]

    # Strategy F: any small visible text inputs grouped together (last resort)
    small_inputs = [
        inp for inp in elements
        if inp.get_attribute('type') in ('text', 'tel', 'number', 'password')
        and inp.is_displayed()
        and inp.get_attribute('id') not in ('cantidad', 'precio')
        and inp.size.get('width', 999) <= 60  # OTP boxes are typically narrow
    ]
    if len(small_inputs) == pin_length:
        return small_inputs

    return []


def _type_otp_digits(driver, otp_inputs, pin_str, label=""):
    """
    Type PIN digits one-by-one into OTP input boxes.
    Uses ActionChains for reliable focus management.
    """
    from selenium.webdriver.common.action_chains import ActionChains
    actions = ActionChains(driver)

    for i, digit in enumerate(pin_str):
        try:
            inp = otp_inputs[i]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", inp)
            time.sleep(0.15)
            # Focus via JS + click to ensure the input is active
            driver.execute_script("arguments[0].focus();", inp)
            inp.click()
            time.sleep(0.1)
            inp.send_keys(digit)
            time.sleep(0.25)  # Wait for frontend to process and auto-advance
        except Exception as ex:
            print(f"  [!] OTP digit [{i}] error: {ex}")
            # Fallback: try JS value injection
            try:
                driver.execute_script(
                    "arguments[0].value = arguments[1]; "
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true})); "
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    otp_inputs[i], digit
                )
            except Exception:
                pass

    # Final pause to let the frontend validate all digits and enable Confirmar
    time.sleep(1.0)
    print(f"  [OK] {label} PIN entered via {len(pin_str)} OTP inputs.")


def _find_and_enter_pin(driver, pin, context_element=None, label=""):
    """
    Try to find a PIN/password input and type the PIN.
    Handles three patterns:
      1. Single password-type or named input (classic).
      2. OTP-style: 6 individual digit inputs detected via multiple strategies
         (maxlength=1, data-index, inputmode=numeric, empty attrs, narrow width).
      3. JS-based injection as last resort.
    Searches context_element first, then falls back to full page.
    Returns True if PIN was entered.
    """
    pin_str = str(pin)
    PIN_LENGTH = len(pin_str)
    roots = []
    if context_element is not None:
        roots.append(("modal", context_element.find_elements(By.TAG_NAME, "input")))
    roots.append(("page", driver.find_elements(By.TAG_NAME, "input")))

    for root_label, inputs in roots:
        # ── Pattern 1: classic password / named PIN field ─────────
        for inp in inputs:
            try:
                inp_type = inp.get_attribute('type') or ''
                inp_name = (inp.get_attribute('name') or '').lower()
                inp_id   = (inp.get_attribute('id') or '').lower()
                inp_ph   = (inp.get_attribute('placeholder') or '').lower()
                is_pin = (
                    inp_type == 'password'
                    or any(kw in inp_name for kw in ('clave', 'pin', 'operacion'))
                    or any(kw in inp_id   for kw in ('clave', 'pin', 'operacion'))
                    or any(kw in inp_ph   for kw in ('clave', 'pin', 'operacion'))
                )
                if is_pin and inp.is_displayed():
                    _clear_and_type(driver, inp, pin_str)
                    print(f"  [OK] {label} PIN entered ({root_label}, classic) — "
                          f"id='{inp.get_attribute('id')}' type='{inp_type}'")
                    return True
            except Exception as ex:
                print(f"  [!] PIN field error: {ex}")

        # ── Pattern 2: OTP-style individual digit boxes (6 inputs) ─
        otp_inputs = _find_otp_inputs(inputs, PIN_LENGTH)
        if otp_inputs:
            print(f"  [OK] OTP-style PIN inputs detected ({len(otp_inputs)} boxes, "
                  f"{root_label}). Typing {PIN_LENGTH} digits...")
            _type_otp_digits(driver, otp_inputs, pin_str, label)
            return True

    print(f"  [!] {label} PIN field not found in modal or page — dumping inputs:")
    _dump_inputs(driver, label)
    return False


# ─────────────────────────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────────────────────────

def execute_selenium_order(
    symbol: str,
    quantity: int,
    price: float,
    order_type: str = "COMPRA",
    pin: str = config.MERCOSUR_CLAVE_OPERACIONES
) -> Dict[str, Any]:
    """
    Executes a complete buy/sell order on Mercosur Casa de Bolsa via Selenium.

    Flow:
      1. Login
      2. Navigate to Mercado
      3. Select stock tile
      4. Click Comprar / Vender
      5. Fill quantity & price
      6. Click "Agregar al carrito"
      7. Open cart page (via carrito link)
      8. Wait for cart to load; tick Declaracion Jurada checkbox
      9. Click "Crear una orden"
     10. Wait for confirmation modal; enter PIN; click Confirmar
     11. Verify via network logs that the real order POST fired
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    options.add_experimental_option("detach", True)

    action_name = "comprar" if order_type.upper() == "COMPRA" else "vender"

    print(f"\n[SeleniumTrader] Launching VISIBLE Chrome — {order_type} {quantity} {symbol} @ {price:.2f} VES")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # ── Step 0: Pre-validate available balance ─────────────────
        if order_type.upper() == "COMPRA":
            print("\n[SeleniumTrader] > Step 0: Validating available balance before opening browser...")
            try:
                from src.client.mercosur_client import MercosurClient
                api_client = MercosurClient()
                api_client.login()
                balances = api_client.get_balances()
                available = balances.get("available_balance", 0.0)
                total_cost = quantity * price
                total_with_fees = total_cost * 1.05  # 5% margin for commissions/fees
                print(f"  Available balance: {available:,.2f} VES")
                print(f"  Order total:       {total_cost:,.2f} VES (with fees ~{total_with_fees:,.2f} VES)")
                if total_with_fees > available:
                    msg = (f"Insufficient balance: need ~{total_with_fees:,.2f} VES "
                           f"but only {available:,.2f} VES available.")
                    print(f"  [!!] {msg}")
                    return {
                        "success": False,
                        "status": "INSUFFICIENT_BALANCE",
                        "message": msg,
                        "available_balance": available,
                        "required_amount": total_with_fees
                    }
                print(f"  [OK] Balance sufficient. Proceeding with order.")
            except Exception as e:
                print(f"  [!] Could not validate balance via API (continuing anyway): {e}")

        # ── Step 1: Login ──────────────────────────────────────────
        print("\n[SeleniumTrader] > Step 1: Login...")
        driver.get("https://clientsapp.mercosur.com.ve/login")
        time.sleep(2)

        email_field = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[type='email'], input[name='email']")))
        password_field = driver.find_element(
            By.CSS_SELECTOR, "input[type='password'], input[name='password']")

        _clear_and_type(driver, email_field, config.MERCOSUR_EMAIL)
        _clear_and_type(driver, password_field, config.MERCOSUR_PASSWORD)

        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        _safe_click(driver, submit, "Login submit")

        print("  Waiting for post-login redirect (up to 20s)...")
        try:
            wait.until(lambda d: "/login" not in d.current_url.lower())
            print(f"  [OK] Logged in. URL: {driver.current_url}")
        except TimeoutException:
            print(f"  [!] Still on login page after 20s: {driver.current_url}")
            raise RuntimeError("Login timed out — check browser for CAPTCHA or wrong credentials.")

        # ── Step 2: Navigate to Mercado ────────────────────────────
        print("\n[SeleniumTrader] > Step 2: Navigating to Mercado...")
        driver.get("https://clientsapp.mercosur.com.ve/dashboard/mercado")
        time.sleep(5)

        # ── Step 3: Select stock tile ──────────────────────────────
        print(f"\n[SeleniumTrader] > Step 3: Selecting '{symbol}' tile...")
        try:
            wait.until(lambda d: any(
                symbol.upper() in b.text.upper()
                for b in d.find_elements(By.TAG_NAME, "button") if b.is_displayed()
            ))
        except TimeoutException:
            print("  [!] Timeout — trying anyway")

        stock_btns = [b for b in driver.find_elements(By.TAG_NAME, "button")
                      if symbol.upper() in b.text.upper() and b.is_displayed()]
        if not stock_btns:
            raise RuntimeError(f"Stock tile '{symbol}' not found on Mercado page.")
        _safe_click(driver, stock_btns[0], f"Stock tile {symbol}")
        time.sleep(4)

        # ── Step 4: Click Comprar / Vender ─────────────────────────
        print(f"\n[SeleniumTrader] > Step 4: Clicking '{action_name}'...")
        try:
            action_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, f"//button[contains(translate(., "
                           f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{action_name}')]")
            ))
            _safe_click(driver, action_btn, action_name)
        except TimeoutException:
            for b in driver.find_elements(By.TAG_NAME, "button"):
                if action_name in b.text.lower() and b.is_displayed():
                    _safe_click(driver, b, action_name)
                    break
        time.sleep(3)

        # ── Step 5: Fill quantity & price ──────────────────────────
        print(f"\n[SeleniumTrader] > Step 5: Entering qty={quantity}, price={price:.2f}...")
        cantidad_inp = wait.until(EC.presence_of_element_located((By.ID, "cantidad")))
        precio_inp = driver.find_element(By.ID, "precio")
        _clear_and_type(driver, cantidad_inp, str(quantity))
        _clear_and_type(driver, precio_inp, f"{price:.2f}")
        time.sleep(2)

        # ── Step 6: Confirm account selection then add to cart ────
        print("\n[SeleniumTrader] > Step 6: Confirming account/cartera and adding to cart...")

        # 6a. Click ACEPTAR if visible — confirms the cuenta/cartera selection panel
        # This must happen BEFORE "Agregar al carrito" becomes enabled
        aceptar_btns = driver.find_elements(
            By.XPATH, "//button[normalize-space(.)='ACEPTAR']")
        for ab in aceptar_btns:
            if ab.is_displayed() and ab.get_attribute("disabled") is None:
                print("  [->] Clicking ACEPTAR (cuenta/cartera confirmation)...")
                _safe_click(driver, ab, "ACEPTAR (cuenta/cartera)")
                time.sleep(2)
                break

        # 6b. Wait for "Agregar al carrito" to become ENABLED (not disabled)
        print("  Waiting for 'Agregar al carrito' to become enabled (up to 15s)...")
        agregar_btn = None
        try:
            agregar_btn = WebDriverWait(driver, 15).until(lambda d: next(
                (b for b in d.find_elements(By.TAG_NAME, "button")
                 if "agregar al carrito" in b.text.lower()
                 and b.is_displayed()
                 and b.get_attribute("disabled") is None),
                None
            ))
            if agregar_btn:
                print(f"  [OK] 'Agregar al carrito' is enabled.")
            else:
                print("  [!] Timeout — 'Agregar al carrito' never became enabled. Dumping buttons:")
                _dump_buttons(driver, "AGREGAR-NOT-ENABLED")
        except TimeoutException:
            print("  [!] Timeout waiting for 'Agregar al carrito' to enable.")
            _dump_buttons(driver, "AGREGAR-TIMEOUT")

        # 6c. Click Agregar al carrito
        if agregar_btn:
            _safe_click(driver, agregar_btn, "Agregar al carrito")
        else:
            # Last-resort: try force-clicking it
            for b in driver.find_elements(By.TAG_NAME, "button"):
                if "agregar al carrito" in b.text.lower() and b.is_displayed():
                    print("  [->] Force-clicking Agregar al carrito...")
                    driver.execute_script("arguments[0].removeAttribute('disabled'); arguments[0].click();", b)
                    break
        time.sleep(4)

        # ── Step 7: Open cart page ─────────────────────────────────
        print("\n[SeleniumTrader] > Step 7: Opening cart...")
        cart_opened = False

        # Strategy A: aria-label / href
        for selector in ["button[aria-label*='carrito']", "button[aria-label*='Carrito']",
                          "button[aria-label*='cart']", "a[href*='carrito']"]:
            els = driver.find_elements(By.CSS_SELECTOR, selector)
            if els:
                _safe_click(driver, els[0], f"Cart ({selector})")
                cart_opened = True
                break

        # Strategy B: button with digit badge (items in cart)
        if not cart_opened:
            for b in driver.find_elements(By.TAG_NAME, "button"):
                if not b.is_displayed():
                    continue
                txt = b.text.strip()
                if txt.isdigit() and 1 <= int(txt) <= 9:
                    _safe_click(driver, b, f"Cart badge button ({txt})")
                    cart_opened = True
                    break

        # Strategy C: SVG button in top bar (y < 120px)
        if not cart_opened:
            for b in driver.find_elements(By.XPATH, "//button[.//*[local-name()='svg']]"):
                if b.is_displayed() and b.location.get('y', 999) < 120:
                    if b.text.strip().isdigit():
                        _safe_click(driver, b, "SVG top-bar cart button")
                        cart_opened = True
                        break

        if not cart_opened:
            print("  [!] Cart icon not found — dumping all buttons:")
            _dump_buttons(driver, "POST-ADD-TO-CART")

        # Wait for cart page to fully load (dynamic content)
        print("  Waiting for cart page inputs to appear (up to 15s)...")
        try:
            wait.until(lambda d: len(d.find_elements(By.TAG_NAME, "input")) > 0)
            print("  [OK] Cart page loaded with inputs.")
        except TimeoutException:
            print("  [!] No inputs after 15s — cart may need more time.")
            _dump_buttons(driver, "CART-TIMEOUT")

        # ── Step 8: Tick Declaracion Jurada checkbox ───────────────
        print("\n[SeleniumTrader] > Step 8: Checking Declaracion Jurada checkbox...")
        _dump_inputs(driver, "Cart page")

        checkbox_xp = (
            "//input[@type='checkbox']"
            " | //span[@role='checkbox']"
            " | //button[@role='checkbox']"
            " | //button[@data-state='unchecked']"
            " | //div[@data-state='unchecked']"
        )
        checkboxes = driver.find_elements(By.XPATH, checkbox_xp)
        print(f"  Found {len(checkboxes)} checkbox element(s)")
        for cb in checkboxes:
            try:
                state = (cb.get_attribute("data-state") or
                         cb.get_attribute("aria-checked") or
                         cb.get_attribute("checked") or "unchecked")
                if state not in ("true", "checked"):
                    _safe_click(driver, cb, "Declaracion Jurada checkbox")
                    time.sleep(0.5)
                    new_state = cb.get_attribute("data-state") or cb.get_attribute("aria-checked")
                    print(f"    Checkbox new state: {new_state}")
            except Exception as ex:
                print(f"  [!] Checkbox error: {ex}")
        time.sleep(2)

        # ── Step 9: Click "Crear una orden" ───────────────────────
        print("\n[SeleniumTrader] > Step 9: Clicking 'Crear una orden'...")
        _dump_buttons(driver, "PRE-SUBMIT")

        SUBMIT_KW = ['PROCESAR', 'ENVIAR', 'CREAR', 'EJECUTAR', 'SUBMIT', 'ORDEN']
        submitted = False

        # First pass: enabled buttons
        for b in driver.find_elements(By.TAG_NAME, "button"):
            try:
                if not b.is_displayed():
                    continue
                txt = b.text.strip().upper()
                if any(kw in txt for kw in SUBMIT_KW) and b.get_attribute("disabled") is None:
                    print(f"  [->] Submit button: '{b.text.strip()}'")
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                    time.sleep(0.5)
                    b.click()
                    submitted = True
                    break
            except Exception as ex:
                print(f"  [!] Click error: {ex}")

        # Second pass: force-click if disabled
        if not submitted:
            for b in driver.find_elements(By.TAG_NAME, "button"):
                txt = b.text.strip().upper()
                if any(kw in txt for kw in SUBMIT_KW):
                    print(f"  [->] Force-clicking: '{b.text.strip()}'")
                    driver.execute_script(
                        "arguments[0].removeAttribute('disabled'); arguments[0].click();", b)
                    submitted = True
                    break

        if not submitted:
            print("  [!!] No submit button found!")
            _dump_buttons(driver, "SUBMIT-NOT-FOUND")

        # ── Step 10: Handle confirmation modal (OTP PIN + Confirmar) ─
        # After clicking submit, a modal appears with:
        #   - 6 individual OTP text inputs (one per digit of the PIN)
        #   - Confirmar button (disabled until all 6 digits entered)
        #   - Cancelar / Close buttons
        print("\n[SeleniumTrader] > Step 10: Waiting for PIN confirmation modal (up to 25s)...")

        # Detect the modal using multiple selector strategies
        MODAL_XPATHS = [
            "//div[@role='dialog']",
            "//div[@role='alertdialog']",
            "//div[contains(@class,'modal')]",
            "//div[contains(@class,'dialog')]",
            "//div[contains(@class,'overlay')]",
            "//div[contains(@class,'MuiModal')]",
            "//div[contains(@class,'MuiDialog')]",
            "//section[@role='dialog']",
        ]
        modal_xpath = " | ".join(MODAL_XPATHS)

        def _detect_pin_modal(d):
            """Find a visible modal/dialog that contains OTP-style inputs or password input."""
            candidates = d.find_elements(By.XPATH, modal_xpath)
            for el in candidates:
                try:
                    if not el.is_displayed():
                        continue
                    el_inputs = el.find_elements(By.TAG_NAME, 'input')
                    # Check for OTP inputs (6 separate digit boxes)
                    otp = _find_otp_inputs(el_inputs, len(str(pin)))
                    if otp:
                        return el
                    # Check for classic password input
                    if any(i.get_attribute('type') == 'password' and i.is_displayed()
                           for i in el_inputs):
                        return el
                except Exception:
                    continue
            return None

        modal = None
        try:
            modal = WebDriverWait(driver, 25).until(_detect_pin_modal)
        except TimeoutException:
            pass

        if modal:
            print("  [OK] PIN confirmation modal detected.")
        else:
            # Fallback: look for ANY visible dialog
            print("  [!] PIN modal not found with OTP inputs — trying any visible dialog...")
            try:
                modal = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                    (By.XPATH, "//div[@role='dialog'] | //div[@role='alertdialog']")
                ))
                if modal.is_displayed():
                    print("  [OK] Fallback dialog found.")
                else:
                    modal = None
            except TimeoutException:
                pass

            if not modal:
                # Last attempt: check if OTP inputs appeared anywhere on the page
                page_inputs = driver.find_elements(By.TAG_NAME, 'input')
                page_otp = _find_otp_inputs(page_inputs, len(str(pin)))
                if page_otp:
                    print("  [OK] OTP inputs found on page (no explicit modal container).")
                else:
                    print("  [!] No dialog or OTP inputs found at all — dumping state:")
                    _dump_buttons(driver, "NO-MODAL")
                    _dump_inputs(driver, "NO-MODAL")

        time.sleep(1.5)  # Let modal animation fully complete

        # Enter PIN
        print("  Entering PIN in confirmation modal...")
        _dump_inputs(driver, "Confirmation modal")
        pin_ok = _find_and_enter_pin(driver, pin, context_element=modal, label="Modal")
        if not pin_ok:
            print("  [!] Could not enter PIN — order will likely be rejected.")
        time.sleep(1.5)

        # Wait for Confirmar to become ENABLED (disabled until all 6 PIN digits entered)
        CONFIRM_KW = ['CONFIRMAR', 'CONFIRM', 'AUTORIZAR', 'PROCESAR']
        print("  Waiting for Confirmar button to become enabled (up to 15s)...")
        confirmar_btn = None
        try:
            def _find_confirmar(d):
                search_root = modal if modal else d
                btns = search_root.find_elements(By.TAG_NAME, "button")
                for b in btns:
                    try:
                        if (any(kw in b.text.strip().upper() for kw in CONFIRM_KW)
                                and b.is_displayed()
                                and b.get_attribute("disabled") is None):
                            return b
                    except Exception:
                        continue
                return None

            confirmar_btn = WebDriverWait(driver, 15).until(_find_confirmar)
        except TimeoutException:
            pass

        if confirmar_btn:
            print(f"  [->] Confirmar button enabled: '{confirmar_btn.text.strip()}'")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", confirmar_btn)
            time.sleep(0.5)
            _safe_click(driver, confirmar_btn, "Confirmar")
        else:
            print("  [!] Confirmar never became enabled — attempting force-click...")
            _dump_buttons(driver, "CONFIRMAR-NOT-ENABLED")
            # Force-click: remove disabled attribute and click via JS
            search_root = modal if modal else driver
            modal_btns = search_root.find_elements(By.TAG_NAME, "button")
            force_clicked = False
            for b in modal_btns:
                try:
                    if any(kw in b.text.strip().upper() for kw in CONFIRM_KW) and b.is_displayed():
                        print(f"  [->] Force-clicking: '{b.text.strip()}'")
                        driver.execute_script(
                            "arguments[0].removeAttribute('disabled'); "
                            "arguments[0].click();", b)
                        force_clicked = True
                        break
                except Exception:
                    continue
            if not force_clicked:
                print("  [!!] Could not find any Confirmar button to force-click.")

        print("  Waiting for order to be processed (10s)...")
        time.sleep(10)

        # ── Step 11: Verify order was placed ─────────────────────
        print("\n[SeleniumTrader] > Step 11: Verifying order confirmation...")

        # 11a. Check for visual success/error indicators on the page
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        SUCCESS_KEYWORDS = [
            'orden creada', 'orden enviada', 'orden ejecutada',
            'exitosamente', 'éxito', 'exito', 'procesada',
            'confirmada', 'orden registrada', 'operación realizada',
        ]
        ERROR_KEYWORDS = [
            'error', 'rechazada', 'fallida', 'insuficiente',
            'no se pudo', 'inválid', 'invalid', 'fallo',
        ]

        found_success = any(kw in page_text for kw in SUCCESS_KEYWORDS)
        found_error = any(kw in page_text for kw in ERROR_KEYWORDS)

        # Check if PIN modal disappeared (good sign — means it was accepted)
        pin_modal_gone = True
        try:
            remaining_dialogs = driver.find_elements(
                By.XPATH, "//div[@role='dialog'] | //div[@role='alertdialog']")
            for d_el in remaining_dialogs:
                if d_el.is_displayed():
                    # Check if this dialog still has OTP inputs (PIN modal still open = bad)
                    d_inputs = d_el.find_elements(By.TAG_NAME, 'input')
                    otp = _find_otp_inputs(d_inputs, len(str(pin)))
                    if otp:
                        pin_modal_gone = False
                        break
        except Exception:
            pass

        # Check if cart is now empty (another success indicator)
        cart_empty = False
        try:
            for b in driver.find_elements(By.TAG_NAME, "button"):
                txt = b.text.strip().lower()
                if 'ejecutar todo' in txt and '(0)' in txt:
                    cart_empty = True
                    break
        except Exception:
            pass

        print(f"  Visual check: success_text={found_success}, error_text={found_error}, "
              f"pin_modal_gone={pin_modal_gone}, cart_empty={cart_empty}")

        # 11b. Check network logs as additional evidence
        all_posts = _get_captured_order_posts(driver)
        EXCLUDE_SUBPATHS = ('/validar-precio', '/calcular-costos', '/validar-cantidad')
        order_posts = [p for p in all_posts
                       if not any(p['url'].endswith(sub) for sub in EXCLUDE_SUBPATHS)]
        validation_posts = [p for p in all_posts if p not in order_posts]

        print(f"  Network summary: {len(all_posts)} total POSTs — "
              f"{len(order_posts)} order creation, {len(validation_posts)} validation/calc")
        for p in all_posts:
            tag = "[ORDER]" if p in order_posts else "[VALID]"
            print(f"    {tag} {p['url']}")
            if p.get('postData'):
                print(f"           payload: {p['postData']}")

        # 11c. Determine final result using all evidence
        # Case 1: Network logs confirmed order POST
        if order_posts:
            print(f"\n  [OK] ORDER CONFIRMED via network logs: {len(order_posts)} order POST(s)!")
            return {
                "success": True,
                "status": "SUBMITTED",
                "message": (f"Order {order_type} {quantity} {symbol} @ {price:.2f} VES submitted. "
                            f"{len(order_posts)} order POST confirmed via network logs."),
                "captured_posts": order_posts,
            }

        # Case 2: No order POST in logs, but visual indicators suggest success
        # (PIN modal closed, no error text, and either success text or cart emptied)
        if pin_modal_gone and not found_error and (found_success or cart_empty):
            print(f"\n  [OK] ORDER LIKELY CONFIRMED via visual indicators "
                  f"(success_text={found_success}, cart_empty={cart_empty}, no errors).")
            return {
                "success": True,
                "status": "SUBMITTED_VISUAL",
                "message": (f"Order {order_type} {quantity} {symbol} @ {price:.2f} VES submitted. "
                            "Confirmed via visual page indicators (network logs did not capture the POST)."),
            }

        # Case 3: PIN modal closed, no errors visible — likely succeeded but can't be 100% sure
        if pin_modal_gone and not found_error:
            print(f"\n  [OK] ORDER PRESUMED SUBMITTED — PIN modal closed, no errors detected. "
                  "Network logs did not capture the order POST (common with fetch-based APIs).")
            return {
                "success": True,
                "status": "SUBMITTED_PRESUMED",
                "message": (f"Order {order_type} {quantity} {symbol} @ {price:.2f} VES presumed submitted. "
                            "PIN was entered, Confirmar clicked, modal closed, no errors on page. "
                            "Network logs did not capture the order POST."),
            }

        # Case 4: Error detected on page
        if found_error:
            print(f"\n  [!!] ERROR detected on page after clicking Confirmar.")
            return {
                "success": False,
                "status": "ERROR_DETECTED",
                "message": (f"Order {order_type} {quantity} {symbol} @ {price:.2f} VES — "
                            "error text detected on page after confirmation attempt."),
            }

        # Case 5: PIN modal still open — PIN was not accepted
        if not pin_modal_gone:
            print(f"\n  [!!] PIN modal still open — PIN likely not accepted.")
            return {
                "success": False,
                "status": "PIN_REJECTED",
                "message": ("PIN confirmation modal still open after attempting to enter PIN. "
                            "PIN may be incorrect or was not properly entered."),
            }

        # Case 6: Fallback — unclear state
        print("\n  [?] Could not determine order status. Check browser window.")
        return {
            "success": True,
            "status": "SUBMITTED_UNVERIFIED",
            "message": (f"Selenium flow completed for {order_type} {quantity} {symbol} @ {price:.2f} VES. "
                        "Could not verify via network logs or visual indicators. "
                        "Check your Mercosur account for confirmation."),
        }

    except Exception as e:
        print(f"\n[SeleniumTrader] FATAL ERROR: {e}")
        logger.exception("Selenium order execution failed")
        return {"success": False, "error": str(e)}

    finally:
        print("\n[SeleniumTrader] Browser stays open 30s — check the result in the window.")
        time.sleep(30)
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    result = execute_selenium_order("BNC", 1, 235.00, "COMPRA")
    print("\n===== RESULT =====")
    print(json.dumps(result, indent=2, ensure_ascii=False))
