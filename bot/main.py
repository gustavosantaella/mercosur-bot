"""Punto de entrada del bot: menú interactivo + CLI.

Opciones interactivas:
  1) Saldos, cartera y estado de cuenta
  2) Inversión automática / análisis completo IA (compras, rotación, liquidez)
  3) Instrumentos en cotización
  4) Órdenes registradas
  5) Consejos: ¿en qué empresa es mejor invertir? (saldo + instrumentos + noticias)

Uso no interactivo (cron / Task Scheduler):
  python main.py --advice                  # consejo del día y salir
  python main.py --analysis --budget 5000  # análisis completo con saldo manual
  python main.py --backtest                # valida el motor con el histórico
  python main.py --tune-weights            # ajusta los pesos con datos reales
  python main.py --portfolio --no-color    # cartera y saldos sin colores
"""
import argparse
import logging
import sys

from src import ui
from src.ai.backtest import (
    backtest_scoring,
    format_backtest_report,
    format_weights_report,
    grid_search_weights,
)

from src.ai.investment_advisor import InvestmentAdvisor
from src.client.mercosur_client import MercosurClient
from src.config import AUTO_EXECUTE_ORDERS, HISTORY_ENABLED, USE_AI
from src.logging_setup import setup_logging
from src.news.news_fetcher import NewsFetcher
from src.storage.history import MarketHistory

logger = logging.getLogger(__name__)

client = MercosurClient()
advisor = InvestmentAdvisor()
news_fetcher = NewsFetcher()
market_history = MarketHistory() if HISTORY_ENABLED else None

# Ajustes que puede fijar la CLI
_budget_override = None
_top_n = 5
_use_history = True
_pause_enabled = True


# ─────────────────────────────────────────────────────────────────
# Helpers de flujo
# ─────────────────────────────────────────────────────────────────
def _pause(message="\nPresiona ENTER para volver al menú..."):
    if not _pause_enabled:
        return
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        pass


def _bootstrap(force_login=False):
    """Autentica (reutilizando sesión si es válida) e informa por consola."""
    if force_login:
        client.clear_session()
    try:
        client.login()
    except Exception as error:
        logger.warning("Fallo de autenticación: %s", error)
    ui.print_auth_success(reused_cache=client.session_reused, cliente_data=client.user_data)
    logger.info("Sesión iniciada (reutilizada=%s)", client.session_reused)


def _fetch_balance():
    """Devuelve (balances, saldo_disponible). El saldo es 0.0 si no se puede consultar."""
    balances = client.get_balances() or {}
    raw = balances.get(
        "available_balance",
        balances.get("disponible", balances.get("saldo_disponible", balances.get("ves_available", 0.0))),
    )
    try:
        balance = float(raw)
    except (TypeError, ValueError):
        balance = 0.0

    if _budget_override is not None:
        ui.console.print(f"[cyan]💡 Usando saldo manual indicado por CLI:[/cyan] "
                         f"{_budget_override:,.2f} VES")
        balance = float(_budget_override)
    return balances, balance


def _fetch_quotes():
    """Cotizaciones (en vivo o caché) y guarda el snapshot histórico de la rueda."""
    quotes = client.fetch_quotes() or []
    ui.print_quotes_source(client.last_quotes_source, client.last_quotes_age_hours)
    if not quotes:
        logger.warning("Sin cotizaciones disponibles")
        return []

    ui.console.print(f"[bold green]✔ Cotizaciones obtenidas:[/bold green] {len(quotes)} instrumentos.")
    if market_history is not None and client.last_quotes_source == "live":
        try:
            summary = market_history.save_snapshot(quotes)
            logger.info("Snapshot histórico guardado: %s", summary)
            ui.console.print(f"[dim]📚 Histórico actualizado (rueda {summary['rueda']}, "
                             f"{summary['instruments']} instrumentos).[/dim]")
        except Exception as error:
            logger.warning("No se pudo guardar el histórico: %s", error)
    return quotes


def _fetch_news():
    """Noticias financieras. Si USE_AI=0 se omite la recolección (según configuración)."""
    if not USE_AI:
        ui.print_ai_disabled()
        ui.console.print("[dim]ℹ️ El consejo se generará solo con saldo, instrumentos e histórico.[/dim]")
        return []
    news = news_fetcher.fetch_latest_news()
    ui.print_news_summary(news)
    logger.info("Noticias obtenidas: %s", len(news))
    return news


def _fetch_positions(quotes=None):
    """Posiciones de la cartera real ([] si el endpoint no está disponible)."""
    try:
        positions = client.fetch_portfolio(quotes=quotes)
    except Exception as error:
        logger.warning("No se pudo obtener la cartera: %s", error)
        positions = []
    if positions:
        logger.info("Cartera obtenida desde %s (%s posiciones)", client.portfolio_source, len(positions))
    return positions


def _active_history():
    """Histórico a usar en el análisis (None si está desactivado o vacío)."""
    if market_history is None or not _use_history:
        return None
    try:
        return market_history if market_history.has_data() else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# Opciones del menú
