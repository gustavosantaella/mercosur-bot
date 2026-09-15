# 🤖 Bot Mercosur Casa de Bolsa — BVC

Bot de análisis e inversión para la **Bolsa de Valores de Caracas** vía
**Mercosur Casa de Bolsa**: consulta saldos, cartera, cotizaciones y noticias, y
genera **consejos de inversión** con un motor cuantitativo propio (con o sin saldo
disponible), además de llevar un **histórico de mercado** que permite *backtesting*
del propio motor.

> ⚠️ **Aviso**: los informes son análisis automatizados de datos de mercado y **no**
> constituyen asesoría financiera vinculante. Verifica cada orden antes de operar.

---

## 📑 Índice

1. [¿Qué hace el bot?](#-qué-hace-el-bot)
2. [Requisitos e instalación](#-requisitos-e-instalación)
3. [Inicio rápido](#-inicio-rápido)
4. [Menú interactivo](#-menú-interactivo)
5. [Parámetros de la CLI](#-parámetros-de-la-cli)
6. [Variables de entorno (`.env`)](#-variables-de-entorno-env)
7. [Cómo funciona el motor de consejos](#-cómo-funciona-el-motor-de-consejos)
8. [Histórico y backtesting](#-histórico-y-backtesting)
9. [Cartera real y P&L](#-cartera-real-y-pl)
10. [Archivos generados](#-archivos-generados)
11. [Solución de problemas](#-solución-de-problemas)
12. [Seguridad](#-seguridad)
13. [Validación (tests)](#-validación-tests)
14. [Estructura del proyecto](#-estructura-del-proyecto)
15. [Estado y pendientes](#-estado-y-pendientes)

---

## 🎯 ¿Qué hace el bot?

| Capacidad | Descripción |
|-----------|-------------|
| 💰 **Saldos** | Saldo disponible, total y bloqueado de Mercosur (parseo tolerante a formatos). |
| 🧾 **Cartera** | Posiciones reales con costo promedio, valor de mercado y **P&L** por posición. |
| 📈 **Instrumentos** | Cotizaciones en vivo con filtro de símbolos excluidos. |
| 📋 **Órdenes** | Órdenes registradas en la cuenta. |
| 🎯 **Consejos IA** | Responde *"¿en qué empresa es mejor invertir hoy?"*, **con o sin saldo**. |
| 🧠 **Análisis completo** | Compras, rotación de capital, liquidez y reglas de portafolio. |
| 📚 **Histórico** | Guarda cada rueda en SQLite → tendencia, momentum y volatilidad por emisor. |
| 🧪 **Backtesting** | Mide si el motor bate al mercado (edge/aciertos) y **ajusta sus pesos con datos**. |
| 📰 **Noticias** | RSS financieros con sentimiento y detección de menciones por emisor. |

**Principios de diseño**: nunca se cae por un dato raro (todo parseo es tolerante), degrada
con elegancia (sin internet, sin saldo, sin cartera) y **nunca inventa datos**: si algo no
está disponible, lo dice explícitamente.

---

## 📦 Requisitos e instalación

- **Python 3.10+** (probado en 3.14.7)
- Windows / Linux / macOS
- Conexión a internet para datos de mercado y noticias (el bot funciona igual sin ella)

```powershell
cd bot
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Dependencias (`requirements.txt`):

| Paquete | Para qué |
|---------|----------|
| `requests` | API de Mercosur y Ollama |
| `python-dotenv` | Lectura del archivo `.env` |
| `rich` | Interfaz de consola (tablas, paneles, Markdown) |
| `selenium` + `webdriver-manager` | Scraping del banco BNC (opcional, desactivado por defecto) |
| `dnspython` | Resolución DNS alternativa para `mercosur.com.ve` (opcional pero recomendado) |
| `beautifulsoup4` + `feedparser` | Reserva para procesado de noticias |

**Configuración mínima**: crea `bot/.env` con tus credenciales:

```env
MERCOSUR_EMAIL=tu_correo@ejemplo.com
MERCOSUR_PASSWORD=tu_password
MERCOSUR_CLAVE_OPERACIONES=tu_clave_6_digitos
```

---

## 🚀 Inicio rápido

```powershell
cd bot

# 1) Menú interactivo (sin argumentos)
.venv\Scripts\python.exe main.py

# 2) Consejo del día y salir (ideal para programar a diario)
.venv\Scripts\python.exe main.py --advice --no-color

# 3) Análisis completo simulando un saldo de 5.000 VES
.venv\Scripts\python.exe main.py --analysis --budget 5000

# 4) Validar el motor con el histórico acumulado
.venv\Scripts\python.exe main.py --backtest

# 5) Ajustar los pesos del motor con datos reales
.venv\Scripts\python.exe main.py --tune-weights

# 6) Ejecutar la batería de validación (72 tests)
.venv\Scripts\python.exe -m unittest validate_bot -v
```

### Programar el consejo diario (Windows)

```powershell
schtasks /create /tn "Mercosur Bot Consejo" /tr "C:\ruta\bot\.venv\Scripts\python.exe C:\ruta\bot\main.py --advice --quiet --no-pause" /sc daily /st 13:00
```

---

## 🖥️ Menú interactivo

Al ejecutar `main.py` sin argumentos se muestra el menú (se limpia la consola en cada vuelta):

| Opción | Nombre | Qué hace exactamente |
|:------:|--------|----------------------|
| **1** | 💰 Ver Saldos, Cartera y Estado de Cuenta | `get_balances()` + `fetch_portfolio()`: tabla de disponible/total/bloqueado y tabla de posiciones con P&L. |
| **2** | 🚀 Inversión Automática / Análisis Completo IA | Saldo + cartera + cotizaciones + noticias + histórico → informe completo (mejor empresa, compras, rotación, liquidez, cartera, reglas) y lo guarda en `data/informe_inversion.md`. Si `AUTO_EXECUTE_ORDERS=1` muestra la orden sugerida y avisa que **no** se envía nada. |
| **3** | 📈 Instrumentos | Lista las empresas en cotización (precio, variación, monto negociado) y guarda `data/cotizaciones.json`. |
| **4** | 📋 Órdenes | Lista tus órdenes (tipo, estado, cantidad, precio, monto bloqueado). |
| **5** | 🎯 Consejos | **Saldo + instrumentos + noticias + histórico + cartera** → *"¿en qué empresa es mejor invertir hoy?"* con top 5, tendencia, contexto de noticias y plan de acción. Guarda el informe. |
| **0** | 🚪 Salir | Cierra el programa. |

Al arrancar (menú o CLI) el bot autentica y muestra si **reutilizó la sesión guardada**
(`🔐 sesión guardada reutilizada`) o inició una nueva (`🔑 nueva sesión iniciada`).

---

## ⌨️ Parámetros de la CLI

Todos son **opcionales**. Sin argumentos → menú interactivo.

### Acciones (elige una; la primera que aparezca en esta lista gana)

| Parámetro | Ejecuta | Equivale a |
|-----------|---------|:----------:|
| `--option {1,2,3,4,5}` | La opción del menú indicada y sale | — |
| `--balance` | Saldos y cartera | `--option 1` |
| `--portfolio` | Alias de `--balance` | `--option 1` |
| `--analysis` | Análisis completo IA | `--option 2` |
| `--instruments` | Cotizaciones | `--option 3` |
| `--orders` | Mis órdenes | `--option 4` |
| `--advice` | Consejo: ¿en qué empresa invertir? | `--option 5` |
| `--backtest` | Backtesting del motor con el histórico | — |
| `--tune-weights` | Backtesting + *grid-search* de pesos | — |

### Ajustes del comportamiento

| Parámetro | Tipo | Default | Qué controla |
|-----------|------|:-------:|--------------|
| `--budget N` | float (VES) | *(ninguno)* | Saldo manual: **sobreescribe** el saldo de la API (útil si falla o para simular aportes). |
| `--top N` | int | `5` | Cuántas opciones considerar/destacar en los rankings. |
| `--no-history` | flag | desactivado | Ignora el histórico SQLite en el consejo (usa solo la rueda actual). |
| `--no-pause` | flag | desactivado | No esperar `ENTER` entre pantallas (para cron/scripting). |
| `--force-login` | flag | desactivado | Borra la sesión guardada y fuerza un login nuevo. |
| `--no-color` | flag | desactivado | Salida sin colores (logs, CI, redirección a archivo). |
| `--quiet` | flag | desactivado | Silencia el log por consola (sigue escribiendo en `data/bot.log`). |
| `--verbose` | flag | desactivado | Log detallado (`DEBUG`) en consola y archivo. |

### Ejemplos

```powershell
# Consejo con saldo simulado y solo 3 opciones, sin esperas y sin color
.venv\Scripts\python.exe main.py --advice --budget 25000 --top 3 --no-pause --no-color

# Ver ayuda completa
.venv\Scripts\python.exe main.py --help
```

---

## ⚙️ Variables de entorno (`.env`)

Todas se leen con **tipado estricto**: los flags booleanos aceptan
`1 / true / yes / si / on` (cualquier otro valor = `False`). Las rutas relativas se
resuelven contra la carpeta `bot/`. Los símbolos se normalizan a mayúsculas.

> 💡 Ninguna es obligatoria salvo las **credenciales de Mercosur**. El archivo `.env`
> está ignorado por git.

### 🔐 Credenciales de Mercosur

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `MERCOSUR_EMAIL` | *(vacío)* | Correo de tu cuenta Mercosur. Si falta, el bot entra en modo **invitado** (solo cotizaciones públicas). |
| `MERCOSUR_USER` | *(vacío)* | Alternativa a `MERCOSUR_EMAIL` (compatibilidad). |
| `MERCOSUR_PASSWORD` | *(vacío)* | Contraseña de Mercosur. |
| `MERCOSUR_CLAVE_OPERACIONES` | *(vacío)* | Clave de 6 dígitos para **operar** (OTP). |
| `MERCOSUR_PIN` | *(vacío)* | Alias de `MERCOSUR_CLAVE_OPERACIONES` (compatibilidad). |

### 🌐 URLs de la API de Mercosur

Normalmente **no hace falta tocarlas**: todas derivan de `MERCOSUR_BASE_URL`.

| Variable | Default |
|----------|---------|
| `MERCOSUR_BASE_URL` | `https://cm.mercosur.com.ve` |
| `MERCOSUR_LOGIN_URL` | `{BASE}/portal/login` |
| `MERCOSUR_COTIZACIONES_URL` | `{BASE}/portal/mercado/dashboard/cotizaciones` |
| `MERCOSUR_SALDOS_URL` | `{BASE}/portal/saldos` |
| `MERCOSUR_MOVIMIENTOS_URL` | `{BASE}/portal/movimientos` |
| `MERCOSUR_COMPRA_VENTA_URL` | `{BASE}/portal/compra-venta` |
| `MERCOSUR_ORDENES_URL` | `{BASE}/portal/ordenes` |
| `MERCOSUR_TRANSFERENCIAS_URL` | `{BASE}/portal/transferencias` |
| `MERCOSUR_PERFIL_URL` | `{BASE}/portal/perfil` |
| `MERCOSUR_LOGOUT_URL` | `{BASE}/portal/logout` |
| `MERCOSUR_PORTAFOLIO_URL` | `{BASE}/portal/portafolio` — **endpoint de la cartera**. Si tu cuenta usa otra ruta, cámbiala aquí. |
| `MERCOSUR_HEADLESS` | `True` | Si el flujo Selenium corre sin ventana. |

> 🔎 **Cartera multi-endpoint**: además de `MERCOSUR_PORTAFOLIO_URL`, el bot prueba en orden
> `/portal/posiciones`, `/portal/cartera` y `/portal/titulos`. Usa el primero que devuelva
> posiciones válidas y lo registra en el log.

### 🗂️ Rutas y archivos

| Variable | Default | Qué es |
|----------|---------|--------|
| `DATA_DIR` | `data/` | Carpeta de datos (se crea automáticamente). |
| `TOKEN_FILE` | `data/session_token.json` | **Sesión guardada** (token + fecha + cliente). |
| `QUOTES_FILE` | `data/cotizaciones.json` | Última copia de cotizaciones (**caché offline**). |
| `REPORT_FILE` | `data/informe_inversion.md` | Último informe generado. |
| `QUOTES_LATEST_FILE` | `quotes_latest.json` | Ruta *legacy* (solo lectura de respaldo). |
| `DATA_FILE` | `data/data.json` | Reservado para datos auxiliares. |

### 🤖 Inteligencia Artificial y noticias

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `USE_AI` | `True` | `1`: habilita noticias + LLM (si Ollama responde). `0`: el bot omite noticias y usa solo el motor cuantitativo. **Los consejos se generan en ambos casos.** |
| `OLLAMA_HOST` | `http://localhost:11434` | Servidor local de Ollama. |
| `OLLAMA_MODEL` | `llama3.2` | Modelo a usar para el informe enriquecido. |
| `NEWS_FEEDS` | *(3 feeds por defecto)* | URLs RSS separadas por coma; si se define, reemplaza las fuentes por defecto. |

Fuentes por defecto: *Finanzas Digital*, *Google News – Bolsa de Valores de Caracas* y
*Google News – Economía Venezuela*.

### 🌐 Red, sesión y caché

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `HTTP_TIMEOUT` | `15` | Segundos de espera de cada petición HTTP. |
| `TIMEOUT` | `15` | Alias de `HTTP_TIMEOUT` (compatibilidad). |
| `SESSION_TTL_HOURS` | `12.0` | Vida de la sesión guardada cuando el JWT no trae `exp`. |
| `USE_QUOTES_CACHE` | `True` | Si la API falla, usar `data/cotizaciones.json` (modo offline). |

### 📚 Histórico de mercado

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `HISTORY_ENABLED` | `True` | Guarda un snapshot por rueda en SQLite. |
| `HISTORY_DB` | `data/market_history.db` | Base de datos del histórico. |
| `HISTORY_WINDOW` | `30` | Cuántas ruedas atrás se consideran para tendencia/volatilidad. |

### ⚖️ Pesos del motor de puntaje

Se pueden ajustar a mano o con `--tune-weights` (grid-search basado en datos reales).

| Variable | Default | Qué controla |
|----------|:-------:|--------------|
| `SCORE_WEIGHT_LIQUIDITY` | `0.50` | Peso de la liquidez negociada (participación de mercado, %). |
| `SCORE_WEIGHT_VARIATION` | `0.30` | Peso de la variación diaria (%). |
| `SCORE_WEIGHT_TREND` | `0.50` | Peso de la tendencia histórica (%, requiere ≥2 ruedas). |
| `SCORE_WEIGHT_DIVIDEND` | `20.0` | Puntos fijos si el emisor paga dividendos (base BVC). |
| `SCORE_WEIGHT_NEWS` | `2.0` | Puntos por mención del emisor en noticias (con signo del sentimiento). |
| `BACKTEST_TOP_N` | `3` | Cuántos instrumentos del ranking se evalúan en el backtest. |
| `BACKTEST_HORIZON` | `3` | Ruedas hacia adelante para medir el retorno del backtest. |

### 🚫 Exclusiones y logging

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `EXCLUDE_SYMBOL` | *(vacío)* | Símbolos a excluir de listados y consejos, separados por coma (ej. `BVL, ABC.A`). |
| `EXCLUDE_SYMBOLS` | *(vacío)* | Alias de `EXCLUDE_SYMBOL`; si ambos existen, se combinan. |
| `LOG_FILE` | `data/bot.log` | Archivo de log (rotación automática). |
| `LOG_LEVEL` | `INFO` | Nivel de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_MAX_BYTES` | `1000000` | Tamaño máximo por archivo antes de rotar. |
| `LOG_BACKUPS` | `3` | Número de archivos de log rotados que se conservan. |

### 🏦 BNC en línea (opcional, desactivado por defecto)

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `FETCH_BNC_BALANCE` | `False` | `1` habilita el scraping del banco con Selenium. |
| `BNC_URL` | `https://personas.bncenlinea.com/` | Portal del banco. |
| `BNC_TARJETA` | *(vacío)* | Número de tarjeta. |
| `BNC_CEDULA` | *(vacío)* | Cédula del titular. |
| `BNC_PASSWORD` | *(vacío)* | Clave de banca en línea. |
| `BNC_HEADLESS` | `True` | Ejecutar Chrome sin ventana. |

### 📤 Ejecución de órdenes

| Variable | Default | Qué es |
|----------|:-------:|--------|
| `AUTO_EXECUTE_ORDERS` | `False` | `1`: muestra la orden sugerida lista para copiar y avisa de su estado. `0`: solo recomendaciones. **Hoy la ejecución automática no está implementada** (ver [pendientes](#-estado-y-pendientes)): con `1` el bot **no envía ninguna orden real** y lo informa explícitamente. |

### 📄 Plantilla de `.env` completa

```env
# ── Credenciales Mercosur ───────────────────────────────
MERCOSUR_EMAIL=tu_correo@ejemplo.com
MERCOSUR_PASSWORD=tu_password
MERCOSUR_CLAVE_OPERACIONES=000000
USE_AI=1
AUTO_EXECUTE_ORDERS=0
EXCLUDE_SYMBOL=BVL

# ── IA local (opcional) ─────────────────────────────────
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# ── Comportamiento ──────────────────────────────────────
HTTP_TIMEOUT=15
SESSION_TTL_HOURS=12
USE_QUOTES_CACHE=1
HISTORY_ENABLED=1

# ── Motor de puntaje (ajustable con --tune-weights) ─────
SCORE_WEIGHT_LIQUIDITY=0.50
SCORE_WEIGHT_VARIATION=0.30
SCORE_WEIGHT_TREND=0.50
SCORE_WEIGHT_DIVIDEND=20.0
SCORE_WEIGHT_NEWS=2.0
```

---

## 🧠 Cómo funciona el motor de consejos

### 1. Insumos

| Insumo | Fuente | Si falta… |
|--------|--------|-----------|
| Saldo disponible | API de Mercosur | saldo `0` → **igual hay consejo** con plan de entrada |
| Instrumentos | Cotizaciones de Mercosur | si la API falla → caché local; sin nada → informe "sin datos" |
| Noticias | RSS (`NEWS_FEEDS`) | sentimiento `neutro` y el informe lo indica |
| Histórico | SQLite (`market_history.db`) | sin ruedas previas → puntaje solo con la rueda actual |
| Cartera | Endpoint de portafolio | sin posiciones → lo dice explícitamente |
| Dividendos | Base BVC (`src/ai/dividends.py`) | política "sujeta a Asamblea" |

### 2. Fórmula del puntaje (única para consejo y backtest)

```
score = (liquidez_share_% × 0.50)     # participación en el monto negociado del mercado
      + (variación_%      × 0.30)     # variación del día
      + (tendencia_%      × 0.50)     # tendencia histórica (solo con ≥2 ruedas)
      + 20.0                          # si el emisor paga dividendos (base BVC)
      + (menciones_noticias × 2.0 × signo_sentimiento)
```

Los pesos son los de la sección anterior y se pueden recalibrar con `--tune-weights`.

### 3. Reglas de decisión (por orden de prioridad)

| Condición | Acción sugerida |
|-----------|-----------------|
| `score ≥ 25` y variación `> 0` | 🟢 **COMPRAR** — *Inversión fuerte en activo líquido* |
| variación `> 0` y monto negociado `≥ 100.000 VES` | 🟢 **COMPRAR (moderado)** |
| paga dividendos y liquidez `≥ 1%` | 🟢 **COMPRAR (por dividendos)** |
| variación `< 0` y liquidez `≥ 5%` | 🔴 **VENDER / REBALANCEAR** |
| monto negociado `< 5.000 VES` | 🔴 **VENDER PARA LIQUIDEZ** |
| tendencia `> 8%` en `≥ 3` ruedas | 🟢 **COMPRAR (tendencia)** *(eleva un 🟡 MANTENER)* |
| resto | 🟡 **MANTENER** |

### 4. Consejos **con y sin saldo**

- **Con saldo**: *"Con tu saldo actual (X VES) puedes comprar N acciones (inversión de Y VES)"*.
- **Sin saldo (0 o no disponible)**: el bot **igual entrega** el mejor instrumento, el top 5 y un
  **plan de entrada con presupuestos de referencia** de **1.000 / 10.000 / 100.000 VES**
  indicando cuántas acciones alcanzan en cada caso.

Para simular un saldo distinto usa `--budget N` (por ejemplo `--budget 50000`).

---

## 📚 Histórico y backtesting

### Base de datos (`data/market_history.db`)

```sql
snapshot_runs(rueda PRIMARY KEY, captured_at, instruments, total_cash)
quote_snapshots(symbol, rueda, captured_at, price, var_pct, cash_amount)
    -- PRIMARY KEY (symbol, rueda)
```

Cada consulta de cotizaciones **en vivo** guarda un snapshot de la rueda. Reejecutar el mismo día
**actualiza** los datos en lugar de duplicarlos (*upsert*). Con eso el motor calcula **tendencia**,
**momentum** (media de las últimas 3 variaciones) y **volatilidad** por emisor.

> Los datos de **caché offline** no se guardan como rueda nueva, para no contaminar el histórico
> con precios antiguos.

### Backtesting (`--backtest`)

Recorre las ruedas guardadas: para cada rueda *t* recalcula el score con los datos de esa rueda y
mide el retorno de los **Top-N** hasta la rueda *t + horizonte* frente al **promedio del mercado**:

| Métrica | Significado |
|---------|-------------|
| **Aciertos** (`hit_rate`) | % de ruedas en que el Top-N superó al promedio del mercado. |
| **Retorno Top-N** | Retorno medio del Top-N en el horizonte. |
| **Retorno mercado** | Retorno medio de todos los instrumentos comparables. |
| **Edge (ventaja)** | *Retorno Top-N − Retorno mercado*. Positivo = el motor aporta valor. |

Si aún no hay suficientes ruedas, el informe lo dice:
*"Se necesitan más de N ruedas guardadas (hay M)"*.

### Ajuste de pesos (`--tune-weights`)

Prueba combinaciones de `liquidez × variación` (0.30/0.50/0.70 × 0.10/0.30/0.50), mide el edge de
cada una y sugiere la mejor con el bloque `.env` listo para copiar. Si los pesos actuales ya son
los mejores, recomienda **no cambiar nada**.

---

## 🧾 Cartera real y P&L

El bot intenta obtener tus posiciones desde varios endpoints (ver
[URLs de Mercosur](#-urls-de-la-api-de-mercosur)) y normaliza estos campos:

| Campo normalizado | Claves aceptadas de la API |
|-------------------|----------------------------|
| `symbol` | `cod_simb`, `simbolo`, `symbol` |
| `quantity` | `cantidad_disponible`, `cantidad`, `tenencia`, `titulos` |
| `avg_price` | `precio_promedio`, `costo_promedio`, `precio_compra` |
| `market_price` | `precio_ultimo`, `precio_mercado`, `precio_actual` |
| `market_value` | `valor_mercado`, `valor_actual` (o `cantidad × precio`) |
| `cost` | `monto_invertido`, `costo_total` (o `cantidad × costo promedio`) |

Se calculan **P&L** = `valor_mercado − costo` y **P&L %**. Cada posición se reevalúa con las
cotizaciones del momento, y el informe muestra tu cartera junto a la recomendación de la IA para
cada emisor que posees (sección *"🧾 Tu cartera real"* en los informes).

> Si ningún endpoint devuelve posiciones, el informe dice *"Sin posiciones disponibles (cartera
> vacía o endpoint no accesible)"* — **nunca inventa** datos. Ajusta `MERCOSUR_PORTAFOLIO_URL`
> cuando identifiques la ruta correcta en tu cuenta.

---

## 📁 Archivos generados

| Ruta | Contenido | ¿En git? |
|------|-----------|:--------:|
| `data/session_token.json` | Token JWT, fecha de guardado y datos del cliente | ❌ ignorado |
| `data/cotizaciones.json` | Última copia de cotizaciones (caché offline) | ❌ ignorado |
| `data/informe_inversion.md` | Último informe de inversión en Markdown | ❌ ignorado |
| `data/market_history.db` | Histórico de ruedas (SQLite) | ❌ ignorado |
| `data/bot.log` (+ `.1`, `.2`…) | Log rotativo | ❌ ignorado |
| `.env` | Credenciales y configuración | ❌ ignorado |

**Estructura interna del token guardado:**

```json
{ "token": "<JWT>", "saved_at": "2026-09-15T13:08:01", "cliente": { "nombre": "…" } }
```

---

## 🛠️ Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `No se pudieron obtener saldos de la cuenta` | Endpoint distinto, sesión expirada o cambio en la API | Ejecuta `--force-login`; revisa `MERCOSUR_SALDOS_URL`; mira `data/bot.log` |
| Saldo disponible en `0.00` pero tienes fondos | Fondos **bloqueados** por órdenes abiertas | Revisa la columna *Bloqueado* y la opción 4 (órdenes) |
| `Sin cotizaciones disponibles (ni en vivo ni en caché)` | Sin internet y sin caché previa | Verifica la conexión; ejecuta el bot con internet al menos una vez para llenar la caché |
| `⚠️ Sin conexión a Mercosur: usando cotizaciones guardadas hace X h` | API caída; modo offline activo | Es normal: el consejo se genera con la caché. Reintenta más tarde |
| Noticias = `0` | Sin internet, feeds caídos o `USE_AI=0` | Revisa `NEWS_FEEDS`; activa `USE_AI=1` |
| `No se pudieron obtener posiciones de la cartera` | El endpoint de cartera no responde o cambió | Ajusta `MERCOSUR_PORTAFOLIO_URL` (el log registra qué URL se intentó) |
| `Se necesitan más de N ruedas guardadas` | Histórico insuficiente | Programa `--advice` a diario; el backtest se activa solo |
| `Aún no hay histórico suficiente` en el consejo | Menos de 2 ruedas | Ídem: acumular ruedas diarias |
| `AUTO_EXECUTE_ORDERS=1` pero no se opera | La ejecución automática no está implementada | Usa la orden sugerida del informe y ejecútala en Mercosur |
| Error de DNS con `mercosur.com.ve` | Resolución bloqueada | `pip install dnspython` (el bot prueba varios DNS públicos) |
| El log no aparece | Nivel o modo silencioso | Usa `--verbose`; revisa `data/bot.log` |

---

## 🔒 Seguridad

1. **El token nunca se imprime**: la autenticación solo informa el estado de la sesión.
2. **`.env` fuera de git** (`.gitignore`), igual que `session_token.json` y todo `data/`.
3. **Sin órdenes automáticas**: aunque `AUTO_EXECUTE_ORDERS=1`, el bot no envía órdenes reales.
4. **Sesión con caducidad**: el JWT se descarta cuando expira (`exp`) o supera `SESSION_TTL_HOURS`.
5. **Datos locales**: credenciales y token viven solo en tu máquina.

> Recomendación: si compartes pantalla o capturas, revisa que no se vean el `.env` ni `data/`.

---

## ✅ Validación (tests)

```powershell
.venv\Scripts\python.exe -m unittest validate_bot -v      # detallado (72 tests)
.venv\Scripts\python.exe -m unittest validate_bot         # resumen
```

La suite es **100% offline** (sin credenciales ni red) y cubre:

| Grupo | Qué verifica |
|-------|--------------|
| `TestConfig` | Flags como `bool` real, rutas absolutas, feeds estructurados |
| `TestAdvisorAlwaysGivesAdvice` | Consejo **con saldo, con saldo 0 y sin saldo**; orden del ranking; exclusión de símbolos; datos sucios (`"N/A"`, `"1.234,56"`, `None`) |
| `TestNewsFetcher` | Parseo RSS **y** Atom, entidades HTML, límites, sentimiento, fallback sin internet |
| `TestSessionPersistence` | Guardado/reutilización/expiración del JWT y que **no** se exponga el token |
| `TestOfflineQuotesFallback` | Uso de la caché, caché deshabilitada y guardado de datos en vivo |
| `TestMarketHistory` | Snapshots, *upsert* del mismo día, tendencia/momentum/volatilidad |
| `TestBacktesting` | El backtest detecta el *pick* ganador, edge positivo e informes |
| `TestPortfolio` | Parseo multi-formato de posiciones y cálculo de P&L |
| `TestAdvisorWithHistory` | El histórico cambia el puntaje y el informe |
| `TestCliAndLogging` | Flags de la CLI, mapeo de acciones, log rotativo a archivo |
| `TestUiAndMenu` / `TestMainWiring` | Menú con opción 5, helpers de UI, cableado de opciones |

---

## 🗂️ Estructura del proyecto

```
bot/
├── main.py                     # Menú interactivo + CLI (opciones 1-5, --advice, --backtest…)
├── validate_bot.py             # Suite de validación (72 tests offline)
├── requirements.txt
├── .env                        # Credenciales y configuración (ignorado por git)
├── README.md                   # Este documento
├── data/                       # Datos generados (ignorado por git)
│   ├── session_token.json
│   ├── cotizaciones.json
│   ├── informe_inversion.md
│   ├── market_history.db
│   └── bot.log
└── src/
    ├── config/__init__.py      # Configuración tipada (único punto de lectura del .env)
    ├── logging_setup.py        # Logging a consola + archivo rotativo
    ├── ui.py                   # Interfaz Rich: menús, tablas, paneles, informes
    ├── ai/
    │   ├── investment_advisor.py  # Motor de puntaje, informes y consejos
    │   ├── backtest.py            # Backtesting y ajuste de pesos
    │   └── dividends.py           # Base de dividendos de emisores BVC
    ├── client/
    │   ├── mercosur_client.py  # API: login/sesión, saldos, cotizaciones, cartera, órdenes
    │   ├── selenium_trader.py  # Ejecución de órdenes vía Selenium (aún NO conectado)
    │   └── bnc_scraper.py      # Saldo del banco BNC (opcional, desactivado)
    ├── news/
    │   └── news_fetcher.py     # RSS/Atom + sentimiento
    └── storage/
        └── history.py          # Histórico de mercado en SQLite
```

---

## 🚧 Estado y pendientes

**Implementado**: saldos, cartera con P&L, cotizaciones (con caché offline), órdenes, noticias con
sentimiento, motor de consejos **con o sin saldo**, histórico SQLite, backtesting con ajuste de
pesos, logging rotativo, CLI no interactiva, sesión persistente y 72 tests de validación.

**Pendiente — Bloque C (ejecución real de órdenes)**:

1. Conectar `src/client/selenium_trader.py` (ya implementado, 827 líneas) a la opción 2.
2. Salvaguardas antes de activarlo: `--dry-run` por defecto, confirmación escribiendo el símbolo,
   límite de VES por orden y % del saldo, lista blanca de símbolos, anti-duplicados e idempotencia.
3. Registrar cada ejecución en `data/bot.log` (auditoría).

**Mejoras futuras sugeridas**: tests de integración HTTP con respuestas grabadas, CI
(GitHub Actions) ejecutando `validate_bot.py`, aviso de *"datos post-cierre"* fuera del horario de
rueda, y reemplazar la base de dividendos estática por datos reales del sitio de la BVC.

---

<p align="center"><em>Bot Mercosur Casa de Bolsa · BVC — Documentación del proyecto.</em></p>






