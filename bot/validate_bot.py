"""Validación automática del bot (offline, sin credenciales ni red).

Ejecutar desde bot/:
    .venv\\Scripts\\python.exe -m unittest validate_bot -v
    .venv\\Scripts\\python.exe validate_bot.py

Verifica: configuración tipada, motor de IA (con y sin saldo), exclusión de
símbolos, sentimiento de noticias, parsing de RSS/Atom, ayudantes del cliente
y la existencia de la opción 5 en el menú.
"""
import base64
import json
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from src import config, ui
from src.ai.backtest import (
    backtest_scoring,
    format_backtest_report,
    format_weights_report,
    grid_search_weights,
)
from src.ai.investment_advisor import InvestmentAIAdvisor, InvestmentAdvisor
from src.client.mercosur_client import MercosurClient
from src.news.news_fetcher import NewsFetcher, _clean_text
from src.storage.history import MarketHistory

QUOTES_FILE = Path(__file__).resolve().parent / "data" / "cotizaciones.json"

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
            legacy = Path(tmp) / "quotes_latest.json"
            original = module.QUOTES_FILE
            original_latest = module.QUOTES_LATEST_FILE
            module.QUOTES_FILE = target
            module.QUOTES_LATEST_FILE = legacy
            try:
                MercosurClient._save_quotes_backup([{"symbol": "BNC", "last_price": 239.0}])
            finally:
                module.QUOTES_FILE = original
                module.QUOTES_LATEST_FILE = original_latest
            self.assertTrue(target.exists())
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["symbol"], "BNC")
            # El archivo legacy ya no debe escribirse (evita ruido en git)
            self.assertFalse(legacy.exists())


class TestUiAndMenu(unittest.TestCase):
    def test_menu_includes_option_5(self):
        import inspect
        source = inspect.getsource(ui.show_main_menu)
        self.assertIn('"5"', source)
        self.assertIn("Consejos", source)

    def test_ui_helpers_exist(self):
        for name in ("display_instruments", "display_orders", "print_mercosur_balances",
                     "display_best_investment", "display_report", "display_ranking",
                     "print_news_summary", "save_report", "print_ai_engine_info",
                     "print_quotes_source", "display_portfolio", "display_history_summary",
                     "set_no_color"):
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
                     "option_orders", "option_advice", "option_backtest", "main",
                     "build_parser", "run_cli"):
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


class TestSessionPersistence(unittest.TestCase):
    """A1: la sesión JWT se guarda, se reutiliza y no se expone en pantalla."""

    def setUp(self):
        import tempfile
        from src.client import mercosur_client as module
        self.module = module
        self.tmp = tempfile.TemporaryDirectory()
        self.original_token_file = module.TOKEN_FILE
        module.TOKEN_FILE = Path(self.tmp.name) / "session_token.json"

    def tearDown(self):
        self.module.TOKEN_FILE = self.original_token_file
        self.tmp.cleanup()

    @staticmethod
    def _jwt(payload):
        def encode(data):
            raw = json.dumps(data).encode()
            return base64.urlsafe_b64encode(raw).decode().rstrip("=")
        return f"{encode({'alg': 'HS256'})}.{encode(payload)}.firma"

    def test_expired_detection_with_exp(self):
        self.assertFalse(MercosurClient._token_expired(self._jwt({"exp": time.time() + 3600})))
        self.assertTrue(MercosurClient._token_expired(self._jwt({"exp": time.time() - 10})))
        self.assertTrue(MercosurClient._token_expired(None))
        self.assertTrue(MercosurClient._token_expired("no-es-un-jwt"))

    def test_ttl_used_when_jwt_has_no_exp(self):
        token = self._jwt({"sub": "cliente"})
        recent = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        old = (datetime.now() - timedelta(hours=99)).isoformat(timespec="seconds")
        self.assertFalse(MercosurClient._token_expired(token, recent))
        self.assertTrue(MercosurClient._token_expired(token, old))

    def test_save_and_reuse_session(self):
        client = MercosurClient()
        client.token = self._jwt({"exp": time.time() + 3600})
        client.user_data = {"nombre": "Cliente Test"}
        client._save_session()
        self.assertTrue(self.module.TOKEN_FILE.exists())

        other = MercosurClient()
        self.assertTrue(other._load_cached_session())
        self.assertTrue(other.session_reused)
        self.assertEqual(other.token, client.token)
        self.assertEqual(other.headers.get("Authorization"), f"Bearer {client.token}")

    def test_expired_token_is_discarded(self):
        client = MercosurClient()
        client.token = self._jwt({"exp": time.time() - 10})
        client._save_session()
        other = MercosurClient()
        self.assertFalse(other._load_cached_session())
        self.assertFalse(self.module.TOKEN_FILE.exists())

    def test_clear_session_removes_file(self):
        client = MercosurClient()
        client.token = self._jwt({"exp": time.time() + 3600})
        client._save_session()
        client.clear_session()
        self.assertFalse(self.module.TOKEN_FILE.exists())
        self.assertIsNone(client.token)
        self.assertNotIn("Authorization", client.headers)

    def test_auth_message_does_not_expose_token(self):
        import inspect
        source = inspect.getsource(ui.print_auth_success)
        self.assertNotIn("token[", source)
        self.assertNotIn("{token", source)
        self.assertNotIn("token", inspect.signature(ui.print_auth_success).parameters)


