import json
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

def print_header():
    console.print("\n[bold cyan]==========================================")
    console.print("[bold cyan] Mercosur Casa de Bolsa - Trading Bot")
    console.print("[bold cyan]==========================================\n")

def print_auth_success(token, cliente_data, reused_cache=False):
    status = "Caché reutilizada" if reused_cache else "Nuevo token obtenido"
    console.print(f"[bold green]✔ Autenticación exitosa ({status})[/bold green]")

def print_mercosur_balances(balances):
    if not balances:
        console.print("[yellow]No se pudieron obtener saldos.[/yellow]")
        return

    avail = balances.get("available_balance", balances.get("disponible", 0.0))
    total = balances.get("total_balance", balances.get("total", 0.0))
    blocked = balances.get("blocked_balance", balances.get("bloqueado", 0.0))

    table = Table(title="Mercosur Casa de Bolsa Account Status")
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

def show_main_menu():
    console.clear()
    console.print(
        Panel.fit(
            "[bold cyan]🤖 MERCADO DE VALORES BVC - INVERSOR AUTOMÁTICO[/bold cyan]\n"
            "[dim]Seleccione una opción del menú para continuar[/dim]",
            border_style="cyan"
        )
    )
    console.print("  [bold green]1.[/bold green] 💰 Ver Saldos y Estado de Cuenta")
    console.print("  [bold green]2.[/bold green] 🚀 Inversión Automática / Consejos IA")
    console.print("  [bold green]3.[/bold green] 📈 Instrumentos (Listar Empresas Cotizando)")
    console.print("  [bold green]4.[/bold green] 📋 Órdenes (Ver mis órdenes registradas)")
    console.print("  [bold red]0.[/bold red] 🚪 Salir\n")

    return Prompt.ask("👉 Seleccione una opción", choices=["1", "2", "3", "4", "0"], default="3")

def display_instruments(quotes):
    if not quotes:
        console.print("[bold red]❌ No se encontraron instrumentos en cotización.[/bold red]")
        return

    table = Table(title="🏢 Instrumentos en Cotización (BVC / Mercosur)")
    table.add_column("Símbolo", style="cyan", no_wrap=True)
    table.add_column("Descripción / Empresa", style="magenta")
    table.add_column("Último Precio (VES)", justify="right", style="green")
    table.add_column("Var. %", justify="right")
    table.add_column("Monto Efectivo", justify="right")

    for item in quotes:
        var_val = float(item.get("var_pct", 0.0))
        var_color = "red" if var_val < 0 else "green"
        table.add_row(
            item.get("symbol", "N/A"),
            item.get("description", "Sin Nombre"),
            f"{float(item.get('last_price', 0.0)):,.2f}",
            f"[{var_color}]{var_val:+.2f}%[/{var_color}]",
            f"{float(item.get('cash_amount', 0.0)):,.2f}"
        )

    console.print(table)

def display_orders(orders):
    if not orders:
        console.print("[bold red]❌ No se encontraron órdenes registradas.[/bold red]")
        return

    table = Table(title="📋 Mis Órdenes (Mercosur / BVC)")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Tipo", style="bold")
    table.add_column("Símbolo", style="cyan")
    table.add_column("Estado", style="magenta")
    table.add_column("Cant. Sol.", justify="right")
    table.add_column("Precio Sol. (VES)", justify="right", style="green")
    table.add_column("Monto Bloq. (VES)", justify="right", style="yellow")

    for order in orders:
        tipo_color = "green" if order["tipo"] == "COMPRA" else "red"
        status_color = "yellow" if order["status"] == "ABIERTA" else "green"
        
        table.add_row(
            str(order["id"]),
            f"[{tipo_color}]{order['tipo']}[/{tipo_color}]",
            order["symbol"],
            f"[{status_color}]{order['status']}[/{status_color}]",
            f"{order['requested_qty']:,.2f}",
            f"{order['requested_price']:,.2f}",
            f"{order['blocked_amount']:,.2f}"
        )

    console.print(table)