# ─────────────────────────────────────────────────────────────────
def option_balances():
    """1) Saldos, cartera y estado de cuenta."""
    ui.console.print("\n[bold yellow]💰 Consultando saldos, cartera y estado de cuenta...[/bold yellow]")
    balances = client.get_balances()
    ui.print_mercosur_balances(balances)
    positions = _fetch_positions()
    ui.display_portfolio(positions, source=client.portfolio_source)


def option_full_analysis():
    """2) Inversión automática / análisis completo con IA."""
    ui.console.print("\n[bold yellow]🚀 Analizando saldo, cartera, mercado y noticias...[/bold yellow]")

    balances, balance = _fetch_balance()
    ui.print_mercosur_balances(balances)

    quotes = _fetch_quotes()
    if not quotes:
        return

    positions = _fetch_positions(quotes)
    if positions:
        ui.display_portfolio(positions, source=client.portfolio_source)

    news = _fetch_news()

    ui.console.print("\n[bold yellow]🤖 Generando análisis completo (compras, rotación y liquidez)..."
                     "[/bold yellow]")
    report = advisor.analyze_investments(
        companies=quotes,
        news=news,
        mercosur_balance=balance if balance > 0 else None,
        top_n=_top_n,
        history=_active_history(),
        positions=positions,
    )
    ui.display_report(report, title="🧠 Análisis completo de inversión IA", save=True)

    ui.print_order_execution_mode(AUTO_EXECUTE_ORDERS)
    if AUTO_EXECUTE_ORDERS:
        ui.console.print(
            "[bold yellow]⚠️ La ejecución automática de órdenes no está habilitada en esta versión: "
            "no se envió ninguna orden real.[/bold yellow]"
        )
        recommendation = advisor.get_recommended_orders(quotes, mercosur_balance=balance)
        if recommendation:
            order = recommendation[0]
            ui.console.print(
                f"[cyan]📌 Orden sugerida:[/cyan] COMPRA de {order['quantity']:,} "
                f"{order['symbol']} @ {order['price']:,.2f} VES — ejecútala manualmente en Mercosur."
            )
        else:
            ui.console.print("[dim]ℹ️ Sin órdenes sugeridas para el saldo actual.[/dim]")


def option_instruments():
    """3) Instrumentos en cotización."""
    ui.console.print("\n[bold yellow]📈 Obteniendo instrumentos en tiempo real...[/bold yellow]")
    quotes = _fetch_quotes()
    ui.display_instruments(quotes)


def option_orders():
    """4) Órdenes registradas."""
    ui.console.print("\n[bold yellow]📋 Obteniendo tus órdenes registradas...[/bold yellow]")
    ui.display_orders(client.fetch_orders())


def option_advice():
    """5) Consejos: ¿en qué empresa es mejor invertir? (saldo + instrumentos + noticias)."""
    ui.console.print("\n[bold yellow]🎯 Consultando saldo, instrumentos y noticias para tu consejo..."
                     "[/bold yellow]")

    balances, balance = _fetch_balance()
    ui.print_mercosur_balances(balances)

    quotes = _fetch_quotes()
    if not quotes:
        return

    positions = _fetch_positions(quotes)
    news = _fetch_news()
    if market_history is not None:
        ui.display_history_summary(market_history.summary())

    ui.console.print("\n[bold yellow]🧠 Evaluando en qué empresa es mejor invertir...[/bold yellow]")
    result = advisor.recommend_best_investment(
        companies=quotes,
        news=news,
        balance=balance if balance > 0 else None,
        top_n=_top_n,
        history=_active_history(),
        positions=positions,
    )
    ui.display_best_investment(result)
    logger.info("Consejo generado: mejor=%s", result.get("best", {}).get("symbol") if result.get("best") else None)


def option_backtest(tune=False):
    """Valida el motor con el histórico guardado (y opcionalmente ajusta los pesos)."""
    if market_history is None:
        ui.console.print("[bold yellow]⚠️ Histórico desactivado (HISTORY_ENABLED=0).[/bold yellow]")
        return

    summary = market_history.summary()
    ui.display_history_summary(summary)
    if not summary.get("ruedas"):
        ui.console.print("[bold yellow]⚠️ Aún no hay ruedas guardadas. Ejecuta el bot a diario "
                         "para acumular histórico.[/bold yellow]")
        return

    ui.console.print("\n[bold yellow]🧪 Ejecutando backtesting del motor de puntaje...[/bold yellow]")
    result = backtest_scoring(market_history, top_n=_top_n)
    ui.display_report(format_backtest_report(result), title="🧪 Backtesting del motor", save=False)

    if tune:
        ui.console.print("\n[bold yellow]⚖️ Buscando los mejores pesos (grid-search)...[/bold yellow]")
        grid = grid_search_weights(market_history, top_n=_top_n)
        ui.display_report(format_weights_report(grid), title="⚖️ Ajuste de pesos sugerido", save=False)


