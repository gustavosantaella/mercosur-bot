import io
import sys
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from src.config import DATA_DIR

# Configure UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

console = Console(force_terminal=True)

def print_header():
    console.print(Panel.fit(
        "[bold blue]🚀 STOCK MARKET QUOTES & INVESTMENT ADVISOR[/bold blue]\n"
        "[green]Mercosur Casa de Bolsa & Local Financial AI[/green]"
    ))

def print_auth_success(token: str, user_data: dict, reused_cache: bool = False):
    msg = "[bold green]✔ Reused Saved Session Token![/bold green]" if reused_cache else "[bold green]✔ POST Authentication Successful![/bold green]"
    console.print(f"{msg} Token: [dim]{token[:25]}...{token[-15:]}[/dim]")
    if user_data:
        name = user_data.get('nombre', '').strip()
        rif = user_data.get('rif')
        kyc = user_data.get('estado_kyc')
        console.print(f"👤 Client: [cyan]{name}[/cyan] | RIF: {rif} | KYC: {kyc}")

def display_quotes_table(companies: list):
    table = Table(title="🏢 Listed Companies & Dividend Policies (Mercosur / BVC)")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Description / Company", style="white")
    table.add_column("Last Price (VES)", justify="right", style="bold green")
    table.add_column("Var. %", justify="right")
    table.add_column("Cash Amount (VES)", justify="right", style="yellow")
    table.add_column("Dividends", style="magenta")

    for emp in companies:
        var_val = emp.get("relative_variation_pct", emp.get("variacion_rel_pct", 0.0))
        var_color = "green" if var_val > 0 else ("red" if var_val < 0 else "white")
        var_str = f"[{var_color}]{var_val:+.2f}%[/{var_color}]"
        
        div_info = emp.get("dividends", emp.get("dividendos", {}))
        div_str = f"{div_info.get('pays_dividends', div_info.get('paga_dividendos', 'N/A'))} ({div_info.get('frequency', div_info.get('frecuencia', 'N/A'))})"
        
        table.add_row(
            emp.get("symbol", emp.get("simbolo", "")),
            emp.get("name", emp.get("nombre", ""))[:40],
            f"{emp.get('last_price', emp.get('precio_ultimo', 0.0)):,.2f}",
            var_str,
            f"{emp.get('cash_amount', emp.get('monto_efectivo', 0.0)):,.2f}",
            div_str
        )

    console.print(table)

# Backward-compatible aliases
display_cotizaciones_table = display_quotes_table

def save_quotes(companies: list):
    json_path = DATA_DIR / "cotizaciones.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    console.print(f"💾 Quotes saved in [bold]{json_path.relative_to(DATA_DIR.parent)}[/bold]")

save_cotizaciones = save_quotes

def print_news_summary(news: list):
    console.print(f"[bold green]✔ Financial news fetched:[/bold green] {len(news)} headlines processed.")
    for idx, item in enumerate(news[:5], 1):
        title = item.get("title", item.get("titulo", ""))
        source = item.get("source", item.get("fuente", ""))
        console.print(f"  {idx}. [bold]{title}[/bold] ([dim]{source}[/dim])")

def print_ai_engine_info(engine_name: str, engine_details: str):
    console.print(f"[bold cyan]🧠 Active AI Engine:[/bold cyan] [bold white]{engine_name}[/bold white] ([dim]{engine_details}[/dim])")

def display_and_save_report(report_text: str):
    console.print("\n" + "="*80)
    console.print(Markdown(report_text))
    console.print("="*80 + "\n")

    md_path = DATA_DIR / "informe_inversion.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n\n")
        f.write(report_text)
    
    console.print(f"[bold green]✨ Process completed successfully![/bold green] Report saved to [bold]{md_path.relative_to(DATA_DIR.parent)}[/bold]")

def print_mercosur_balances(balances: dict):
    available = balances.get("available_balance", balances.get("saldo_disponible", 0.0))
    current = balances.get("current_balance", balances.get("saldo_actual", 0.0))
    blocked = balances.get("blocked_funds", balances.get("bloqueos", 0.0))
    currency = balances.get("currency", balances.get("moneda", "VES"))
    account = balances.get("account_name", balances.get("nombre_cuenta", "Main Account"))

    console.print(f"[bold green]✔ Mercosur Account Balance Retrieved:[/bold green] Available: [bold white]{available:,.2f} {currency}[/bold white] | Current Total: {current:,.2f} {currency} | Blocked: {blocked:,.2f} {currency}")

    console.print(Panel(
        f"[bold green]💵 Available Balance to Trade:[/bold green] [bold white]{available:,.2f} {currency}[/bold white]\n"
        f"[cyan]Total Current Balance:[/cyan] {current:,.2f} {currency} | [yellow]Blocked Funds:[/yellow] {blocked:,.2f} {currency}\n"
        f"[dim]Account:[/dim] {account}",
        title="🏦 Mercosur Casa de Bolsa Account Status",
        border_style="green" if available > 0 else "yellow"
    ))

print_mercosur_saldos = print_mercosur_balances


def print_order_execution_mode(auto_execute: bool):
    if auto_execute:
        console.print("[bold red]🚨 ATTENTION: REAL ORDER EXECUTION MODE ACTIVE (AUTO_EXECUTE_ORDERS=1). Orders will be submitted to Mercosur Casa de Bolsa.[/bold red]")
    else:
        console.print("[bold yellow]ℹ️ SIMULATION & RECOMMENDATION MODE ACTIVE (AUTO_EXECUTE_ORDERS=0). No real orders will be submitted.[/bold yellow]")

def print_ai_disabled():
    console.print("\n[bold yellow]ℹ️ AI analysis disabled in configuration (USE_AI=0). Skipping news and AI evaluation.[/bold yellow]")
    console.print("[bold green]✨ Process completed successfully (quotes only).[/bold green]")


