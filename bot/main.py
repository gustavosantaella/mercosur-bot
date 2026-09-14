from src.ui import show_main_menu, display_instruments, print_mercosur_balances
from src.client.mercosur_client import MercosurClient
from src.ai.investment_advisor import InvestmentAdvisor
from rich.console import Console

console = Console()
client = MercosurClient()
advisor = InvestmentAdvisor()

def main():
    while True:
        option = show_main_menu()

        if option == "1":
            console.print("\n[bold yellow]💰 Consultando saldos y estado de cuenta...[/bold yellow]")
            balances = client.get_balances()
            print_mercosur_balances(balances)
            input("\nPresiona ENTER para continuar...")
        
        elif option == "2":
            console.print("\n[bold yellow]🚀 Analizando mercado, saldos y generando consejos de IA...[/bold yellow]")
            
            # Obtener datos reales concurrentes
            balances = client.get_balances()
            mercosur_bal = balances.get("disponible", balances.get("ves_available", 0.0))
            
            quotes = client.fetch_quotes()
            
            # Generar informe de inversión y consejos
            analysis_report = advisor.analyze_investments(
                companies=quotes, 
                news=[], 
                mercosur_balance=mercosur_bal
            )
            
            console.print(f"\n{analysis_report}")
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
