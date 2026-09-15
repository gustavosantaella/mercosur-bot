"""Validación automática del bot (offline, sin credenciales ni red).

Ejecutar desde bot/:
    .venv\\Scripts\\python.exe -m unittest validate_bot -v
    .venv\\Scripts\\python.exe validate_bot.py

Verifica: configuración tipada, motor de IA (con y sin saldo), exclusión de
símbolos, sentimiento de noticias, parsing de RSS/Atom, ayudantes del cliente
y la existencia de la opción 5 en el menú.
"""
import json
import unittest
from pathlib import Path

from src import config, ui
from src.ai.investment_advisor import InvestmentAIAdvisor, InvestmentAdvisor
from src.client.mercosur_client import MercosurClient
from src.news.news_fetcher import NewsFetcher, _clean_text

QUOTES_FILE = Path(__file__).resolve().parent / "quotes_latest.json"

FALLBACK_QUOTES = [
    {"symbol": "BNC", "description": "BANCO NACIONAL DE CREDITO", "last_price": 239.0,
     "var_pct": 1.7, "cash_amount": 1998667.65, "dividends": "N/A"},
    {"symbol": "BPV", "description": "BANCO PROVINCIAL, S.A.", "last_price": 75.0,
     "var_pct": 4.17, "cash_amount": 2178933.7, "dividends": "N/A"},
    {"symbol": "MVZ.A", "description": "MERCANTIL SERV. FINANCIEROS CLS.(A)", "last_price": 8000.0,
     "var_pct": 1.27, "cash_amount": 173370.02, "dividends": "N/A"},
    {"symbol": "BVL", "description": "BANCO DE VENEZUELA", "last_price": 1800.0,
     "var_pct": 3.15, "cash_amount": 704752.0, "dividends": "N/A"},
]

RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
  <item><title>BVC cierra con crecimiento y ganancias</title>
    <link>https://example.com/1</link><pubDate>Mon, 01 Jan 2026</pubDate>
    <description><![CDATA[<p>El mercado reporta <b>alza</b> general</p>]]></description></item>
  <item><title>Riesgo por inflaci&oacute;n y ca&iacute;da de la producci&oacute;n</title>
    <link>https://example.com/2</link><pubDate>Tue, 02 Jan 2026</pubDate>
    <description>Sin detalle</description></item>
</channel></rss>"""

ATOM_SAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test</title>
  <entry><title>Dividendos aprobados en Asamblea</title>
    <link href="https://example.com/atom1"/>
    <updated>2026-01-03T10:00:00Z</updated>
    <summary>Banco Provincial anuncia dividendo</summary></entry>
</feed>"""


def _load_quotes():
    if QUOTES_FILE.exists():
        with open(QUOTES_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list) and data:
            return data
    return FALLBACK_QUOTES


class TestConfig(unittest.TestCase):
    def test_flags_are_real_booleans(self):
        """Los flags deben ser bool reales ('0' NO puede evaluar como True)."""
        for name in ("USE_AI", "AUTO_EXECUTE_ORDERS", "FETCH_BNC_BALANCE", "BNC_HEADLESS"):
            self.assertIsInstance(getattr(config, name), bool, f"{name} no es bool")

    def test_typed_values(self):
        self.assertIsInstance(config.HTTP_TIMEOUT, int)
        self.assertGreater(config.HTTP_TIMEOUT, 0)
        self.assertIsInstance(config.EXCLUDE_SYMBOLS, list)
        self.assertTrue(all(sym == sym.upper() for sym in config.EXCLUDE_SYMBOLS))

    def test_news_feeds_are_structured(self):
        self.assertIsInstance(config.NEWS_FEEDS, list)
        self.assertTrue(config.NEWS_FEEDS)
        for feed in config.NEWS_FEEDS:
            self.assertIsInstance(feed, dict)
            self.assertTrue(str(feed.get("url", "")).startswith("http"))

    def test_paths_are_absolute(self):
        self.assertTrue(config.DATA_DIR.is_absolute())
        self.assertTrue(config.REPORT_FILE.is_absolute())
        self.assertTrue(config.DATA_DIR.exists())

    def test_no_dead_duplicate_config_module(self):
        """El paquete src/config debe ser el que resuelve el import (no quedar sombreado)."""
        self.assertIn("config", str(config.__file__).replace("\\", "/"))
        self.assertTrue(str(config.__file__).replace("\\", "/").endswith("src/config/__init__.py"))


