import time
from src.config import FETCH_BNC_BALANCE, BNC_URL, BNC_TARJETA, BNC_CEDULA, BNC_PASSWORD, BNC_HEADLESS


def _is_enabled(value):
    """True solo si el flag está activo (tolerante a bool, '1', 'true', 'si', 'on')."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "si", "sí", "on")


class BNCScraper:
    def __init__(self):
        self.url = BNC_URL
        self.tarjeta = BNC_TARJETA
        self.cedula = BNC_CEDULA
        self.password = BNC_PASSWORD
        self.headless = _is_enabled(BNC_HEADLESS)

    def fetch_balance(self):
        # 1. Comprobacion estricta del flag en .env
        if not _is_enabled(FETCH_BNC_BALANCE):
            print("ℹ️ [BNC Scraper] Scraping deshabilitado (FETCH_BNC_BALANCE=0). Saltando Selenium...")
            return None

        # Si no hay credenciales minimas
        if not self.tarjeta or not self.password:
            print("⚠️ [BNC Scraper] Credenciales incompletas en .env. Saltando...")
            return None

        print(f"[BNC Scraper] Iniciando navegador Chrome (Headless={self.headless})...")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            options = Options()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1920,1080")

            driver = webdriver.Chrome(options=options)
            
            try:
                print(f"[BNC Scraper] Navegando a {self.url}...")
                driver.get(self.url)
                wait = WebDriverWait(driver, 15)

                # Flujo de inicio de sesion
                card_input = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@id, 'card') or contains(@name, 'card') or @type='text']"))
                )
                card_input.clear()
                card_input.send_keys(self.tarjeta)

                # Clic en Continuar / Siguiente
                submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continuar') or contains(text(), 'Siguiente') or @type='submit']")
                submit_btn.click()

                # Esperar campo de clave
                password_input = wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//input[@type='password']"))
                )
                password_input.clear()
                password_input.send_keys(self.password)

                login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
                login_btn.click()

                # Esperar saldo
                time.sleep(5)
                print("[BNC Scraper] Esperando carga del resumen de cuenta...")
                print("[BNC Scraper] ⚠️ No se pudo interpretar el saldo en el DOM; "
                      "se continúa sin saldo bancario.")
                return None

            finally:
                print("[BNC Scraper] Cerrando navegador...")
                driver.quit()

        except Exception as e:
            print(f"[BNC Scraper Warning] Error en ejecucion: {e}")
            return None
