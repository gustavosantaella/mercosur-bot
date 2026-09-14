import sys
from src.config import USE_AI, FETCH_BNC_BALANCE, AUTO_EXECUTE_ORDERS
from src.client import MercosurClient, BNCScraper
from src.news import NewsFetcher
from src.ai import InvestmentAIAdvisor
from src import ui


def authenticate():
    """Authenticate with Mercosur and return the client instance."""
    ui.console.print("\n[yellow]🔑 Authenticating with Mercosur Casa de Bolsa...[/yellow]")
    client = MercosurClient()
    try:
        had_token = bool(client.token)
        token = client.login()
        ui.print_auth_success(token, client.user_data, reused_cache=had_token)
        return client
    except Exception as e:
        ui.console.print(f"[bold red]❌ Authentication Error:[/bold red] {e}")
        sys.exit(1)


def option_balances(client):
    """Option 1: Show Mercosur account balances."""
    ui.console.print("\n[yellow]💰 Fetching Account Balances from Mercosur...[/yellow]")
    try:
        balances = client.get_balances()
        ui.print_mercosur_balances(balances)
    except Exception as e:
        ui.console.print(f"[bold red]❌ Error fetching Mercosur balance:[/bold red] {e}")


def option_auto_invest(client):
    """Option 2: Full automated investment flow (quotes, news, AI, orders)."""

    # 1. Mercosur Account Balances
    ui.console.print("\n[yellow]💰 Step 1: Fetching Account Balances from Mercosur...[/yellow]")
    mercosur_balances = {}
    mercosur_balance = 0.0
    try:
        mercosur_balances = client.get_balances()
        mercosur_balance = mercosur_balances.get("available_balance", 0.0)
        ui.print_mercosur_balances(mercosur_balances)
    except Exception as e:
        ui.console.print(f"[bold red]❌ Error fetching Mercosur balance:[/bold red] {e}")

    # 2. Real-time Quotes
    ui.console.print("\n[yellow]📈 Step 2: Fetching Real-time Stock Quotes...[/yellow]")
    try:
        companies = client.get_companies_summary()
        ui.console.print(f"[bold green]✔ Quotes fetched:[/bold green] {len(companies)} instruments.")
        ui.display_quotes_table(companies)
        ui.save_quotes(companies)
    except Exception as e:
        ui.console.print(f"[bold red]❌ Error fetching stock quotes:[/bold red] {e}")
        return

    # Control flag USE_AI (0 or 1)
    if not USE_AI:
        ui.print_ai_disabled()
        return

    # 3. News Collection
    ui.console.print("\n[yellow]📰 Step 3: Gathering Financial News...[/yellow]")
    news = NewsFetcher().fetch_latest_news()
    ui.print_news_summary(news)

    # 4. BNC Bank Balance Extraction (Selenium Web Scraping)
    ui.console.print("\n[yellow]🏦 Step 4: Fetching BNC Bank Available Balance...[/yellow]")
    bnc_balance = None
    if FETCH_BNC_BALANCE:
        try:
            bnc_scraper = BNCScraper()
            bnc_balance = bnc_scraper.fetch_balance()
            if bnc_balance is not None:
                ui.console.print(f"[bold green]✔ BNC balance retrieved:[/bold green] {bnc_balance:,.2f} VES")
            else:
                ui.console.print("[bold yellow]⚠️ Could not fetch BNC balance. Continuing without bank balance filter.[/bold yellow]")
        except Exception as e:
            ui.console.print(f"[bold red]❌ Error in BNC Scraper:[/bold red] {e}")
    else:
        ui.console.print("[dim]ℹ️ BNC balance check disabled (FETCH_BNC_BALANCE=0 in .env).[/dim]")

    # 5. Investment AI Analysis & Quantitative Engine
    ui.console.print("\n[yellow]🤖 Step 5: Generating AI Investment Analysis & Purchasing Power...[/yellow]")
    advisor = InvestmentAIAdvisor()
    engine_name, engine_details = advisor.get_engine_info()
    ui.print_ai_engine_info(engine_name, engine_details)

    report_text = advisor.analyze_investments(
        companies,
        news,
        bnc_balance=bnc_balance,
        mercosur_balance=mercosur_balance
    )
    ui.display_and_save_report(report_text)

    # 6. Order Execution Management (Buy / Sell)
    ui.console.print("\n[yellow]⚡ Step 6: Automatic Order Execution Control...[/yellow]")
    ui.print_order_execution_mode(AUTO_EXECUTE_ORDERS)

    if AUTO_EXECUTE_ORDERS:
        ui.console.print("[bold green]🚀 Processing recommended orders for execution in Mercosur Casa de Bolsa...[/bold green]")
        if mercosur_balance <= 0:
            ui.console.print("[bold yellow]⚠️ Insufficient available balance in Mercosur to place buy orders.[/bold yellow]")
        else:
            orders = advisor.get_recommended_orders(companies, mercosur_balance=mercosur_balance)
            if not orders:
                ui.console.print("[bold yellow]ℹ️ No buy orders generated matching available balance.[/bold yellow]")
            else:
                for ord_req in orders:
                    try:
                        ui.console.print(f"[bold cyan]📤 Submitting {ord_req['order_type']} order to Mercosur:[/bold cyan] {ord_req['quantity']:,} {ord_req['symbol']} @ {ord_req['price']:,.2f} VES...")
                        res = client.create_order(
                            order_type=ord_req['order_type'],
                            symbol=ord_req['symbol'],
                            quantity=ord_req['quantity'],
                            price=ord_req['price']
                        )
                        ui.console.print(f"[bold green]✔ ORDER EXECUTED SUCCESSFULLY![/bold green] Response: {res}")
                    except Exception as ex_ord:
                        err_msg = str(ex_ord)
                        if "CLAVE_OPERACIONES_REQUERIDA" in err_msg:
                            ui.console.print("[bold red]❌ Orden rechazada por Mercosur:[/bold red] Se requiere tu Clave de Operaciones de Mercosur.")
                            ui.console.print("[bold yellow]💡 SOLUCIÓN:[/bold yellow] Configura tu clave en el archivo [bold].env[/bold]: [cyan]MERCOSUR_CLAVE_OPERACIONES=tu_clave_de_operaciones[/cyan]")
                        else:
                            ui.console.print(f"[bold red]❌ Order submission failed:[/bold red] {err_msg}")