class TestAdvisorAlwaysGivesAdvice(unittest.TestCase):
    """Requisito central: SIEMPRE hay consejo, incluso sin saldo."""

    def setUp(self):
        self.quotes = _load_quotes()
        self.advisor = InvestmentAIAdvisor(use_ollama=False)

    def test_best_investment_without_balance(self):
        result = self.advisor.recommend_best_investment(self.quotes, news=[], balance=None)
        self.assertTrue(result["ranking"], "Debe haber ranking aunque no haya saldo")
        self.assertFalse(result["balance_available"])
        self.assertIsNotNone(result["best"])
        self.assertIn("Mejor opción", result["report"])
        self.assertIn("presupuestos de referencia", result["report"])

    def test_best_investment_with_zero_balance(self):
        result = self.advisor.recommend_best_investment(self.quotes, balance=0.0)
        self.assertTrue(result["ranking"])
        self.assertFalse(result["balance_available"])
        self.assertIn("Mejor opción", result["report"])

    def test_best_investment_with_balance(self):
        result = self.advisor.recommend_best_investment(self.quotes, balance=50000.0)
        self.assertTrue(result["balance_available"])
        self.assertIn("saldo actual", result["report"])

    def test_full_analysis_without_balance(self):
        report = self.advisor.analyze_investments(companies=self.quotes, news=[], mercosur_balance=None)
        self.assertIn("Mejor empresa para invertir", report)
        self.assertIn("Oportunidades de COMPRA", report)
        self.assertIn("No disponible", report)

    def test_top_pick_is_the_highest_score(self):
        result = self.advisor.recommend_best_investment(self.quotes, balance=None)
        scores = [item["score"] for item in result["ranking"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(result["best"]["score"], max(scores))

    def test_excluded_symbols_are_not_recommended(self):
        result = self.advisor.recommend_best_investment(self.quotes, balance=None)
        symbols = {item["symbol"] for item in result["ranking"]}
        for excluded in config.EXCLUDE_SYMBOLS:
            self.assertNotIn(excluded, symbols, f"{excluded} debería estar excluido")
        self.assertGreaterEqual(result["analyzed"], 1)

    def test_handles_dirty_data_without_crashing(self):
        dirty = [
            {"symbol": "XX", "description": "Precio inválido", "last_price": "N/A", "var_pct": None},
            {"symbol": "YY", "description": "Precio local", "last_price": "1.234,56", "var_pct": "2,5"},
            {"symbol": "ZZ", "description": "Dividendos JSON", "last_price": 100, "var_pct": 1,
             "cash_amount": 5000, "dividends": '{"pays_dividends": "Yes"}'},
            "texto suelto", None, {},
        ]
        result = self.advisor.recommend_best_investment(dirty, balance=None)
        symbols = {item["symbol"] for item in result["ranking"]}
        self.assertIn("YY", symbols)
        self.assertIn("ZZ", symbols)
        self.assertNotIn("XX", symbols)
        zz_pays = next(item for item in result["ranking"] if item["symbol"] == "ZZ")["dividends"]["pays"]
        self.assertTrue(zz_pays, "El dividendo declarado en JSON debe detectarse")

    def test_empty_market_does_not_crash(self):
        report = self.advisor.analyze_investments(companies=[], news=[], mercosur_balance=None)
        self.assertIn("Sin datos suficientes", report)
        result = self.advisor.recommend_best_investment(None, balance=None)
        self.assertIsNone(result["best"])
        self.assertIn("Sin datos suficientes", result["report"])

    def test_recommended_orders_respects_balance(self):
        self.assertEqual(self.advisor.get_recommended_orders(self.quotes, 0.0), [])
        orders = self.advisor.get_recommended_orders(self.quotes, 100000.0)
        if orders:
            self.assertEqual(orders[0]["order_type"], "COMPRA")
            self.assertGreater(orders[0]["quantity"], 0)

    def test_alias_class_available(self):
        self.assertIs(InvestmentAdvisor, InvestmentAIAdvisor)


class TestNewsFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = NewsFetcher(feeds=[])

    def test_parse_rss(self):
        news = self.fetcher._parse_feed(RSS_SAMPLE, "Test", 5)
        self.assertEqual(len(news), 2)
        self.assertEqual(news[0]["title"], "BVC cierra con crecimiento y ganancias")
        self.assertEqual(news[0]["link"], "https://example.com/1")
        self.assertEqual(news[0]["source"], "Test")
        self.assertNotIn("<p>", news[0]["summary"])
        self.assertIn("alza", news[0]["summary"])

    def test_parse_atom(self):
        news = self.fetcher._parse_feed(ATOM_SAMPLE, "AtomSrc", 5)
        self.assertEqual(len(news), 1)
        self.assertEqual(news[0]["link"], "https://example.com/atom1")
        self.assertEqual(news[0]["pub_date"], "2026-01-03T10:00:00Z")

    def test_parse_limits_and_bad_xml(self):
        self.assertEqual(len(self.fetcher._parse_feed(RSS_SAMPLE, "T", 1)), 1)
        self.assertEqual(self.fetcher._parse_feed(b"<no-xml", "T", 5), [])

    def test_clean_text(self):
        self.assertEqual(_clean_text("<p>Hola&nbsp;  mundo</p>"), "Hola mundo")
        self.assertEqual(_clean_text(None), "")

    def test_normalize_feeds_accepts_several_formats(self):
        feeds = NewsFetcher._normalize_feeds([
            {"name": "A", "url": "https://a.test/feed"},
            ("B", "https://b.test/feed"),
            "https://c.test/feed",
            {"name": "sin-url", "url": ""},
        ])
        self.assertEqual(len(feeds), 3)

    def test_fetch_without_feeds_returns_empty_list(self):
        """Sin fuentes configuradas no se descarga nada y no se lanza excepción."""
        self.assertEqual(NewsFetcher(feeds=[]).fetch_latest_news(), [])

    def test_no_internet_returns_empty_list(self):
        """Sin internet el fetcher degrada a lista vacía (no lanza excepción)."""
        from src.news import news_fetcher as module
        original = module._has_internet
        module._has_internet = lambda: False
        try:
            self.assertEqual(NewsFetcher().fetch_latest_news(), [])
        finally:
            module._has_internet = original

    def test_sanitize_html_entities(self):
        """Entidades HTML no declaradas no deben romper el parseo XML (bug corregido)."""
        from src.news.news_fetcher import _sanitize_entities
        parsed = self.fetcher._parse_feed(
            b'<?xml version="1.0"?><rss><channel><item>'
            b'<title>Producci&oacute;n y econom&iacute;a &amp; m&aacute;s</title>'
            b'<link>https://x.test</link></item></channel></rss>',
            "Entidades", 5,
        )
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], "Producción y economía & más")
        self.assertIn("&amp;", _sanitize_entities("A &amp; B"))

    def test_sentiment_detection(self):
        advisor = InvestmentAIAdvisor(use_ollama=False)
        positive = advisor._news_sentiment([{"title": "Crecimiento y ganancias récord"}])
        negative = advisor._news_sentiment([{"title": "Crisis, inflación y caída"}])
        self.assertEqual(positive["label"], "positivo")
        self.assertGreater(positive["score"], 0)
        self.assertEqual(negative["label"], "negativo")
        self.assertLess(negative["score"], 0)
        self.assertEqual(advisor._news_sentiment([])["label"], "neutro")

    def test_news_mentions_affect_score(self):
        advisor = InvestmentAIAdvisor(use_ollama=False)
        quotes = [{"symbol": "BNC", "description": "BANCO NACIONAL DE CREDITO",
                   "last_price": 239.0, "var_pct": 1.0, "cash_amount": 100000}]
        with_news = advisor.rank_companies(quotes, [{"title": "BNC reporta crecimiento"}])["ranking"][0]["score"]
        without_news = advisor.rank_companies(quotes, [])["ranking"][0]["score"]
        self.assertGreater(with_news, without_news)


