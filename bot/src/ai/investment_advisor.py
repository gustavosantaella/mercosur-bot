import json

class InvestmentAdvisor:
    def __init__(self, ollama_client=None):
        self.ollama_client = ollama_client

    def analyze_investments(self, companies, news, bnc_balance=0.0, mercosur_balance=0.0):
        return self._analyze_with_local_engine(companies, news, bnc_balance, mercosur_balance)

    def _analyze_with_local_engine(self, companies, news, bnc_balance, mercosur_balance):
        recommendations = []
        
        for comp in companies:
            if not isinstance(comp, dict):
                continue

            symbol = comp.get("symbol", "N/A")
            price = comp.get("last_price", 0.0)
            div = comp.get("dividends", {})

            # Validar y formatear 'div' si es una cadena de texto o un diccionario
            if isinstance(div, str):
                try:
                    div = json.loads(div)
                except Exception:
                    div = {"raw_value": div}

            if isinstance(div, dict):
                pays_div = div.get("pays_dividends", div.get("paga_dividendos", "")) in ("Yes", "Sí", True)
                div_amount = float(div.get("monto_efectivo") or div.get("cash_amount") or 0.0)
            else:
                pays_div = False
                div_amount = 0.0

            recommendations.append({
                "symbol": symbol,
                "price": price,
                "pays_dividends": pays_div,
                "dividend_amount": div_amount
            })

        return {
            "status": "success",
            "mercosur_balance": mercosur_balance,
            "bnc_balance": bnc_balance,
            "recommendations": recommendations
        }
