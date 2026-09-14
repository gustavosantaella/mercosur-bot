# 📈 Mercosur & BVC Stock Intelligence & Local AI Investment Advisor

Sistema profesional modular en Python para:
1. Autenticación JWT y extracción automatizada de cotizaciones de la **Bolsa de Valores de Caracas** desde el endpoint oficial de **Mercosur Casa de Bolsa** (`cm.mercosur.com.ve`).
2. Scraping y agregación de noticias económicas y financieras de Venezuela en tiempo real.
3. Evaluación de oportunidades de inversión y análisis bursátil con **Inteligencia Artificial 100% Local** (Ollama + Motor Cuantitativo Local NLP Offline).

---

## 📂 Estructura Profesional del Proyecto

```text
mercosur/
├── .env                       # Variables de entorno activas
├── .env.example               # Plantilla de configuración
├── README.md                  # Documentación del proyecto
├── requirements.txt           # Dependencias de Python
├── main.py                    # Punto de entrada principal (CLI)
├── data/                      # Salidas generadas
│   ├── cotizaciones.json      # Cotizaciones en tiempo real
│   └── informe_inversion.md   # Reporte de análisis de inversión
└── src/                       # Código fuente modular
    ├── __init__.py
    ├── config.py              # Configuración global y rutas
    ├── client/                # Módulo de integración API Mercosur
    │   ├── __init__.py
    │   └── mercosur_client.py
    ├── news/                  # Módulo de noticias económicas
    │   ├── __init__.py
    │   └── news_fetcher.py
    └── ai/                    # Módulo de Inteligencia Artificial Local
        ├── __init__.py
        └── investment_advisor.py
```

---

## 🚀 Ejecución y Configuración

Puedes activar o desactivar el uso de IA mediante la variable `USE_AI` en tu archivo `.env`:
- `USE_AI=1`: Habilita la recopilación de noticias y el análisis bursátil con IA.
- `USE_AI=0`: Realiza únicamente la autenticación en Mercosur, descarga las cotizaciones y guarda `data/cotizaciones.json` sin llamar a la IA.

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar el proyecto
```bash
python main.py
```

---

## 📄 Salidas Generadas en `data/`
- **[`data/cotizaciones.json`](file:///c:/Users/llxsa/projects/mercosur/data/cotizaciones.json)**: JSON con todas las cotizaciones de la rueda en tiempo real.
- **[`data/informe_inversion.md`](file:///c:/Users/llxsa/projects/mercosur/data/informe_inversion.md)**: Informe ejecutivo con análisis de sentimiento, empresas recomendadas y estrategia.