class TestClientHelpers(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(MercosurClient._to_float("1.234,56"), 1234.56)
        self.assertEqual(MercosurClient._to_float("12,5"), 12.5)
        self.assertEqual(MercosurClient._to_float(None), 0.0)
        self.assertEqual(MercosurClient._to_float("N/A"), 0.0)
        self.assertEqual(MercosurClient._to_float(""), 0.0)
        self.assertEqual(MercosurClient._to_float(7), 7.0)

    def test_pick(self):
        self.assertEqual(MercosurClient._pick({"a": None, "b": 3}, "a", "b"), 3)
        self.assertIsNone(MercosurClient._pick({}, "a"))

    def test_empty_balances_structure(self):
        empty = MercosurClient._empty_balances()
        for key in ("disponible", "available_balance", "ves_available", "total", "total_balance", "bloqueado"):
            self.assertIn(key, empty)
            self.assertEqual(empty[key], 0.0)

    def test_client_uses_config(self):
        client = MercosurClient()
        self.assertTrue(client.url_quotes.startswith("https://"))
        self.assertIn("cotizaciones", client.url_quotes)
        self.assertEqual(client.timeout, config.HTTP_TIMEOUT)
        self.assertEqual(client.exclude_symbols, set(config.EXCLUDE_SYMBOLS))

    def test_save_quotes_backup_writes_files(self):
        import tempfile
        from src.client import mercosur_client as module
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cotizaciones.json"
            original = module.QUOTES_FILE
            original_latest = module.QUOTES_LATEST_FILE
            module.QUOTES_FILE = target
            module.QUOTES_LATEST_FILE = Path(tmp) / "quotes_latest.json"
            try:
                MercosurClient._save_quotes_backup([{"symbol": "BNC", "last_price": 239.0}])
            finally:
                module.QUOTES_FILE = original
                module.QUOTES_LATEST_FILE = original_latest
            self.assertTrue(target.exists())
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["symbol"], "BNC")


