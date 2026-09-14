from src.ui import show_main_menu, display_instruments, print_mercosur_balances
from src.client.mercosur_client import MercosurClient
from rich.console import Console

console = Console()
client = MercosurClient()

def main():
    while True:
        option = show_main_menu()

        if option == "1":
            balances = client.get_balances()
            print_mercosur_balances(balances)
            input("\nPresiona ENTER para continuar...")
        elif option == "2":
            console.print("\n[bold yellow]🚀 Ejecutando Inversión Automática y Consejos de IA...[/bold yellow]")
            # Aquí va tu lógica actual de inversión automática
            input("\nPresiona ENTER para volver al menú...")
        elif option == "3":
            console.print("\n[bold yellow]📈 Obteniendo instrumentos en tiempo real...[/bold yellow]")
            quotes = client.fetch_quotes()
            display_instruments(quotes)
            input("\nPresiona ENTER para volver al menú...")
        elif option == "0":
            console.print("[bold cyan]¡Hasta luego![/bold cyan]")
            break

if __name__ == "__main__":
    main()
