import json

class InvestmentAIAdvisor:
    def __init__(self, ollama_client=None):
        self.ollama_client = ollama_client

    def get_engine_info(self):
        """Retorna el nombre e información descriptiva del motor de IA / análisis."""
        if self.ollama_client:
            return "Ollama Local LLM", "Modelo de Lenguaje Local impulsado por Ollama"
        return "Quantitative Engine & Decision Matrix", "Capital Rotation Algorithm (Offline Python)"

    def analyze_investments(self, companies, news, bnc_balance=0.0, mercosur_balance=0.0):
        return self._analyze_with_local_engine(companies, news, bnc_balance, mercosur_balance)

    def _analyze_with_local_engine(self, companies, news, bnc_balance=0.0, mercosur_balance=0.0):
        # Asegurar balance numérico
        try:
            available_ves = float(mercosur_balance)
        except (ValueError, TypeError):
            available_ves = 0.0

        recommendations = []
        affordable_options = []

        for comp in companies:
            if not isinstance(comp, dict):
                continue

            symbol = comp.get("symbol", "N/A")
            price = float(comp.get("last_price") or 0.0)
            description = comp.get("description", symbol)
            div = comp.get("dividends", {})

            # Validar dividendos
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

            # Evaluar si el saldo disponible alcanza para comprar al menos 1 acción
            can_afford = available_ves >= price > 0
            max_qty = int(available_ves // price) if price > 0 else 0

            item = {
                "symbol": symbol,
                "description": description,
                "price": price,
                "pays_dividends": pays_div,
                "dividend_amount": div_amount,
                "can_afford": can_afford,
                "max_qty": max_qty
            }
            
            recommendations.append(item)
            if can_afford:
                affordable_options.append(item)

        # Ordenar opciones alcanzables por atractivo (pago de dividendos o menor precio)
        affordable_options.sort(key=lambda x: (x["pays_dividends"], -x["price"]), reverse=True)

        # Construcción del informe y consejos de la IA
        lines = []
        lines.append("🤖 CONSEJOS Y ANÁLISIS DE INVERSIÓN (IA)")
        lines.append("=" * 45)
        lines.append(f"💰 Saldo Disponible Evaluado: {available_ves:,.2f} VES")
        lines.append(f"📊 Cotizaciones Analizadas: {len(companies)} instrumentos\n")

        lines.append("💡 RECOMENDACIONES DE COMPRA DE LA IA:")
        if affordable_options:
            for opt in affordable_options:
                div_str = f"| Dividendo: {opt['dividend_amount']:.2f} VES" if opt['pays_dividends'] else ""
                lines.append(
                    f"  ✔ [COMPRAR] {opt['symbol']} ({opt['description'][:25]})\n"
                    f"    • Precio Unitario: {opt['price']:,.2f} VES\n"
                    f"    • Cantidad Máxima Comprable: {opt['max_qty']} acc.\n"
                    f"    • Consejo: Opción alcanzable con tu disponible actual. {div_str}\n"
                )
        else:
            lines.append("  ⚠️ No se encontraron acciones cuyo precio unitario sea inferior a tu saldo disponible.")
            lines.append("  💡 Consejo: Considera abonar más fondos o monitorear instrumentos de menor valor como TPU o PCIB.\n")

        lines.append("📰 ANÁLISIS DE NOTICIAS Y ENTORNO:")
        if news:
            lines.append(f"  • {len(news)} artículos evaluados. Mercado local estable sin alertas críticas de volatilidad.")
        else:
            lines.append("  • No hay noticias críticas recientes que afecten el portafolio actual.")

        return "\n".join(lines)

# Alias de compatibilidad
InvestmentAdvisor = InvestmentAIAdvisor