class TestUiAndMenu(unittest.TestCase):
    def test_menu_includes_option_5(self):
        import inspect
        source = inspect.getsource(ui.show_main_menu)
        self.assertIn('"5"', source)
        self.assertIn("Consejos", source)

    def test_ui_helpers_exist(self):
        for name in ("display_instruments", "display_orders", "print_mercosur_balances",
                     "display_best_investment", "display_report", "display_ranking",
                     "print_news_summary", "save_report", "print_ai_engine_info"):
            self.assertTrue(callable(getattr(ui, name)), f"Falta ui.{name}")

    def test_balances_render_without_crash(self):
        ui.print_mercosur_balances(MercosurClient._empty_balances())
        ui.print_mercosur_balances(None)
        ui.print_mercosur_balances({"available_balance": "1.234,56"})

    def test_best_investment_renders_and_saves_report(self):
        advisor = InvestmentAIAdvisor(use_ollama=False)
        result = advisor.recommend_best_investment(_load_quotes(), balance=None)
        ui.display_best_investment(result)
        self.assertTrue(config.REPORT_FILE.exists())
        self.assertIn("Mejor opción", config.REPORT_FILE.read_text(encoding="utf-8"))


class TestMainWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main as main_module
        cls.main = main_module

    def test_option_functions_exist(self):
        for name in ("option_balances", "option_full_analysis", "option_instruments",
                     "option_orders", "option_advice", "main"):
            self.assertTrue(callable(getattr(self.main, name)), f"Falta main.{name}")

    def test_advice_option_uses_balance_instruments_and_news(self):
        import inspect
        source = inspect.getsource(self.main.option_advice)
        self.assertIn("_fetch_balance", source)
        self.assertIn("_fetch_quotes", source)
        self.assertIn("_fetch_news", source)
        self.assertIn("recommend_best_investment", source)

    def test_full_analysis_option_uses_news(self):
        import inspect
        source = inspect.getsource(self.main.option_full_analysis)
        self.assertIn("_fetch_news", source)
        self.assertIn("analyze_investments", source)

    def test_ai_flag_is_respected_for_news(self):
        import inspect
        source = inspect.getsource(self.main._fetch_news)
        self.assertIn("USE_AI", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)