class TestOfflineQuotesFallback(unittest.TestCase):
    """A2: si la API falla, se usan las cotizaciones guardadas localmente."""

    def setUp(self):
        import tempfile
        from src.client import mercosur_client as module
        self.module = module
        self.tmp = tempfile.TemporaryDirectory()
        self.original_file = module.QUOTES_FILE
        self.original_latest = module.QUOTES_LATEST_FILE
        module.QUOTES_FILE = Path(self.tmp.name) / "cotizaciones.json"
        module.QUOTES_LATEST_FILE = Path(self.tmp.name) / "quotes_latest.json"
        self.original_live = MercosurClient._fetch_quotes_live
        MercosurClient._fetch_quotes_live = lambda self: []  # simula API caída

    def tearDown(self):
        MercosurClient._fetch_quotes_live = self.original_live
        self.module.QUOTES_FILE = self.original_file
        self.module.QUOTES_LATEST_FILE = self.original_latest
        self.tmp.cleanup()

    def test_cache_used_when_api_fails(self):
        self.module.QUOTES_FILE.write_text(
            json.dumps([{"symbol": "BNC", "last_price": 239.0}]), encoding="utf-8"
        )
        client = MercosurClient()
        quotes = client.fetch_quotes()
        self.assertEqual(len(quotes), 1)
        self.assertEqual(client.last_quotes_source, "cache")
        self.assertGreaterEqual(client.last_quotes_age_hours, 0.0)

    def test_empty_when_no_cache(self):
        client = MercosurClient()
        self.assertEqual(client.fetch_quotes(), [])
        self.assertEqual(client.last_quotes_source, "none")

    def test_cache_can_be_disabled(self):
        self.module.QUOTES_FILE.write_text(
            json.dumps([{"symbol": "BNC", "last_price": 239.0}]), encoding="utf-8"
        )
        client = MercosurClient()
        self.assertEqual(client.fetch_quotes(allow_cache=False), [])
        self.assertEqual(client.last_quotes_source, "none")

    def test_live_data_is_stored_for_offline_use(self):
        MercosurClient._fetch_quotes_live = lambda self: [{"symbol": "BNC", "last_price": 239.0}]
        client = MercosurClient()
        quotes = client.fetch_quotes()
        self.assertEqual(client.last_quotes_source, "live")
        self.assertEqual(len(quotes), 1)
        self.assertTrue(self.module.QUOTES_FILE.exists())
        saved = json.loads(self.module.QUOTES_FILE.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["symbol"], "BNC")


