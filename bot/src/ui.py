"""Interfaz de consola (Rich): menús, tablas, paneles e informes de inversión."""
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

try:
    from src.config import QUOTES_FILE, REPORT_FILE
except Exception:  # pragma: no cover - fallback defensivo
    QUOTES_FILE = REPORT_FILE = None

# En Windows algunas consolas no están en UTF-8 y los emojis rompen la salida
for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    encoding = (getattr(stream, "encoding", "") or "").lower()
    if hasattr(stream, "reconfigure") and encoding and encoding not in ("utf-8", "utf8"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

console = Console()


def _num(value, default=0.0):
    """Convierte cualquier valor (None/str) a float sin romper la interfaz."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pick(balances: Dict[str, Any], keys, default=0.0):
    """Devuelve el primer valor disponible entre varias claves posibles."""
    for key in keys:
        if key in balances and balances[key] is not None:
            return balances[key]
    return default


# ─────────────────────────────────────────────────────────────────
# Cabeceras y estado
# ─────────────────────────────────────────────────────────────────
def print_header():
    console.print(Panel.fit(
        "[bold cyan]🤖 MERCADO DE VALORES BVC - INVERSOR AUTOMÁTICO[/bold cyan]\n"
        "[dim]Mercosur Casa de Bolsa · Análisis local con IA[/dim]",
        border_style="cyan",
    ))


def print_auth_success(token=None, cliente_data=None, reused_cache=False):
    status = "caché reutilizada" if reused_cache else "nuevo token obtenido"
    token_txt = f" [dim]{(str(token)[:18] + '...') if token else ''}[/dim]"
    console.print(f"[bold green]✔ Autenticación exitosa[/bold green] ({status}){token_txt}")
    data = cliente_data if isinstance(cliente_data, dict) else {}
    name = str(data.get("nombre") or data.get("username") or "").strip()
    if name:
        console.print(f"👤 Cliente: [cyan]{name}[/cyan] | RIF: {data.get('rif', 'N/D')} "
                      f"| KYC: {data.get('estado_kyc', 'N/D')}")


def print_ai_engine_info(engine_name: str, engine_detail: str = ""):
    console.print(f"[bold cyan]🧠 Motor de análisis:[/bold cyan] [bold white]{engine_name}[/bold white]"
                  f" [dim]({engine_detail})[/dim]")


def print_ai_disabled():
    console.print("[bold yellow]ℹ️ IA/noticias desactivadas en configuración (USE_AI=0).[/bold yellow]")


def print_order_execution_mode(auto_execute: bool):
    if auto_execute:
        console.print("[bold red]🚨 MODO EJECUCIÓN REAL ACTIVO (AUTO_EXECUTE_ORDERS=1).[/bold red] "
                      "Las órdenes se enviarían a Mercosur.")
    else:
        console.print("[bold yellow]ℹ️ Modo simulación/recomendación (AUTO_EXECUTE_ORDERS=0). "
                      "No se envían órdenes reales.[/bold yellow]")


def print_news_summary(news):
    if not news:
        console.print("[dim]📰 Sin noticias disponibles (sin internet o feeds caídos).[/dim]")
        return
    console.print(f"[bold green]✔ Noticias obtenidas:[/bold green] {len(news)} titulares")
    table = Table(title="📰 Noticias financieras recientes", show_lines=False)
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Titular", style="white")
    table.add_column("Fuente", style="cyan", no_wrap=True)
    for idx, item in enumerate(news[:10], 1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("titulo") or "").strip()
        source = str(item.get("source") or item.get("fuente") or "N/D").strip()
        table.add_row(str(idx), title[:95], source[:28])
    console.print(table)


# ─────────────────────────────────────────────────────────────────
# Saldos, instrumentos y órdenes
# ─────────────────────────────────────────────────────────────────
def print_mercosur_balances(balances):
    if not balances or not isinstance(balances, dict):
        console.print("[yellow]⚠️ No se pudieron obtener saldos de la cuenta.[/yellow]")
        return

    available = _num(_pick(balances, ("available_balance", "disponible", "saldo_disponible", "ves_available")))
    total = _num(_pick(balances, ("total_balance", "total", "actual", "saldo_actual", "saldo")))
    blocked = _num(_pick(balances, ("blocked_balance", "bloqueado", "bloqueos")))

    table = Table(title="🏦 Estado de Cuenta Mercosur Casa de Bolsa")
    table.add_column("Cuenta", style="cyan")
    table.add_column("Disponible (VES)", style="green", justify="right")
    table.add_column("Total (VES)", style="bold", justify="right")
    table.add_column("Bloqueado (VES)", style="red", justify="right")
    table.add_row("Cuenta Principal", f"{available:,.2f}", f"{total:,.2f}", f"{blocked:,.2f}")
    console.print(table)

    if available <= 0:
        console.print("[bold yellow]⚠️ Saldo disponible en 0.00 VES: los consejos se generarán igual "
                      "usando el ranking de mercado y planes de entrada de referencia.[/bold yellow]")
    else:
        console.print(f"[bold green]💵 Saldo disponible para operar:[/bold green] {available:,.2f} VES")


def display_instruments(quotes):
    if not quotes:
        console.print("[bold red]❌ No se encontraron instrumentos en cotización.[/bold red]")
        return

    table = Table(title="🏢 Instrumentos en Cotización (BVC / Mercosur)")
    table.add_column("Símbolo", style="cyan", no_wrap=True)
    table.add_column("Descripción / Empresa", style="magenta")
    table.add_column("Último Precio (VES)", justify="right", style="green")
    table.add_column("Var. %", justify="right")
    table.add_column("Monto Negociado (VES)", justify="right", style="yellow")

    for item in quotes:
        if not isinstance(item, dict):
            continue
        var_val = _num(item.get("var_pct", item.get("relative_variation_pct")))
        var_color = "red" if var_val < 0 else ("green" if var_val > 0 else "white")
        symbol = str(item.get("symbol") or item.get("simbolo") or "N/A")
        description = str(item.get("description") or item.get("descripcion") or "Sin Nombre")
        price = _num(item.get("last_price", item.get("precio_ultimo")))
        traded = _num(item.get("cash_amount", item.get("monto_efectivo")))
        table.add_row(symbol, description[:45], f"{price:,.2f}",
                      f"[{var_color}]{var_val:+.2f}%[/{var_color}]", f"{traded:,.2f}")

    console.print(table)

    if QUOTES_FILE:
        try:
            with open(QUOTES_FILE, "w", encoding="utf-8") as handle:
                json.dump(quotes, handle, ensure_ascii=False, indent=2)
            console.print(f"[dim]💾 Cotizaciones guardadas en {QUOTES_FILE}[/dim]")
        except Exception as error:
            console.print(f"[dim]⚠️ No se pudo guardar el archivo de cotizaciones: {error}[/dim]")


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
        if not isinstance(order, dict):
            continue
        tipo = str(order.get("tipo") or "N/D")
        status = str(order.get("status") or order.get("estado") or "N/D")
        tipo_color = "green" if tipo.upper().startswith("COMPRA") else "red"
        status_color = "yellow" if status.upper() in ("ABIERTA", "ABIERTA/PARCIAL") else "green"
        table.add_row(
            str(order.get("id", "N/D")),
            f"[{tipo_color}]{tipo}[/{tipo_color}]",
            str(order.get("symbol") or order.get("cod_simb") or "N/D"),
            f"[{status_color}]{status}[/{status_color}]",
            f"{_num(order.get('requested_qty')):,.2f}",
            f"{_num(order.get('requested_price')):,.2f}",
            f"{_num(order.get('blocked_amount')):,.2f}",
        )

    console.print(table)


# ─────────────────────────────────────────────────────────────────
# Ranking e informes de IA
# ─────────────────────────────────────────────────────────────────
def display_ranking(ranking, title="🎯 Ranking IA de instrumentos"):
    if not ranking:
        return
    table = Table(title=title)
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Símbolo", style="cyan", no_wrap=True)
    table.add_column("Empresa", style="magenta")
    table.add_column("Precio (VES)", justify="right", style="green")
    table.add_column("Var. %", justify="right")
    table.add_column("Puntaje IA", justify="right", style="bold")
    table.add_column("Acción", style="white")

    for position, item in enumerate(ranking, 1):
        var_val = _num(item.get("var_pct"))
        var_color = "red" if var_val < 0 else ("green" if var_val > 0 else "white")
        table.add_row(
            str(position),
            str(item.get("symbol", "N/D")),
            str(item.get("description", ""))[:38],
            f"{_num(item.get('price')):,.2f}",
            f"[{var_color}]{var_val:+.2f}%[/{var_color}]",
            f"{_num(item.get('score')):,.2f}",
            str(item.get("action", "")),
        )
    console.print(table)


def save_report(report_text: str) -> Optional[str]:
    """Guarda el informe en disco (REPORT_FILE) y devuelve la ruta o None si falla."""
    if not REPORT_FILE:
        return None
    try:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as handle:
            handle.write(f"<!-- Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n\n")
            handle.write(report_text)
        return str(REPORT_FILE)
    except Exception as error:
        console.print(f"[dim]⚠️ No se pudo guardar el informe: {error}[/dim]")
        return None


def display_report(report_text: str, title=None, save=True):
    """Imprime un informe Markdown y opcionalmente lo guarda en disco."""
    if title:
        console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))
    console.print(Markdown(str(report_text or "")))
    if save:
        saved_path = save_report(str(report_text or ""))
        if saved_path:
            console.print(f"[dim]💾 Informe guardado en {saved_path}[/dim]")


def display_best_investment(result: Dict[str, Any]):
    """Muestra el consejo de la opción 5: en qué empresa es mejor invertir."""
    if not result:
        console.print("[bold red]❌ No fue posible generar el consejo de inversión.[/bold red]")
        return

    engine_name, engine_detail = result.get("engine", ("Motor local", ""))
    print_ai_engine_info(engine_name, engine_detail)

    best = result.get("best")
    if best:
        balance_txt = (f"{_num(result.get('balance')):,.2f} VES"
                       if result.get("balance_available") else "No disponible / 0.00 VES")
        console.print(Panel(
            f"[bold green]🥇 Mejor empresa para invertir:[/bold green] "
            f"[bold white]{best.get('symbol')}[/bold white] — {best.get('description')}\n"
            f"[cyan]Precio:[/cyan] {_num(best.get('price')):,.2f} VES | "
            f"[cyan]Variación:[/cyan] {_num(best.get('var_pct')):+.2f}% | "
            f"[cyan]Puntaje IA:[/cyan] {_num(best.get('score')):,.2f}\n"
            f"[cyan]Acción sugerida:[/cyan] {best.get('action')}\n"
            f"[cyan]Saldo evaluado:[/cyan] {balance_txt}",
            title="🎯 Consejo de Inversión",
            border_style="green",
        ))

    if result.get("ranking"):
        display_ranking(result["ranking"][:5], title="🥈 Top 5 de instrumentos por puntaje IA")

    display_report(result.get("report", ""), title="🧠 Informe completo del consejo IA", save=True)


# ─────────────────────────────────────────────────────────────────
# Menú principal
# ─────────────────────────────────────────────────────────────────
def show_main_menu():
    console.clear()
    print_header()
    console.print("  [bold green]1.[/bold green] 💰 Ver Saldos y Estado de Cuenta")
    console.print("  [bold green]2.[/bold green] 🚀 Inversión Automática / Análisis Completo IA")
    console.print("  [bold green]3.[/bold green] 📈 Instrumentos (Listar Empresas Cotizando)")
    console.print("  [bold green]4.[/bold green] 📋 Órdenes (Ver mis órdenes registradas)")
    console.print("  [bold green]5.[/bold green] 🎯 Consejos (¿En qué empresa es mejor invertir?)")
    console.print("  [bold red]0.[/bold red] 🚪 Salir\n")

    return Prompt.ask(
        "👉 Seleccione una opción",
        choices=["1", "2", "3", "4", "5", "0"],
        default="3",
    )