OPTIONS = {
    "1": option_balances,
    "2": option_full_analysis,
    "3": option_instruments,
    "4": option_orders,
    "5": option_advice,
}


# ─────────────────────────────────────────────────────────────────
# CLI (modo no interactivo)
# ─────────────────────────────────────────────────────────────────
def build_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Mercosur Casa de Bolsa - bot de análisis e inversión (BVC).",
    )
    parser.add_argument("--option", choices=["1", "2", "3", "4", "5"],
                        help="Ejecuta una opción del menú y sale (1=saldos/cartera, 2=análisis, "
                             "3=instrumentos, 4=órdenes, 5=consejos).")
    parser.add_argument("--balance", action="store_true", help="Atajo de --option 1 (saldos y cartera).")
    parser.add_argument("--portfolio", action="store_true", help="Atajo de --option 1 (saldos y cartera).")
    parser.add_argument("--analysis", action="store_true", help="Atajo de --option 2 (análisis completo IA).")
    parser.add_argument("--instruments", action="store_true", help="Atajo de --option 3 (cotizaciones).")
    parser.add_argument("--orders", action="store_true", help="Atajo de --option 4 (mis órdenes).")
    parser.add_argument("--advice", action="store_true", help="Atajo de --option 5 (¿en qué empresa invertir?).")
    parser.add_argument("--backtest", action="store_true",
                        help="Evalúa el motor de puntaje con el histórico guardado.")
    parser.add_argument("--tune-weights", action="store_true",
                        help="Backtesting + grid-search para ajustar los pesos del motor.")
    parser.add_argument("--budget", type=float, default=None,
                        help="Saldo manual en VES (si la API no devuelve saldo).")
    parser.add_argument("--top", type=int, default=5, help="Cantidad de opciones a considerar (default 5).")
    parser.add_argument("--no-history", action="store_true", help="Ignora el histórico en el consejo.")
    parser.add_argument("--no-pause", action="store_true", help="No esperar ENTER entre pantallas.")
    parser.add_argument("--force-login", action="store_true", help="Descarta la sesión guardada y hace login.")
    parser.add_argument("--no-color", action="store_true", help="Salida sin colores (para logs/CI).")
    parser.add_argument("--quiet", action="store_true", help="Silencia el log por consola (solo a archivo).")
    parser.add_argument("--verbose", action="store_true", help="Log detallado en consola y archivo.")
    return parser


def _apply_args(args):
    """Aplica los ajustes de la CLI a las variables globales del módulo."""
    global _budget_override, _top_n, _use_history, _pause_enabled
    _budget_override = args.budget
    _top_n = max(1, int(args.top))
    _use_history = not args.no_history
    _pause_enabled = not args.no_pause


def _resolve_action(args):
    """Determina qué ejecutar; None significa menú interactivo."""
    if args.backtest or args.tune_weights:
        return "backtest"
    if args.advice:
        return "5"
    if args.analysis:
        return "2"
    if args.balance or args.portfolio:
        return "1"
    if args.instruments:
        return "3"
    if args.orders:
        return "4"
    return args.option


def run_cli(args):
    """Ejecuta la acción solicitada. Devuelve True si ya se hizo el trabajo (sin menú)."""
    setup_logging(quiet=args.quiet, verbose=args.verbose)
    if args.no_color:
        ui.set_no_color()
    _apply_args(args)

    action = _resolve_action(args)
    if action is None:
        return False

    logger.info("CLI: acción=%s top=%s presupuesto=%s", action, _top_n, _budget_override)
    _bootstrap(force_login=args.force_login)

    if action == "backtest":
        option_backtest(tune=args.tune_weights)
    else:
        OPTIONS[action]()

    _pause()
    logger.info("CLI: finalizado")
    return True


# ─────────────────────────────────────────────────────────────────
# Bucle principal (menú interactivo)
# ─────────────────────────────────────────────────────────────────
def main(argv=None):
    args = build_parser().parse_args(argv)
    if run_cli(args):
        return 0

    setup_logging(quiet=args.quiet, verbose=args.verbose)
    if args.no_color:
        ui.set_no_color()
    _apply_args(args)
    _bootstrap(force_login=args.force_login)

    while True:
        try:
            option = ui.show_main_menu()
        except (KeyboardInterrupt, EOFError):
            ui.console.print("\n[bold cyan]¡Hasta luego![/bold cyan]")
            return 0

        try:
            if option == "0":
                ui.console.print("[bold cyan]¡Hasta luego![/bold cyan]")
                return 0
            handler = OPTIONS.get(option)
            if handler:
                handler()
                _pause()
        except KeyboardInterrupt:
            ui.console.print("\n[bold yellow]⏹️ Operación cancelada por el usuario.[/bold yellow]")
        except Exception as error:
            logger.exception("Error no controlado en la opción %s", option)
            ui.console.print(f"[bold red]❌ Error inesperado:[/bold red] {error}")
        finally:
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        ui.console.print("\n[bold cyan]¡Hasta luego![/bold cyan]")



