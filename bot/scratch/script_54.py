import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from src.config import OLLAMA_HOST, OLLAMA_MODEL

class InvestmentAIAdvisor:
    """
    Local AI for quantitative stock market analysis and portfolio decisions in BVC (Mercosur).
    Calculates automatic trading signals for:
    - 🟢 BUY
    - 🔴 SELL / CAPITAL ROTATION (Rebalance)
    - 💵 SELL FOR CASH / LIQUIDITY
    - 🟡 HOLD
    """

    def __init__(self, ollama_host: str = OLLAMA_HOST, ollama_model: str = OLLAMA_MODEL):
        self.ollama_host = ollama_host.rstrip('/')
        self.ollama_model = ollama_model

    def is_ollama_available(self) -> bool:
        """
        Checks if local Ollama LLM server is active and responding.
        """
        try:
            res = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def get_engine_info(self) -> Tuple[str, str]:
        """
        Returns (engine_name, model_details) tuple for active AI engine.
        """
        if self.is_ollama_available():
            return "Ollama (Local LLM)", f"{self.ollama_model} @ {self.ollama_host}"
        return "Quantitative Engine & Decision Matrix", "Capital Rotation Algorithm (Offline Python)"

    def analyze_investments(
        self,
        companies: List[Dict[str, Any]],
        news: List[Dict[str, Any]],
        bnc_balance: Optional[float] = None,
        mercosur_balance: Optional[float] = None
    ) -> str:
        """
        Main entry point for investment analysis and portfolio recommendations.
        """
        if self.is_ollama_available():
            ollama_analysis = self._analyze_with_ollama(companies, news, bnc_balance, mercosur_balance)
            if ollama_analysis:
                return ollama_analysis

        return self._analyze_with_local_engine(companies, news, bnc_balance, mercosur_balance)

    def _analyze_with_ollama(
        self,
        companies: List[Dict[str, Any]],
        news: List[Dict[str, Any]],
        bnc_balance: Optional[float] = None,
        mercosur_balance: Optional[float] = None
    ) -> Optional[str]:
        """
        Executes LLM inference via local Ollama server.
        """
        mercosur_info = f"MERCOSUR AVAILABLE BALANCE: {mercosur_balance:,.2f} VES" if mercosur_balance is not None else "MERCOSUR BALANCE: Not specified"
        bnc_info = f"BNC BANK AVAILABLE BALANCE: {bnc_balance:,.2f} VES" if bnc_balance is not None else "BNC BALANCE: Not specified / Skipped"

        prompt = f"""
You are an expert portfolio manager and financial analyst for Bolsa de Valores de Caracas (BVC).

OPERATIONAL BALANCE STATUS:
- {mercosur_info}
- {bnc_info}

REAL-TIME QUOTES AND DIVIDENDS (Mercosur Casa de Bolsa):
{json.dumps(companies, indent=2, ensure_ascii=False)}

ECONOMIC AND FINANCIAL NEWS:
{json.dumps(news, indent=2, ensure_ascii=False)}

STRATEGIC REQUIREMENTS:
Based on market liquidity, price variation, available balances, and news sentiment:
1. Stock BUY recommendations (evaluating purchasable shares with Mercosur balance of {mercosur_balance if mercosur_balance else 'N/A'} VES).
2. Stock SELL AND REBALANCE recommendations (rotating stagnant capital into top performers).
3. Stock SELL FOR CASH LIQUIDITY recommendations.
4. HOLD recommendations.

Provide a clean, direct Markdown report in Spanish with clear rationale.
"""
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False
        }

        try:
            res = requests.post(f"{self.ollama_host}/api/generate", json=payload, timeout=60)
            if res.status_code == 200:
                return res.json().get("response")
            else:
                print(f"[Ollama Error] HTTP {res.status_code}: {res.text}")
                return None
        except Exception as e:
            print(f"[Ollama Exception] {e}")
            return None

    def _analyze_with_local_engine(
        self,
        companies: List[Dict[str, Any]],
        news: List[Dict[str, Any]],
        bnc_balance: Optional[float] = None,
        mercosur_balance: Optional[float] = None
    ) -> str:
        """
        100% offline quantitative algorithm (SARA - Sell And Rotate Assets).
        """
        positive_keywords = ["crecimiento", "aumento", "consenso", "inversión", "acuerdo", "producción", "ganancias", "recuperación"]
        negative_keywords = ["inflación", "caída", "sanciones", "crisis", "riesgo", "baja", "conflicto"]

        news_score = 0
        for item in news:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            news_score += sum(1 for w in positive_keywords if w in text) - sum(1 for w in negative_keywords if w in text)

        total_market_cash = sum(c.get('cash_amount', c.get('monto_efectivo', 0)) for c in companies) or 1.0

        evaluated_companies = []
        for emp in companies:
            price = emp.get("last_price", emp.get("precio_ultimo", 0.0))
            if price <= 0:
                continue

            var_pct = emp.get("relative_variation_pct", emp.get("variacion_rel_pct", 0.0))
            cash = emp.get("cash_amount", emp.get("monto_efectivo", 0.0))
            volume = emp.get("volume", emp.get("volumen", 0.0))
            div = emp.get("dividends", emp.get("dividendos", {}))
            pays_div = div.get("pays_dividends", div.get("paga_dividendos", "")) in ("Yes", "Sí")

            liquidity_share = (cash / total_market_cash) * 100.0
            score_q = (liquidity_share * 0.50) + (var_pct * 0.30) + (20.0 if pays_div else 0.0)

            max_shares_mercosur = int(mercosur_balance // price) if (mercosur_balance and mercosur_balance > 0 and price > 0) else 0
            max_shares_bnc = int(bnc_balance // price) if (bnc_balance and bnc_balance > 0 and price > 0) else 0

            if score_q >= 5.0 or (var_pct > 1.0 and cash > 1000000):
                action = "🟢 COMPRAR"
                strategy_type = "Inversión Fuerte en Activo Líquido"
                reason = "Sólida liquidez institucional con momento alcista y dividendo respaldado."
            elif var_pct > 0 and cash > 100000:
                action = "🟢 COMPRAR MODERADO"
                strategy_type = "Acumulación Progresiva"
                reason = "Buen comportamiento de precio con liquidez operable."
            elif var_pct < 0 and cash > 500000:
                action = "🔴 VENDER / REBALANCEAR"
                strategy_type = "Rotación de Capital hacia Acciones con Mayor Retorno"
                reason = f"Variación negativa ({var_pct:+.2f}%). Conviene vender para rotar capital hacia acciones líderes."
            elif cash < 5000 and volume > 0:
                action = "🔴 VENDER PARA LIQUIDEZ"
                strategy_type = "Liberar Efectivo"
                reason = "Baja actividad del emisor. Recomendable vender si se necesita efectivo libre en cuenta."
            elif cash == 0:
                action = "🟡 MANTENER / SIN VOLUMEN"
                strategy_type = "Pausa Operativa"
                reason = "Sin volumen en la rueda actual."
            else:
                action = "🟡 MANTENER"
                strategy_type = "Posición Estable"
                reason = "Comportamiento estable dentro del rango bursátil."

            evaluated_companies.append({
                **emp,
                "score_q": score_q,
                "liquidity_share": liquidity_share,
                "max_shares_mercosur": max_shares_mercosur,
                "max_shares_bnc": max_shares_bnc,
                "action": action,
                "strategy_type": strategy_type,
                "reason": reason
            })

        buy_recommendations = sorted([e for e in evaluated_companies if "COMPRAR" in e["action"]], key=lambda x: x["score_q"], reverse=True)[:5]
        rebalance_sales = sorted([e for e in evaluated_companies if "REBALANCEAR" in e["action"]], key=lambda x: x.get("relative_variation_pct", 0.0))[:3]
        cash_sales = sorted([e for e in evaluated_companies if "LIQUIDEZ" in e["action"]], key=lambda x: x.get("cash_amount", 0.0))[:3]

        report = []
        report.append("# 🧠 Matriz Cuantitativa de Inversión, Compras & Rebalanceo de Portafolio\n")
        report.append("> **Procesamiento:** 100% Local (Algoritmo de Rotación de Activos SARA)")
        if mercosur_balance is not None:
            report.append(f"> **Saldo Mercosur Casa de Bolsa:** `{mercosur_balance:,.2f} VES`")
        else:
            report.append("> **Saldo Mercosur:** `No disponible`")
        if bnc_balance is not None:
            report.append(f"> **Saldo Banco (BNC en Línea):** `{bnc_balance:,.2f} VES`")
        else:
            report.append("> **Saldo Banco (BNC):** `No consultado / Extracción desactivada`")
        report.append(f"> **Volumen Total Mercado:** `{total_market_cash:,.2f} VES` | **Empresas Evaluadas:** {len(evaluated_companies)}\n")

        report.append("## 🟢 1. Oportunidades de COMPRA (Maximizar Retorno & Dividendos)\n")
        for idx, emp in enumerate(buy_recommendations, 1):
            div = emp.get("dividends", {})
            sym = emp.get("symbol", emp.get("simbolo", ""))
            name = emp.get("name", emp.get("nombre", ""))
            last_p = emp.get("last_price", emp.get("precio_ultimo", 0.0))
            var_p = emp.get("relative_variation_pct", emp.get("variacion_rel_pct", 0.0))
            cash_m = emp.get("cash_amount", emp.get("monto_efectivo", 0.0))

            report.append(f"### {idx}. {sym} - {name}")
            report.append(f"- **Acción:** `{emp['action']}` | **Estrategia:** {emp['strategy_type']}")
            report.append(f"- **Precio:** `{last_p:,.2f} VES` | **Variación:** `{var_p:+.2f}%`")
            report.append(f"- **Monto Transado:** `{cash_m:,.2f} VES` ({emp['liquidity_share']:.2f}% del mercado)")
            if mercosur_balance is not None:
                cost_mercosur = emp['max_shares_mercosur'] * last_p
                report.append(f"- **🛍️ Capacidad de Compra con Saldo Mercosur:** `{emp['max_shares_mercosur']:,} acciones` (Inversión estimada: `{cost_mercosur:,.2f} VES`)")
            if bnc_balance and bnc_balance > 0:
                cost_bnc = emp['max_shares_bnc'] * last_p
                report.append(f"- **🏦 Capacidad de Compra con Saldo BNC:** `{emp['max_shares_bnc']:,} acciones` (Inversión estimada: `{cost_bnc:,.2f} VES`)")
            report.append(f"- **💵 Dividendo:** {div.get('pays_dividends', 'N/D')} ({div.get('frequency', 'N/D')}) - {div.get('type', 'N/D')}")
            report.append(f"- **Fundamento IA:** {emp['reason']}\n")

        report.append("---\n")
        report.append("## 🔴 2. Acciones para VENDER Y ROTAR CAPITAL (Rebalanceo Inteligente)\n")
        if rebalance_sales:
            report.append("Se recomienda **vender** las siguientes posiciones estancadas o en corrección para **rebalancear e invertir el capital** en los líderes del mercado:\n")
            for idx, emp in enumerate(rebalance_sales, 1):
                sym = emp.get("symbol", emp.get("simbolo", ""))
                name = emp.get("name", emp.get("nombre", ""))
                last_p = emp.get("last_price", emp.get("precio_ultimo", 0.0))
                var_p = emp.get("relative_variation_pct", emp.get("variacion_rel_pct", 0.0))

                report.append(f"### {idx}. {sym} - {name}")
                report.append(f"- **Recomendación:** `🔴 VENDER Y REBALANCEAR`")
                report.append(f"- **Precio Actual:** `{last_p:,.2f} VES` | **Variación Diaria:** `{var_p:+.2f}%`")
                report.append(f"- **Motivo de Venta:** {emp['reason']}")
                if buy_recommendations:
                    top_sym = buy_recommendations[0].get("symbol", buy_recommendations[0].get("simbolo", ""))
                    top_name = buy_recommendations[0].get("name", buy_recommendations[0].get("nombre", "")).strip()
                    report.append(f"- **Destino Sugerido del Capital:** Comprar `{top_sym}` ({top_name}) para capturar momento alcista y rendimiento por dividendo.\n")
        else:
            report.append("No se detectan presiones vendedoras críticas en las empresas activas del día.\n")

        report.append("---\n")
        report.append("## 💵 3. Estrategia para GENERAR LIQUIDEZ EN EFECTIVO\n")
        if cash_sales:
            report.append("Si necesitas **retirar efectivo libre** en tu cuenta de Mercosur, la IA sugiere vender las siguientes posiciones con menor potencial de apreciación inmediata:\n")
            for idx, emp in enumerate(cash_sales, 1):
                sym = emp.get("symbol", emp.get("simbolo", ""))
                name = emp.get("name", emp.get("nombre", "")).strip()
                report.append(f"- **{sym} ({name}):** {emp['reason']}")
        else:
            report.append("Para generar efectivo inmediato, prioriza vender las posiciones que muestren variación 0.00% y bajo volumen relativo.")

        report.append("\n---\n")
        report.append("## 🛡️ Reglas Algorítmicas de Ejecución de Portafolio")
        report.append("1. **Regla de Rotación:** Vender posiciones con variación diaria negativa para evitar el costo de oportunidad y reinvertir en los emisores con >50% del volumen del mercado.")
        report.append("2. **Regla de Liquidez:** Mantener al menos un 15% del portafolio en acciones bancarias de alta bursatilidad (BNC, BPV) que permiten venta inmediata en cualquier rueda.")
        report.append("3. **Cosecha de Dividendos:** Conservar antes de las Asambleas de Accionistas las acciones que pagan dividendo mixto (Efectivo + Acciones liberadas).")
        return "\n".join(report)

    def get_recommended_orders(
        self,
        companies: List[Dict[str, Any]],
        mercosur_balance: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates actionable BUY/SELL order dictionaries based on Mercosur account balance.
        """
        if not mercosur_balance or mercosur_balance <= 0:
            return []

        candidates = []
        total_market_cash = sum(c.get('cash_amount', c.get('monto_efectivo', 0)) for c in companies) or 1.0

        for emp in companies:
            price = emp.get("last_price", emp.get("precio_ultimo", 0.0))
            if price <= 0:
                continue

            var_pct = emp.get("relative_variation_pct", emp.get("variacion_rel_pct", 0.0))
            cash = emp.get("cash_amount", emp.get("monto_efectivo", 0.0))
            div = emp.get("dividends", emp.get("dividendos", {}))
            pays_div = div.get("pays_dividends", div.get("paga_dividendos", "")) in ("Yes", "Sí")

            liquidity_share = (cash / total_market_cash) * 100.0
            score_q = (liquidity_share * 0.50) + (var_pct * 0.30) + (20.0 if pays_div else 0.0)

            if score_q >= 5.0 or (var_pct > 0 and cash > 100000):
                max_shares = int(mercosur_balance // price)
                symbol = emp.get("symbol", emp.get("simbolo", ""))
                if max_shares > 0 and symbol:
                    candidates.append({
                        "order_type": "COMPRA",
                        "symbol": symbol,
                        "quantity": max_shares,
                        "price": price,
                        "score_q": score_q
                    })

        candidates = sorted(candidates, key=lambda x: x["score_q"], reverse=True)
        return candidates[:1]