class TestMarketHistory(unittest.TestCase):
    """B7: histórico SQLite (snapshots, tendencia, volatilidad, upsert idempotente)."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.history = MarketHistory(db_path=Path(self.tmp.name) / "hist.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_read_snapshot(self):
        summary = self.history.save_snapshot(FALLBACK_QUOTES)
        self.assertGreater(summary["instruments"], 0)
        self.assertTrue(self.history.has_data())
        self.assertEqual(self.history.available_ruedas(), [summary["rueda"]])
        self.assertEqual(len(self.history.market_snapshot(summary["rueda"])), len(FALLBACK_QUOTES))

    def test_same_rueda_is_upserted_not_duplicated(self):
        self.history.save_snapshot(FALLBACK_QUOTES)
        self.history.save_snapshot(FALLBACK_QUOTES)
        self.assertEqual(len(self.history.available_ruedas()), 1)
        self.assertEqual(len(self.history.market_snapshot(self.history.available_ruedas()[0])),
                         len(FALLBACK_QUOTES))

    def test_trend_volatility_and_momentum(self):
        days = [datetime(2026, 1, 1), datetime(2026, 1, 2), datetime(2026, 1, 3)]
        for day, price in zip(days, (100.0, 110.0, 121.0)):
            self.history.save_snapshot(
                [{"symbol": "BNC", "last_price": price, "var_pct": 10.0, "cash_amount": 1000}], when=day
            )
        stats = self.history.get_symbol_stats("BNC")
        self.assertEqual(stats["samples"], 3)
        self.assertAlmostEqual(stats["trend_pct"], 21.0, places=1)
        self.assertAlmostEqual(stats["momentum_pct"], 10.0, places=1)
        self.assertEqual(stats["volatility"], 0.0)
        self.assertEqual(len(stats["lines"]), 3)

    def test_stats_without_history(self):
        stats = self.history.get_symbol_stats("NOEXISTE")
        self.assertEqual(stats["samples"], 0)
        self.assertEqual(stats["trend_pct"], 0.0)
        self.assertEqual(stats["lines"], [])

    def test_invalid_rows_are_ignored(self):
        summary = self.history.save_snapshot([{"symbol": "X", "last_price": "N/A"}, "basura", None, {}])
        self.assertEqual(summary["instruments"], 0)

    def test_summary_reports_range(self):
        self.history.save_snapshot(FALLBACK_QUOTES, when=datetime(2026, 2, 1))
        info = self.history.summary()
        self.assertEqual(info["ruedas"], 1)
        self.assertEqual(info["from"], "2026-02-01")
        self.assertGreater(info["symbols"], 0)


class TestBacktesting(unittest.TestCase):
    """B8: backtesting del motor y ajuste de pesos con datos."""

    SYMBOLS = ["BNC", "BPV", "MVZ.A", "RST"]

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.history = MarketHistory(db_path=Path(self.tmp.name) / "bt.db")
        for index in range(6):
            day = datetime(2026, 1, 1) + timedelta(days=index)
            rows = []
            for position, symbol in enumerate(self.SYMBOLS):
                price = 100.0 * (1 + 0.05 * index) if symbol == "BNC" else 100.0 + position
                rows.append({
                    "symbol": symbol,
                    "last_price": price,
                    "var_pct": 5.0 if symbol == "BNC" else 0.0,
                    "cash_amount": 2_000_000 if symbol == "BNC" else 10_000,
                })
            self.history.save_snapshot(rows, when=day)

    def tearDown(self):
        self.tmp.cleanup()

    def test_backtest_detects_the_winning_pick(self):
        result = backtest_scoring(self.history, horizon=3, top_n=1)
        self.assertGreater(result["runs"], 0)
        self.assertGreater(result["edge"], 0)
        self.assertEqual(result["hit_rate"], 100.0)
        self.assertEqual(result["evaluations"][0]["picks"], ["BNC"])

    def test_backtest_report_renders(self):
        report = format_backtest_report(backtest_scoring(self.history, horizon=3, top_n=1))
        self.assertIn("Backtesting", report)
        self.assertIn("Ventaja del motor", report)
        self.assertIn("Detalle por rueda", report)

    def test_backtest_without_history_is_safe(self):
        empty = MarketHistory(db_path=Path(self.tmp.name) / "vacio.db")
        result = backtest_scoring(empty)
        self.assertEqual(result["runs"], 0)
        self.assertIn("Se necesitan más de", format_backtest_report(result))

    def test_grid_search_returns_candidates(self):
        grid = grid_search_weights(self.history, horizon=3, top_n=1)
        self.assertTrue(grid["candidates"])
        self.assertIsNotNone(grid["best"])
        report = format_weights_report(grid)
        self.assertIn("liquidez", report)
        self.assertIn("Combinaciones probadas", report)

    def test_score_formula_is_shared_with_the_advisor(self):
        score = InvestmentAIAdvisor.score_value(liquidity_share=10.0, var_pct=2.0, pays_dividends=True)
        self.assertAlmostEqual(score, 10 * 0.5 + 2 * 0.3 + 20.0, places=6)


class TestPortfolio(unittest.TestCase):
    """B9: parseo de posiciones (varios formatos) y cálculo de P&L."""

    def test_parse_positions_computes_pnl(self):
        payload = {"posiciones": [
            {"cod_simb": "BNC", "cantidad_disponible": 10, "precio_promedio": 200.0, "precio_ultimo": 239.0},
        ]}
        positions = MercosurClient._parse_positions(payload)
        self.assertEqual(len(positions), 1)
        item = positions[0]
        self.assertEqual(item["symbol"], "BNC")
        self.assertEqual(item["quantity"], 10.0)
        self.assertEqual(item["cost"], 2000.0)
        self.assertEqual(item["market_value"], 2390.0)
        self.assertAlmostEqual(item["pnl"], 390.0, places=2)
        self.assertAlmostEqual(item["pnl_pct"], 19.5, places=2)

    def test_parse_positions_accepts_alternative_names(self):
        positions = MercosurClient._parse_positions([
            {"simbolo": "bpv", "tenencia": "5,0", "costo_promedio": "75,5", "valor_actual": "400"},
        ])
        self.assertEqual(positions[0]["symbol"], "BPV")
        self.assertEqual(positions[0]["quantity"], 5.0)
        self.assertEqual(positions[0]["avg_price"], 75.5)
        self.assertEqual(positions[0]["market_value"], 400.0)

    def test_parse_positions_ignores_invalid_entries(self):
        self.assertEqual(MercosurClient._parse_positions([{"symbol": "X", "cantidad": 0}, "basura", {}]), [])
        self.assertEqual(MercosurClient._parse_positions(None), [])

    def test_enrich_positions_recalculates_market_value(self):
        positions = MercosurClient._parse_positions([
            {"cod_simb": "BNC", "cantidad": 10, "precio_promedio": 200.0, "precio_ultimo": 200.0},
        ])
        enriched = MercosurClient.enrich_positions(positions, [{"symbol": "BNC", "last_price": 250.0}])
        self.assertEqual(enriched[0]["market_price"], 250.0)
        self.assertEqual(enriched[0]["market_value"], 2500.0)
        self.assertEqual(enriched[0]["pnl"], 500.0)
        self.assertEqual(enriched[0]["pnl_pct"], 25.0)

    def test_advisor_report_includes_real_portfolio(self):
        advisor = InvestmentAIAdvisor(use_ollama=False)
        positions = MercosurClient._parse_positions([
            {"cod_simb": "BNC", "cantidad": 10, "precio_promedio": 200.0, "precio_ultimo": 239.0},
        ])
        result = advisor.recommend_best_investment(FALLBACK_QUOTES, positions=positions, balance=1000.0)
        self.assertIn("Tu cartera real", result["report"])
        self.assertIn("BNC", result["report"])
        self.assertIn("Resultado", result["report"])


class TestAdvisorWithHistory(unittest.TestCase):
    """B7 integrado: el histórico cambia el puntaje y el informe del advisor."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.history = MarketHistory(db_path=Path(self.tmp.name) / "adv.db")
        for index, price in enumerate((100.0, 120.0, 150.0)):
            self.history.save_snapshot(
                [{"symbol": "BNC", "last_price": price, "var_pct": 10.0, "cash_amount": 1000}],
                when=datetime(2026, 1, 1) + timedelta(days=index),
            )
        self.advisor = InvestmentAIAdvisor(use_ollama=False)
        self.quotes = [{"symbol": "BNC", "description": "BANCO NACIONAL DE CREDITO",
                        "last_price": 150.0, "var_pct": 0.0, "cash_amount": 1000}]

    def tearDown(self):
        self.tmp.cleanup()

    def test_history_enriches_ranking_and_score(self):
        without = self.advisor.rank_companies(self.quotes, history=None)
        with_history = self.advisor.rank_companies(self.quotes, history=self.history)
        self.assertEqual(without["ranking"][0]["history_samples"], 0)
        self.assertFalse(without["history_used"])
        self.assertEqual(with_history["ranking"][0]["history_samples"], 3)
        self.assertTrue(with_history["history_used"])
        self.assertGreater(with_history["ranking"][0]["trend_pct"], 0)
        self.assertGreater(with_history["ranking"][0]["score"], without["ranking"][0]["score"])

    def test_report_mentions_trend_section(self):
        result = self.advisor.recommend_best_investment(self.quotes, history=self.history, balance=None)
        self.assertIn("Tendencia histórica", result["report"])

    def test_report_without_history_and_portfolio_says_so(self):
        result = self.advisor.recommend_best_investment(self.quotes, balance=None)
        self.assertIn("Sin posiciones disponibles", result["report"])
        self.assertIn("no hay histórico", result["report"].lower())


