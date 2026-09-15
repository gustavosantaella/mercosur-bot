"""Punto de entrada del bot: menú interactivo de Mercosur Casa de Bolsa.

Opciones:
  1) Saldos y estado de cuenta
  2) Inversión automática / análisis completo IA (compras, rotación, liquidez)
  3) Instrumentos en cotización
  4) Órdenes registradas
  5) Consejos: ¿en qué empresa es mejor invertir? (saldo + instrumentos + noticias)
"""
import sys

from src import ui
from src.ai.investment_advisor import InvestmentAdvisor
from src.client.mercosur_client import MercosurClient
from src.config import AUTO_EXECUTE_ORDERS, USE_AI
from src.news.news_fetcher import NewsFetcher

client = MercosurClient()
advisor = InvestmentAdvisor()
news_fetcher = NewsFetcher()


def _pause(message="\nPresiona ENTER para volver al menú..."):
    try:
        input(message)
    except (EOFError, KeyboardInterrupt):
        pass


def _fetch_balance():
    """Devuelve (balances, saldo_disponible). El saldo es 0.0 si no se pudo consultar."""
    balances = client.get_balances() or {}
    raw = balances.get(
        "available_balance",
        balances.get("disponible", balances.get("saldo_disponible", balances.get("ves_available", 0.0))),
    )
    try:
        balance = float(raw)
    except (TypeError, ValueError):
        balance = 0.0
    return balances, balance


def _fetch_quotes():
    quotes = client.fetch_quotes() or []
    if quotes:
        ui.console.print(f"[bold green]✔ Cotizaciones obtenidas:[/bold green] {len(quotes)} instrumentos.")
    else:
        ui.console.print("[bold red]❌ No se pudieron obtener cotizaciones de Mercosur.[/bold red]")
    return quotes


def _fetch_news():
    """Noticias financieras. Si USE_AI=0 se omite la recolección (según configuración)."""
    if not USE_AI:
        ui.print_ai_disabled()
        ui.console.print("[dim]ℹ️ El consejo se generará solo con saldo e instrumentos.[/dim]")
        return []
    news = news_fetcher.fetch_latest_news()
    ui.print_news_summary(news)
    return news


# ─────────────────────────────────────────────────────────────────
# Opciones del menú
# ─────────────────────────────────────────────────────────────────
def option_balances():
    """1) Saldos y estado de cuenta."""
    ui.console.print("\n[bold yellow]💰 Consultando saldos y estado de cuenta...[/bold yellow]")
    balances = client.get_balances()
    ui.print_mercosur_balances(balances)


def option_full_analysis():
    """2) Inversión automática / análisis completo con IA."""
    ui.console.print("\n[bold yellow]🚀 Analizando saldo, mercado y noticias para generar el informe IA..."
                     "[/bold yellow]")

    balances, balance = _fetch_balance()
    ui.print_mercosur_balances(balances)

    quotes = _fetch_quotes()
    if not quotes:
        return

    news = _fetch_news()

    ui.console.print("\n[bold yellow]🤖 Generando análisis completo (compras, rotación y liquidez)..."
                     "[/bold yellow]")
    report = advisor.analyze_investments(
        companies=quotes,
        news=news,
        mercosur_balance=balance if balance > 0 else None,
    )
    ui.display_report(report, title="🧠 Análisis completo de inversión IA", save=True)

    # Gestión de ejecución de órdenes
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
    orders = client.fetch_orders()
    ui.display_orders(orders)


def option_advice():
    """5) Consejos: ¿en qué empresa es mejor invertir? (saldo + instrumentos + noticias)."""
    ui.console.print("\n[bold yellow]🎯 Consultando saldo, instrumentos y noticias para tu consejo..."
                     "[/bold yellow]")

    balances, balance = _fetch_balance()
    ui.print_mercosur_balances(balances)

    quotes = _fetch_quotes()
    if not quotes:
        return

    news = _fetch_news()

    ui.console.print("\n[bold yellow]🧠 Evaluando en qué empresa es mejor invertir..."
                     "[/bold yellow]")
    result = advisor.recommend_best_investment(
        companies=quotes,
        news=news,
        balance=balance if balance > 0 else None,
    )
    ui.display_best_investment(result)


# ─────────────────────────────────────────────────────────────────
# Bucle principal
# ─────────────────────────────────────────────────────────────────
def main():
    while True:
        try:
            option = ui.show_main_menu()
        except (KeyboardInterrupt, EOFError):
            ui.console.print("\n[bold cyan]¡Hasta luego![/bold cyan]")
            return

        try:
            if option == "1":
                option_balances()
                _pause()
            elif option == "2":
                option_full_analysis()
                _pause()
            elif option == "3":
                option_instruments()
                _pause()
            elif option == "4":
                option_orders()
                _pause()
            elif option == "5":
                option_advice()
                _pause()
            elif option == "0":
                ui.console.print("[bold cyan]¡Hasta luego![/bold cyan]")
                return
        except KeyboardInterrupt:
            ui.console.print("\n[bold yellow]⏹️ Operación cancelada por el usuario.[/bold yellow]")
        except Exception as error:
            ui.console.print(f"[bold red]❌ Error inesperado:[/bold red] {error}")
        finally:
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        ui.console.print("\n[bold cyan]¡Hasta luego![/bold cyan]")

