import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def print_header():
    console.print("\n[bold cyan]===============================================[/bold cyan]")
    console.print("[bold cyan]   Mercosur Casa de Bolsa - Trading Bot        [/bold cyan]")
    console.print("[bold cyan]===============================================[/bold cyan]")

def print_auth_success(token, user_data, reused_cache=False):
    status = "Caché reutilizada" if reused_cache else "Nuevo token generado"
    console.print(f"[bold green]✔ Autenticación exitosa ({status})[/bold green]")

def print_mercosur_balances(balances):
    if not balances:
        console.print("[yellow]No se pudieron obtener saldos.[/yellow]")
        return
    
    avail = balances.get("available_balance", balances.get("disponible", 0.0))
    total = balances.get("total_balance", balances.get("total", 0.0))
    blocked = balances.get("blocked_balance", balances.get("bloqueado", 0.0))
    
    table = Table(title="🏦 Mercosur Casa de Bolsa Account Status", show_header=True)
    table.add_column("Cuenta", style="cyan")
    table.add_column("Disponible (VES)", style="green")
    table.add_column("Total (VES)", style="bold")
    table.add_column("Bloqueado (VES)", style="red")
    
    table.add_row(
        "Cuenta Principal",
        f"{float(avail):,.2f}",
        f"{float(total):,.2f}",
        f"{float(blocked):,.2f}"
    )
    console.print(table)

def safe_float(val, default=0.0):
    """Convierte cualquier valor a float de manera segura."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        val_str = str(val).replace(",", ".").strip()
        return float(val_str)
    except (ValueError, TypeError):
        return default

def display_quotes_table(quotes):
    """Muestra la tabla de cotizaciones convirtiendo tipos de forma segura."""
    table = Table(title="🏢 Listed Companies & Dividend Policies (Mercosur / BVC)")
    table.add_column("Symbol", style="bold cyan")
    table.add_column("Description / Company", style="white")
    table.add_column("Last Price (VES)", justify="right", style="green")
    table.add_column("Var. %", justify="right")
    table.add_column("Cash Amount (VES)", justify="right")
    table.add_column("Dividends", justify="center")

    for q in quotes:
        if not isinstance(q, dict):
            continue

        # Búsqueda de claves flexibles
        symbol = (
            q.get("symbol") or q.get("simbolo") or q.get("ticker") or 
            q.get("codigo") or q.get("symbolo") or "N/A"
        )
        
        description = (
            q.get("description") or q.get("descripcion") or q.get("company") or 
            q.get("nombre") or q.get("empresa") or "N/A"
        )

        last_price = safe_float(
            q.get("last_price") or q.get("precio_ultimo") or q.get("precio") or 
            q.get("price") or q.get("ultimo")
        )

        prev_price = safe_float(
            q.get("previous_price") or q.get("precio_anterior") or q.get("anterior")
        )

        # Cálculo seguro de variación para evitar ZeroDivisionError / TypeError
        var_pct = safe_float(q.get("variation") or q.get("variacion"))
        if var_pct == 0.0 and prev_price > 0:
            var_pct = ((last_price - prev_price) / prev_price) * 100.0

        cash_amount = safe_float(
            q.get("cash_amount") or q.get("monto_efectivo") or q.get("dividendo")
        )

        div_info = str(q.get("dividends") or q.get("dividendos") or "N/A")

        var_str = f"{var_pct:+.2f}%"
        var_style = "green" if var_pct > 0 else ("red" if var_pct < 0 else "white")

        table.add_row(
            str(symbol).strip(),
            str(description).strip(),
            f"{last_price:,.2f}",
            f"[{var_style}]{var_str}[/{var_style}]",
            f"{cash_amount:,.2f}",
            div_info
        )

    console.print(table)

def save_quotes(quotes):
    try:
        with open("quotes_latest.json", "w", encoding="utf-8") as f:
            json.dump(quotes, f, indent=4, ensure_ascii=False)
    except Exception as e:
        console.print(f"[dim red]Error guardando quotes: {e}[/dim red]")

def print_ai_disabled():
    console.print("[yellow]ℹ️ Análisis de IA deshabilitado (USE_AI=0).[/yellow]")

def print_news_summary(news):
    console.print(f"[bold green]✔ Noticias procesadas:[/bold green] {len(news)} artículos.")

def print_ai_engine_info(name, details):
    console.print(f"[bold blue]🤖 Motor de IA:[/bold blue] {name} ({details})")

def display_and_save_report(report_text):
    console.print(Panel(report_text, title="📊 Informe de Inversión IA", expand=False))

def print_order_execution_mode(auto_execute):
    mode = "AUTOMÁTICO" if auto_execute else "MANUAL / SOLO LECTURA"
    console.print(f"[bold yellow]Modo de ejecución:[/bold yellow] {mode}")