def print_menu():
    """Display the main menu."""
    ui.console.print("\n[bold blue]═══════════════════════════════════════[/bold blue]")
    ui.console.print("[bold blue]           📋 MENÚ PRINCIPAL           [/bold blue]")
    ui.console.print("[bold blue]═══════════════════════════════════════[/bold blue]")
    ui.console.print("  [bold cyan]1)[/bold cyan] 💰 Saldos")
    ui.console.print("  [bold cyan]2)[/bold cyan] 🤖 Inversión automática")
    ui.console.print("  [bold cyan]0)[/bold cyan] 🚪 Salir")
    ui.console.print("[bold blue]═══════════════════════════════════════[/bold blue]")


def main():
    ui.print_header()

    # Authenticate once at startup
    client = authenticate()

    while True:
        print_menu()
        try:
            choice = input("\n  Selecciona una opción: ").strip()
        except (KeyboardInterrupt, EOFError):
            ui.console.print("\n[bold yellow]👋 ¡Hasta luego![/bold yellow]")
            break

        if choice == "1":
            option_balances(client)
        elif choice == "2":
            option_auto_invest(client)
        elif choice == "0":
            ui.console.print("\n[bold yellow]👋 ¡Hasta luego![/bold yellow]")
            break
        else:
            ui.console.print("[bold red]❌ Opción no válida. Intenta de nuevo.[/bold red]")


if __name__ == "__main__":
    main()
