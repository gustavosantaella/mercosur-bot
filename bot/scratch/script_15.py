import time
import re
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from src.config import (
    BNC_URL,
    BNC_TARJETA,
    BNC_CEDULA,
    BNC_PASSWORD,
    FETCH_BNC_BALANCE,
    BNC_HEADLESS
)

class BNCScraper:
    """
    Extractor automatizado de saldo mediante Selenium para BNC Personas (https://personas.bncenlinea.com/).
    Soporta inicio de sesión con Número de Tarjeta, Cédula de Identidad y Contraseña.
    Incluye logout obligatorio (Cerrar Sesión) para garantizar cierres limpios de sesión.
    """

    def __init__(
        self,
        tarjeta: str = BNC_TARJETA,
        cedula: str = BNC_CEDULA,
        password: str = BNC_PASSWORD,
        headless: bool = BNC_HEADLESS
    ):
        self.tarjeta = tarjeta
        self.cedula = cedula
        self.password = password
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def _init_driver(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def fetch_balance(self) -> Optional[float]:
        """
        Navega a BNC en Línea, realiza el login, extrae el saldo disponible y ejecuta el logout de seguridad.
        """
        if not FETCH_BNC_BALANCE:
            print("[BNC Scraper] Extracción desactivada en configuración (FETCH_BNC_BALANCE=0).")
            return None

        if not (self.tarjeta and self.cedula and self.password):
            print("[BNC Scraper] Faltan credenciales de BNC en .env (BNC_TARJETA, BNC_CEDULA, BNC_PASSWORD).")
            return None

        saldo_encontrado: Optional[float] = None

        try:
            print(f"[BNC Scraper] Iniciando navegador Chrome (Headless={self.headless})...")
            self._init_driver()
            
            print(f"[BNC Scraper] Navegando a {BNC_URL}...")
            self.driver.get(BNC_URL)
            wait = WebDriverWait(self.driver, 20)

            time.sleep(3)

            # Buscar e ingresar número de tarjeta
            try:
                tarjeta_elem = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//input[contains(@id, 'card') or contains(@id, 'tarjeta') or contains(@placeholder, 'Tarjeta') or contains(@name, 'tarjeta')] | //input[@type='text'][1]"))
                )
                tarjeta_elem.clear()
                tarjeta_elem.send_keys(self.tarjeta)
            except Exception as e_t:
                print(f"[BNC Scraper Warning] Error en campo tarjeta: {e_t}")

            # Buscar e ingresar Cédula
            try:
                cedula_elem = self.driver.find_element(By.XPATH, "//input[contains(@id, 'cedula') or contains(@placeholder, 'Cédula') or contains(@name, 'cedula') or contains(@name, 'identity')] | //input[@type='text'][2]")
                cedula_elem.clear()
                cedula_elem.send_keys(self.cedula)
            except Exception as e_c:
                print(f"[BNC Scraper Warning] Error en campo cédula: {e_c}")

            # Buscar e ingresar Password
            try:
                pass_elem = self.driver.find_element(By.XPATH, "//input[@type='password']")
                pass_elem.clear()
                pass_elem.send_keys(self.password)
            except Exception as e_p:
                print(f"[BNC Scraper Warning] Error en campo clave: {e_p}")

            # Clic en botón "Continuar" / "Ingresar"
            try:
                btn_continuar = self.driver.find_element(By.XPATH, "//button[contains(., 'Continuar') or contains(., 'Ingresar') or contains(., 'Iniciar')] | //input[@type='submit']")
                btn_continuar.click()
            except Exception as e_b:
                print(f"[BNC Scraper Warning] Error en botón ingresar: {e_b}")

            print("[BNC Scraper] Esperando carga del resumen de cuenta...")
            time.sleep(6)

            # Extraer saldo desde la página
            page_text = self.driver.page_source
            match = re.search(r'(?:Bs\.?|VES)\s*([\d\.,]+)|([\d\.,]+)\s*(?:Bs\.?|VES)', page_text, re.IGNORECASE)
            if match:
                raw_val = match.group(1) or match.group(2)
                val_clean = raw_val.replace('.', '').replace(',', '.')
                saldo_encontrado = float(val_clean)
                print(f"[BNC Scraper] ✔ Saldo disponible detectado: {saldo_encontrado:,.2f} VES")
            else:
                print("[BNC Scraper] No se pudo extraer la cifra de saldo numérico del dashboard.")

        except Exception as e:
            print(f"[BNC Scraper Error] {e}")

        finally:
            # Requisito obligatorio: Manejar Logout (Cerrar Sesión) para garantizar que la sesión se cierre limpiamente
            if self.driver:
                try:
                    print("[BNC Scraper] Ejecutando Logout (Cerrar Sesión) de seguridad...")
                    logout_buttons = self.driver.find_elements(By.XPATH, "//a[contains(., 'Salir') or contains(., 'Cerrar') or contains(., 'Logout')] | //button[contains(., 'Salir') or contains(., 'Cerrar')]")
                    if logout_buttons:
                        logout_buttons[0].click()
                        time.sleep(2)
                except Exception as ex_logout:
                    print(f"[BNC Scraper Logout Warning] {ex_logout}")

                print("[BNC Scraper] Cerrando navegador...")
                self.driver.quit()
                self.driver = None

        return saldo_encontrado