class TestCliAndLogging(unittest.TestCase):
    """A5/A6: logging a archivo rotativo y CLI no interactiva."""

    def test_parser_defaults(self):
        import main as main_module
        args = main_module.build_parser().parse_args([])
        self.assertIsNone(args.option)
        self.assertEqual(args.top, 5)
        self.assertFalse(args.advice)
        self.assertIsNone(args.budget)
        self.assertFalse(args.no_history)

    def test_parser_flags_and_global_apply(self):
        import main as main_module
        args = main_module.build_parser().parse_args(
            ["--advice", "--top", "3", "--budget", "1500", "--no-history", "--no-color", "--quiet"]
        )
        self.assertTrue(args.advice)
        self.assertEqual(args.top, 3)
        self.assertEqual(args.budget, 1500.0)

        main_module._apply_args(args)
        try:
            self.assertEqual(main_module._top_n, 3)
            self.assertEqual(main_module._budget_override, 1500.0)
            self.assertFalse(main_module._use_history)
        finally:
            main_module._apply_args(main_module.build_parser().parse_args([]))
        self.assertEqual(main_module._top_n, 5)
        self.assertIsNone(main_module._budget_override)

    def test_resolve_action_mapping(self):
        import main as main_module
        parser = main_module.build_parser()
        self.assertEqual(main_module._resolve_action(parser.parse_args(["--advice"])), "5")
        self.assertEqual(main_module._resolve_action(parser.parse_args(["--analysis"])), "2")
        self.assertEqual(main_module._resolve_action(parser.parse_args(["--portfolio"])), "1")
        self.assertEqual(main_module._resolve_action(parser.parse_args(["--backtest"])), "backtest")
        self.assertEqual(main_module._resolve_action(parser.parse_args(["--option", "3"])), "3")
        self.assertIsNone(main_module._resolve_action(parser.parse_args([])))

    def test_budget_override_is_used(self):
        import main as main_module
        main_module._apply_args(main_module.build_parser().parse_args(["--budget", "2500"]))
        try:
            self.assertEqual(main_module._budget_override, 2500.0)
        finally:
            main_module._apply_args(main_module.build_parser().parse_args([]))
        self.assertIsNone(main_module._budget_override)

    def test_setup_logging_writes_to_file(self):
        import logging
        import tempfile
        from src import logging_setup
        root = logging.getLogger()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bot.log"
            original_file = logging_setup.LOG_FILE
            logging_setup.LOG_FILE = target
            logging_setup._configured = False
            for handler in list(root.handlers):
                root.removeHandler(handler)
            try:
                logging_setup.setup_logging(quiet=True)
                logging.getLogger("validacion").info("mensaje de prueba")
                for handler in list(root.handlers):
                    handler.flush()
                self.assertTrue(target.exists())
                content = target.read_text(encoding="utf-8")
            finally:
                for handler in list(root.handlers):
                    handler.close()
                    root.removeHandler(handler)
                logging_setup.LOG_FILE = original_file
                logging_setup._configured = False
            self.assertIn("mensaje de prueba", content)







if __name__ == "__main__":
    unittest.main(verbosity=2)



