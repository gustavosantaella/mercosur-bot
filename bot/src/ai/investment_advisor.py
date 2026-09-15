"""Motor de análisis y consejos de inversión para la BVC (Mercosur).

Dos modos de funcionamiento:
  1. Motor cuantitativo local (100% offline, sin dependencias): puntúa cada
     instrumento combinando liquidez negociada, variación diaria, política de
     dividendos (src/ai/dividends.py) y el sentimiento de las noticias.
  2. Ollama (LLM local) opcional: si el servidor responde, enriquece el informe.

CLAVE: los consejos se generan SIEMPRE, incluso cuando el saldo es 0 o no se
pudo consultar (en ese caso se entrega el ranking y planes de entrada con
presupuestos de referencia).
"""
import json
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.config import (
        EXCLUDE_SYMBOLS,
        HTTP_TIMEOUT,
        OLLAMA_HOST,
        OLLAMA_MODEL,
        SCORE_WEIGHT_DIVIDEND,
        SCORE_WEIGHT_LIQUIDITY,
        SCORE_WEIGHT_NEWS,
        SCORE_WEIGHT_TREND,
        SCORE_WEIGHT_VARIATION,
        USE_AI,
    )
except Exception:  # pragma: no cover - fallback defensivo
    EXCLUDE_SYMBOLS, HTTP_TIMEOUT = [], 10
    OLLAMA_HOST, OLLAMA_MODEL, USE_AI = "http://localhost:11434", "llama3.2", True
    SCORE_WEIGHT_LIQUIDITY, SCORE_WEIGHT_VARIATION = 0.50, 0.30
    SCORE_WEIGHT_TREND, SCORE_WEIGHT_DIVIDEND, SCORE_WEIGHT_NEWS = 0.50, 20.0, 2.0

try:
    from .dividends import get_dividend_info
except Exception:  # pragma: no cover
    def get_dividend_info(symbol: str) -> Dict[str, Any]:
        return {"pays_dividends": "Subject to Assembly", "frequency": "Annual / Eventual",
                "type": "Cash or Stock", "details": "Depende de la Asamblea de Accionistas."}


POSITIVE_KEYWORDS = (
    "crecimiento", "aumento", "aumenta", "ganancia", "ganancias", "utilidad", "utilidades",
    "recuperación", "recuperacion", "acuerdo", "inversión", "inversion", "producción",
    "produccion", "expansión", "expansion", "dividendo", "dividendos", "récord", "record",
    "alza", "mejora", "optimismo", "rentabilidad", "liquidez", "estabilidad", "impulso",
)
NEGATIVE_KEYWORDS = (
    "inflación", "inflacion", "caída", "caida", "pérdida", "perdida", "crisis", "riesgo",
    "sanción", "sancion", "sanciones", "conflicto", "cierre", "baja", "despido", "deuda",
    "morosidad", "quiebra", "contracción", "contraccion", "suspensión", "suspension",
    "incertidumbre", "déficit", "deficit",
)

# Presupuestos de referencia para orientar la inversión cuando no hay saldo disponible
REFERENCE_BUDGETS = (1_000.0, 10_000.0, 100_000.0)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convierte a float tolerando None, strings con formato y valores vacíos."""
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace("\u00a0", "")
    if not text:
        return default
    # Formato venezolano: 1.234,56 -> 1234.56
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(",") == 1 and len(text.split(",")[-1]) <= 2:
        text = text.replace(",", ".")
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


class InvestmentAIAdvisor:
    """Consejero de inversión: ranking, mejor empresa y planes de compra."""

    # Pesos del motor (configurables por .env y ajustables con el backtesting)
    DEFAULT_WEIGHTS = {
        "liquidity": SCORE_WEIGHT_LIQUIDITY,
        "variation": SCORE_WEIGHT_VARIATION,
        "trend": SCORE_WEIGHT_TREND,
        "dividend": SCORE_WEIGHT_DIVIDEND,
        "news": SCORE_WEIGHT_NEWS,
    }

    @classmethod
    def score_value(cls, liquidity_share, var_pct, pays_dividends=False, news_bonus=0.0,
                    trend_pct=0.0, weights=None):
        """Fórmula ÚNICA de puntaje (compartida con el backtesting).

        score = liquidez*peso + variación*peso + tendencia*peso + dividendos + noticias
        """
        effective = dict(cls.DEFAULT_WEIGHTS)
        if weights:
            effective.update({key: value for key, value in weights.items() if value is not None})

        score = (_safe_float(liquidity_share) * effective["liquidity"]) + \
                (_safe_float(var_pct) * effective["variation"])
        if pays_dividends:
            score += effective["dividend"]
        score += _safe_float(trend_pct) * effective["trend"]
        score += _safe_float(news_bonus) * effective["news"]
        return score

    def __init__(self, ollama_client=None, use_ollama: Optional[bool] = None):
        self.ollama_client = ollama_client
        self.ollama_host = (OLLAMA_HOST or "").rstrip("/")
        self.ollama_model = OLLAMA_MODEL or "llama3.2"
        self.use_ollama = USE_AI if use_ollama is None else bool(use_ollama)

    # ─────────────────────────────────────────────────────────────
    # Motor de IA (Ollama local, opcional)
    # ─────────────────────────────────────────────────────────────
    def is_ollama_available(self) -> bool:
        """True si el servidor local de Ollama responde."""
        try:
            import requests
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def get_engine_info(self) -> Tuple[str, str]:
        """Retorna (nombre_del_motor, detalle) para mostrar en la interfaz."""
        if self.use_ollama and self.ollama_client is None and self.is_ollama_available():
            return "Ollama (LLM local)", f"{self.ollama_model} @ {self.ollama_host}"
        return ("Matriz Cuantitativa de Decisión",
                "Algoritmo local de rotación de capital (offline, sin dependencias)")

    # ─────────────────────────────────────────────────────────────
    # Preparación de datos
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _news_text(news: Optional[List[Dict[str, Any]]]) -> List[str]:
        """Normaliza la lista de noticias a textos en minúsculas para análisis."""
        texts = []
        for item in news or []:
            if not isinstance(item, dict):
                if item:
                    texts.append(str(item).lower())
                continue
            blob = " ".join([
                _safe_str(item.get("title") or item.get("titulo")),
                _safe_str(item.get("summary") or item.get("resumen") or item.get("description")),
                _safe_str(item.get("source") or item.get("fuente")),
            ])
            if blob.strip():
                texts.append(blob.lower())
        return texts

    def _news_sentiment(self, news: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calcula el sentimiento agregado de las noticias (positivo/negativo/neutro)."""
        texts = self._news_text(news)
        positives, negatives = [], []
        for text in texts:
            positives.extend(kw for kw in POSITIVE_KEYWORDS if kw in text)
            negatives.extend(kw for kw in NEGATIVE_KEYWORDS if kw in text)

        score = len(positives) - len(negatives)
        if score > 0:
            label = "positivo"
        elif score < 0:
            label = "negativo"
        else:
            label = "neutro"

        return {
            "count": len(texts),
            "score": score,
            "label": label,
            "positives": sorted(set(positives)),
            "negatives": sorted(set(negatives)),
        }

    @staticmethod
    def _dividend_info(company: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Combina la política de dividendos de la BVC con lo que reporte la cotización."""
        info = dict(get_dividend_info(symbol))
        raw = company.get("dividends") or company.get("dividendos")
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                info.update({k: v for k, v in parsed.items() if v})
            elif raw.strip().upper() not in ("N/A", "NA", "NONE", "-"):
                info["report"] = raw.strip()

        flag = info.get("pays_dividends", info.get("paga_dividendos", ""))
        info["pays_dividends"] = flag
        info["pays"] = str(flag).strip().lower() in (
            "yes", "sí", "si", "true", "1", "variable / subject to assembly", "subject to assembly"
        )
        return info

    def _company_news_hits(self, symbol: str, name: str, news_texts: List[str]) -> int:
        """Cuenta menciones de la empresa en las noticias (aproximación de relevancia)."""
        if not news_texts:
            return 0
        keys = [symbol.lower()]
        for part in str(symbol).replace(".", " ").split():
            if len(part) >= 3 and part.lower() not in keys:
                keys.append(part.lower())
        first_word = str(name).split()[0].strip().lower() if str(name).split() else ""
        if len(first_word) >= 4 and first_word not in keys:
            keys.append(first_word)

        return sum(1 for text in news_texts for key in keys if key and key in text)

    def _evaluate_company(self, company, total_market_cash, sentiment, news_texts, stats=None):
        """Puntúa un instrumento combinando liquidez, variación, tendencia, dividendos y noticias."""
        symbol = _safe_str(company.get("symbol") or company.get("simbolo"), "N/A").upper()
        name = _safe_str(
            company.get("description") or company.get("descripcion")
            or company.get("name") or company.get("nombre"),
            symbol,
        )
        price = _safe_float(company.get("last_price") or company.get("precio_ultimo"))
        var_pct = _safe_float(
            company.get("var_pct", company.get("relative_variation_pct", company.get("variacion_rel")))
        )
        traded_cash = _safe_float(company.get("cash_amount") or company.get("monto_efectivo"))
        dividends = self._dividend_info(company, symbol)

        stats = stats or {}
        trend_pct = _safe_float(stats.get("trend_pct"))
        samples = int(_safe_float(stats.get("samples")))
        liquidity_share = (traded_cash / total_market_cash * 100.0) if total_market_cash else 0.0
        news_hits = self._company_news_hits(symbol, name, news_texts)
        direction = 1.0 if sentiment["score"] >= 0 else -1.0

        score = self.score_value(
            liquidity_share=liquidity_share,
            var_pct=var_pct,
            pays_dividends=dividends["pays"],
            news_bonus=news_hits * direction,
            trend_pct=trend_pct,
        )

        if score >= 25.0 and var_pct > 0:
            action, strategy = "🟢 COMPRAR", "Inversión fuerte en activo líquido"
            reason = "Alta liquidez negociada, momento alcista y dividendo respaldado por la BVC."
        elif var_pct > 0 and traded_cash >= 100_000:
            action, strategy = "🟢 COMPRAR (moderado)", "Acumulación progresiva"
            reason = "Comportamiento de precio positivo con liquidez suficiente para entrar y salir."
        elif dividends["pays"] and liquidity_share >= 1.0:
            action, strategy = "🟢 COMPRAR (por dividendos)", "Cosecha de dividendos"
            reason = "Emisor con política de dividendos activa y bursatilidad aceptable."
        elif var_pct < 0 and liquidity_share >= 5.0:
            action, strategy = "🔴 VENDER / REBALANCEAR", "Rotación de capital"
            reason = f"Corrección de {var_pct:+.2f}% con alto volumen: conviene rotar el capital."
        elif traded_cash < 5_000:
            action, strategy = "🔴 VENDER PARA LIQUIDEZ", "Liberar efectivo"
            reason = "Actividad muy baja en la rueda; difícil salir sin castigar el precio."
        else:
            action, strategy = "🟡 MANTENER", "Posición estable"
            reason = "Comportamiento dentro del rango esperado, sin señales fuertes."

        # Ajuste por tendencia histórica (solo si hay ruedas suficientes)
        if samples >= 3 and trend_pct > 8.0 and "MANTENER" in action:
            action, strategy = "🟢 COMPRAR (tendencia)", "Momentum sostenido"
            reason = f"Tendencia alcista sostenida de {trend_pct:+.2f}% en {samples} ruedas."

        if samples >= 2:
            reason = f"{reason} Tendencia de {trend_pct:+.2f}% en {samples} ruedas."

        return {
            "symbol": symbol,
            "description": name,
            "price": price,
            "var_pct": var_pct,
            "traded_cash": traded_cash,
            "liquidity_share": liquidity_share,
            "dividends": dividends,
            "news_hits": news_hits,
            "trend_pct": round(trend_pct, 2),
            "volatility": round(_safe_float(stats.get("volatility")), 2),
            "momentum_pct": round(_safe_float(stats.get("momentum_pct")), 2),
            "history_samples": samples,
            "score": round(score, 2),
            "action": action,
            "strategy": strategy,
            "reason": reason,
        }

    def rank_companies(self, companies, news=None, limit=None, history=None):
        """Ordena los instrumentos por atractivo (mayor puntaje primero).

        Si se pasa ``history`` (MarketHistory) se incorpora tendencia/volatilidad
        de las ruedas anteriores al puntaje.
        """
        companies = [c for c in (companies or []) if isinstance(c, dict)]
        sentiment = self._news_sentiment(news)
        news_texts = self._news_text(news)

        stats_map = {}
        if history is not None:
            try:
                stats_map = history.get_all_stats()
            except Exception:
                stats_map = {}

        total_market_cash = sum(
            _safe_float(c.get("cash_amount") or c.get("monto_efectivo")) for c in companies
        )
        if total_market_cash <= 0:
            total_market_cash = 1.0

        evaluated, excluded, seen = [], [], set()
        for company in companies:
            symbol = _safe_str(company.get("symbol") or company.get("simbolo"), "").upper()
            if not symbol or symbol in seen:
                continue
            price = _safe_float(company.get("last_price") or company.get("precio_ultimo"))
            if symbol in EXCLUDE_SYMBOLS or price <= 0:
                excluded.append(symbol)
                continue
            seen.add(symbol)
            evaluated.append(self._evaluate_company(
                company, total_market_cash, sentiment, news_texts, stats=stats_map.get(symbol)
            ))

        evaluated.sort(key=lambda item: item["score"], reverse=True)
        return {
            "ranking": evaluated[:limit] if limit else evaluated,
            "evaluated": evaluated,
            "excluded": sorted(set(excluded)),
            "sentiment": sentiment,
            "total_market_cash": total_market_cash,
            "analyzed": len(evaluated),
            "history_used": bool(stats_map),
        }

    @staticmethod
    def _qty_for(price, budget):
        """Cantidad entera de acciones comprables con un presupuesto dado."""
        if price <= 0 or budget <= 0:
            return 0
        return int(budget // price)

    def _attach_purchase_plan(self, ranking, balance):
        """Agrega a cada opción cuántas acciones se pueden comprar con el saldo (o con presupuestos de referencia)."""
        has_balance = balance is not None and _safe_float(balance, 0.0) > 0
        budget = _safe_float(balance, 0.0) if has_balance else 0.0
        for item in ranking:
            if has_balance:
                qty = self._qty_for(item["price"], budget)
                item["max_qty"] = qty
                item["max_investment"] = round(qty * item["price"], 2)
                item["affordable"] = qty > 0
                item["budget_plan"] = []
            else:
                plan = []
                for reference in REFERENCE_BUDGETS:
                    qty = self._qty_for(item["price"], reference)
                    plan.append({"budget": reference, "qty": qty,
                                 "invested": round(qty * item["price"], 2)})
                item["max_qty"] = 0
                item["max_investment"] = 0.0
                item["affordable"] = False
                item["budget_plan"] = plan
        return ranking

    # ─────────────────────────────────────────────────────────────
    # Informes
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _balance_line(balance, has_balance):
        if has_balance:
            return f"`{_safe_float(balance):,.2f} VES`"
        return "`No disponible / 0.00 VES`"

    @staticmethod
    def _capacity_lines(item, balance, has_balance):
        """Líneas que explican cuánto se puede comprar con o sin saldo."""
        lines = []
        if has_balance and item.get("affordable"):
            lines.append(
                f"- **Con tu saldo actual ({_safe_float(balance):,.2f} VES):** puedes comprar "
                f"`{item['max_qty']:,} acciones` (inversión de `{item['max_investment']:,.2f} VES`)."
            )
        elif has_balance:
            lines.append(
                f"- **Con tu saldo actual ({_safe_float(balance):,.2f} VES):** no alcanza para 1 "
                f"acción de {item['symbol']} (precio `{item['price']:,.2f} VES`)."
            )
        else:
            plan = " | ".join(
                f"{step['budget']:,.0f} VES -> {step['qty']:,} acc."
                for step in item.get("budget_plan", []) if step["qty"] > 0
            )
            if plan:
                lines.append(f"- **Plan de entrada sin saldo disponible (presupuestos de referencia):** {plan}")
            else:
                lines.append(
                    f"- **Plan de entrada:** el precio (`{item['price']:,.2f} VES`) excede los "
                    "presupuestos de referencia; evalúa un aporte mayor."
                )
        return lines

    def _news_block(self, sentiment, news):
        lines = ["## 📰 Contexto de noticias y sentimiento", ""]
        lines.append(
            f"- Noticias evaluadas: `{sentiment['count']}` | Sentimiento agregado: "
            f"**{sentiment['label']}** (`{sentiment['score']:+d}`)"
        )
        if sentiment["positives"]:
            lines.append(f"- Señales positivas detectadas: {', '.join(sentiment['positives'][:8])}")
        if sentiment["negatives"]:
            lines.append(f"- Señales de riesgo detectadas: {', '.join(sentiment['negatives'][:8])}")
        if not sentiment["count"]:
            lines.append("- Sin noticias disponibles (sin internet o feeds caídos): el consejo se basa "
                         "solo en instrumentos y saldo.")
        for item in (news or [])[:5]:
            if isinstance(item, dict):
                title = _safe_str(item.get("title") or item.get("titulo"))
                source = _safe_str(item.get("source") or item.get("fuente"), "N/D")
                if title:
                    lines.append(f"  - {title} *({source})*")
        lines.append("")
        return lines

    def _history_block(self, ranking, top=6):
        """Sección con tendencia/momentum/volatilidad de las ruedas anteriores."""
        lines = ["## 📈 Tendencia histórica (ruedas anteriores)", ""]
        with_history = [item for item in ranking if int(item.get("history_samples", 0)) >= 2][:top]
        if not with_history:
            lines.append("- Aún no hay histórico suficiente: el puntaje usa solo la rueda actual. "
                         "Ejecuta el bot a diario para acumular ruedas y activar tendencia/volatilidad.")
            lines.append("")
            return lines

        for item in with_history:
            lines.append(
                f"- **`{item['symbol']}`**: tendencia `{item['trend_pct']:+.2f}%` en "
                f"{item['history_samples']} ruedas | momentum `{item['momentum_pct']:+.2f}%` | "
                f"volatilidad `{item['volatility']:.2f}`"
            )
        lines.append("")
        return lines

    def _portfolio_block(self, positions, ranking):
        """Sección con la cartera real del usuario (posiciones y P&L)."""
        lines = ["## 🧾 Tu cartera real (posiciones y P&L)", ""]
        if not positions:
            lines.append("- Sin posiciones disponibles (cartera vacía o endpoint no accesible). "
                         "Las recomendaciones se basan en el ranking de mercado.")
            lines.append("")
            return lines

        ranking_map = {item["symbol"]: item for item in ranking}
        total_value = sum(_safe_float(p.get("market_value")) for p in positions)
        total_cost = sum(_safe_float(p.get("cost")) for p in positions)
        total_pnl = sum(_safe_float(p.get("pnl")) for p in positions)
        lines.append(
            f"- Posiciones: `{len(positions)}` | Invertido: `{total_cost:,.2f} VES` | "
            f"Valor de mercado: `{total_value:,.2f} VES` | "
            f"Resultado: `{total_pnl:+,.2f} VES`"
        )
        lines.append("")
        for position in positions[:12]:
            symbol = _safe_str(position.get("symbol"), "N/D")
            item = ranking_map.get(symbol)
            verdict = f" · IA: {item['action']}" if item else " · IA: sin cotización"
            lines.append(
                f"- **`{symbol}`**: {_safe_float(position.get('quantity')):,.2f} acc. | "
                f"costo prom. `{_safe_float(position.get('avg_price')):,.2f}` | "
                f"mercado `{_safe_float(position.get('market_price')):,.2f}` | "
                f"valor `{_safe_float(position.get('market_value')):,.2f} VES` | "
                f"P&L `{_safe_float(position.get('pnl')):+,.2f} VES` "
                f"(`{_safe_float(position.get('pnl_pct')):+.2f}%`){verdict}"
            )
        lines.append("")
        return lines

    def _build_best_report(self, result, balance, has_balance):

        """Informe enfocado: ¿en qué empresa es mejor invertir? (Opción 5)."""
        engine_name, engine_detail = self.get_engine_info()
        ranking = result["ranking"]
        sentiment = result["sentiment"]

        lines = ["# 🎯 Consejo IA: ¿En qué empresa es mejor invertir hoy?", ""]
        lines.append(f"> **Motor de análisis:** {engine_name} — {engine_detail}")
        lines.append(f"> **Saldo Mercosur:** {self._balance_line(balance, has_balance)}")
        lines.append(
            f"> **Instrumentos analizados:** `{result['analyzed']}` (excluidos: `{len(result['excluded'])}`)"
            f" | **Noticias evaluadas:** `{sentiment['count']}`"
        )
        lines.append(f"> **Volumen negociado del mercado:** `{result['total_market_cash']:,.2f} VES`")
        lines.append("")

        if not ranking:
            lines.append("## ⚠️ Sin datos suficientes")
            lines.append("No se recibieron instrumentos cotizados válidos. Verifica la conexión con "
                         "Mercosur y vuelve a intentarlo.")
            return "\n".join(lines)

        best = ranking[0]
        payout = "Sí" if best["dividends"]["pays"] else "No / sujeto a Asamblea"
        lines.append(f"## 🥇 Mejor opción: `{best['symbol']}` — {best['description']}")
        lines.append("")
        lines.append(f"- **Puntaje IA:** `{best['score']:,.2f} pts` (el más alto de {result['analyzed']} instrumentos)")
        lines.append(f"- **Acción sugerida:** `{best['action']}` — {best['strategy']}")
        lines.append(f"- **Precio por acción:** `{best['price']:,.2f} VES`")
        lines.append(f"- **Variación del día:** `{best['var_pct']:+.2f}%`")
        lines.append(f"- **Monto negociado:** `{best['traded_cash']:,.2f} VES` "
                     f"({best['liquidity_share']:.2f}% del mercado)")
        lines.append(f"- **Dividendos:** {payout} ({_safe_str(best['dividends'].get('frequency'), 'N/D')})")
        if int(best.get("history_samples", 0)) >= 2:
            lines.append(f"- **Tendencia histórica:** `{best['trend_pct']:+.2f}%` en "
                         f"{best['history_samples']} ruedas | momentum `{best['momentum_pct']:+.2f}%` | "
                         f"volatilidad `{best['volatility']:.2f}`")
        lines.append(f"- **¿Por qué la recomendamos?** {best['reason']}")
        lines.extend(self._capacity_lines(best, balance, has_balance))
        lines.append("")

        if len(ranking) > 1:
            lines.append("## 🥈 Alternativas evaluadas (Top 5)")
            lines.append("")
            for position, item in enumerate(ranking[1:5], start=2):
                lines.append(
                    f"{position}. `{item['symbol']}` — {item['description'][:38]} | "
                    f"`{item['price']:,.2f} VES` | `{item['var_pct']:+.2f}%` | "
                    f"puntaje `{item['score']:,.2f}` | {item['action']}"
                )
            lines.append("")

        lines.extend(self._news_block(sentiment, result.get("news")))
        lines.extend(self._history_block(ranking))
        lines.extend(self._portfolio_block(result.get("positions") or [], ranking))

        lines.append("## ✅ Plan de acción sugerido")
        lines.append("")
        if has_balance:
            lines.append(f"1. Destinar hasta `{_safe_float(balance):,.2f} VES` del saldo disponible a la opción principal.")
        else:
            lines.append("1. Sin saldo disponible: usa el plan de entrada por presupuestos de referencia "
                         "para programar tu aporte.")
        lines.append(f"2. Priorizar `{best['symbol']}` mientras mantenga variación positiva y liquidez alta.")
        lines.append("3. Diversificar con una segunda opción del Top 5 para reducir el riesgo de emisor único.")
        lines.append("4. Repetir este consejo en cada rueda: las variaciones y volúmenes cambian a diario.")
        lines.append("")
        lines.append("> ⚠️ Este informe es un análisis automatizado de datos de mercado y **no** constituye "
                     "asesoría financiera vinculante.")
        return "\n".join(lines)

    def _item_block(self, item, balance, has_balance, include_action=True):
        lines = [f"### `{item['symbol']}` — {item['description']}"]
        if include_action:
            lines.append(f"- **Acción:** `{item['action']}` | **Estrategia:** {item['strategy']}")
        lines.append(f"- **Precio:** `{item['price']:,.2f} VES` | **Variación:** `{item['var_pct']:+.2f}%`")
        lines.append(f"- **Monto negociado:** `{item['traded_cash']:,.2f} VES` "
                     f"({item['liquidity_share']:.2f}% del mercado)")
        lines.append(f"- **Puntaje IA:** `{item['score']:,.2f} pts`")
        if int(item.get("history_samples", 0)) >= 2:
            lines.append(f"- **Tendencia:** `{item['trend_pct']:+.2f}%` en "
                         f"{item['history_samples']} ruedas | momentum `{item['momentum_pct']:+.2f}%` | "
                         f"volatilidad `{item['volatility']:.2f}`")
        lines.append(f"- **Dividendos:** {_safe_str(item['dividends'].get('pays_dividends'), 'N/D')} "
                     f"({_safe_str(item['dividends'].get('frequency'), 'N/D')}) — "
                     f"{_safe_str(item['dividends'].get('type'), 'N/D')}")
        lines.append(f"- **Fundamento:** {item['reason']}")
        lines.extend(self._capacity_lines(item, balance, has_balance))
        lines.append("")
        return lines

    def _build_full_report(self, result, balance, has_balance, bnc_balance=None):
        """Informe completo de portafolio: compras, rotación, liquidez y reglas (Opción 2)."""
        engine_name, engine_detail = self.get_engine_info()
        ranked = result["evaluated"]
        sentiment = result["sentiment"]

        buys = [item for item in ranked if "COMPRAR" in item["action"]][:5]
        if not buys and ranked:
            buys = ranked[:3]
        rebalance = [item for item in ranked if "REBALANCEAR" in item["action"]][:3]
        cash_out = [item for item in ranked if "LIQUIDEZ" in item["action"]][:3]

        lines = ["# 🧠 Matriz Cuantitativa de Inversión, Compras y Rebalanceo de Portafolio", ""]
        lines.append(f"> **Motor de análisis:** {engine_name} — {engine_detail}")
        lines.append(f"> **Saldo Mercosur:** {self._balance_line(balance, has_balance)}")
        if bnc_balance is not None and _safe_float(bnc_balance) > 0:
            lines.append(f"> **Saldo BNC en Línea:** `{_safe_float(bnc_balance):,.2f} VES`")
        else:
            lines.append("> **Saldo BNC en Línea:** `No consultado / desactivado`")
        lines.append(
            f"> **Empresas evaluadas:** `{result['analyzed']}` (excluidas: `{len(result['excluded'])}`)"
            f" | **Noticias:** `{sentiment['count']}` (sentimiento: **{sentiment['label']}**)"
        )
        lines.append(f"> **Volumen total del mercado:** `{result['total_market_cash']:,.2f} VES`")
        lines.append("")

        if not ranked:
            lines.append("## ⚠️ Sin datos suficientes")
            lines.append("No se recibieron instrumentos cotizados válidos; no es posible generar "
                         "recomendaciones en esta rueda.")
            return "\n".join(lines)

        lines.append("## 🥇 1. Mejor empresa para invertir hoy")
        lines.append("")
        lines.extend(self._item_block(ranked[0], balance, has_balance, include_action=True))
        lines.append("---")
        lines.append("")

        lines.append("## 🟢 2. Oportunidades de COMPRA (maximizar retorno y dividendos)")
        lines.append("")
        if buys:
            for item in buys:
                lines.extend(self._item_block(item, balance, has_balance, include_action=False))
        else:
            lines.append("No se detectaron señales de compra claras en esta rueda. "
                         "Se recomienda esperar confirmación de volumen.")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## 🔴 3. Vender y rotar capital (rebalanceo inteligente)")
        lines.append("")
        if rebalance:
            for item in rebalance:
                lines.append(f"- **`{item['symbol']}` ({item['description'][:35]}):** {item['reason']}")
                if buys:
                    lines.append(f"  - Destino sugerido del capital: `{buys[0]['symbol']}` "
                                 f"({buys[0]['description'][:30]}).")
        else:
            lines.append("No se detectan presiones vendedoras críticas entre las empresas activas del día.")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## 💵 4. Estrategia para generar liquidez en efectivo")
        lines.append("")
        if cash_out:
            for item in cash_out:
                lines.append(f"- **`{item['symbol']}` ({item['description'][:35]}):** {item['reason']}")
        else:
            lines.append("No hay posiciones con liquidez crítica. Para efectivo inmediato, prioriza "
                         "instrumentos con variación `0.00%` y bajo monto negociado.")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.extend(self._news_block(sentiment, result.get("news")))
        lines.extend(self._history_block(ranked))
        lines.extend(self._portfolio_block(result.get("positions") or [], ranked))

        lines.append("---")
        lines.append("")
        lines.append("## 🛡️ 5. Reglas algorítmicas de ejecución")
        lines.append("")
        lines.append("1. **Rotación:** vender posiciones en corrección con alto volumen y reinvertir en los "
                     "emisores líderes por volumen negociado.")
        lines.append("2. **Liquidez:** mantener al menos un 15% del portafolio en acciones bancarias de alta "
                     "bursatilidad (BNC, BPV), de venta inmediata en cualquier rueda.")
        lines.append("3. **Cosecha de dividendos:** conservar hasta la Asamblea las acciones con dividendo "
                     "mixto (efectivo + acciones liberadas).")
        lines.append("")
        lines.append("> ⚠️ Análisis automatizado con fines informativos. No constituye asesoría financiera "
                     "vinculante; verifica cada orden antes de ejecutarla.")
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────────────────────
    def _analyze_with_ollama(self, companies, news, bnc_balance, mercosur_balance, top_n=5):
        """Enriquece el análisis con el LLM local. Retorna None si falla."""
        try:
            import requests
        except Exception:
            return None

        balance_txt = (f"{_safe_float(mercosur_balance):,.2f} VES"
                       if mercosur_balance is not None and _safe_float(mercosur_balance) > 0
                       else "NO DISPONIBLE / 0 VES")
        bnc_txt = (f"{_safe_float(bnc_balance):,.2f} VES" if _safe_float(bnc_balance) > 0
                   else "No consultado / desactivado")
        brief = [
            {"symbol": item["symbol"], "precio": item["price"], "variacion_pct": item["var_pct"],
             "monto_negociado": item["traded_cash"], "paga_dividendos": item["dividends"]["pays"],
             "puntaje": item["score"]}
            for item in self.rank_companies(companies, news)["ranking"][:20]
        ]

        prompt = f"""Eres un analista de portafolio experto de la Bolsa de Valores de Caracas (BVC).

SALDO DISPONIBLE EN MERCOSUR: {balance_txt}
SALDO BANCO (BNC): {bnc_txt}

COTIZACIONES Y PUNTAJES (datos reales de la rueda):
{json.dumps(brief, indent=2, ensure_ascii=False)}

NOTICIAS RECIENTES:
{json.dumps(news, indent=2, ensure_ascii=False)}

INSTRUCCIONES OBLIGATORIAS:
1. Indica con claridad EN QUÉ EMPRESA ES MEJOR INVERTIR hoy y por qué (precio, variación,
   liquidez negociada y dividendos).
2. Da un top {top_n} de opciones ordenadas.
3. Si el saldo es 0 o no está disponible, IGUAL debes dar tu recomendación y explicar el plan
   de entrada sugerido (cuántas acciones para presupuestos de 1.000 / 10.000 / 100.000 VES).
4. Indica qué vender/rebalancear y qué mantener.
5. Responde en español, en Markdown, directo y concreto.
"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=max(60, HTTP_TIMEOUT * 8),
            )
            if response.status_code == 200:
                return _safe_str(response.json().get("response")) or None
        except Exception:
            return None
        return None

    def recommend_best_investment(self, companies, news=None, balance=None, top_n=5,
                                  history=None, positions=None):
        """Responde "¿en qué empresa es mejor invertir?" — funciona CON o SIN saldo."""
        news = list(news or [])
        data = self.rank_companies(companies, news, history=history)
        ranking = self._attach_purchase_plan(data["ranking"], balance)

        balance_value = _safe_float(balance, 0.0)
        has_balance = balance is not None and balance_value > 0
        result = {
            "ranking": ranking,
            "evaluated": ranking,
            "excluded": data["excluded"],
            "sentiment": data["sentiment"],
            "total_market_cash": data["total_market_cash"],
            "analyzed": data["analyzed"],
            "history_used": data.get("history_used", False),
            "positions": list(positions or []),
            "news": news,
        }
        result["report"] = self._build_best_report(result, balance_value, has_balance)
        result["best"] = ranking[0] if ranking else None
        result["balance"] = balance_value
        result["balance_available"] = has_balance
        result["engine"] = self.get_engine_info()
        return result

    def analyze_investments(self, companies, news=None, bnc_balance=None, mercosur_balance=None,
                            top_n=5, use_ollama=None, history=None, positions=None):
        """Informe completo de portafolio (compras, rotación, liquidez y reglas)."""
        news = list(news or [])
        llm_enabled = self.use_ollama if use_ollama is None else bool(use_ollama)

        if llm_enabled and (self.ollama_client is not None or self.is_ollama_available()):
            llm_report = self._analyze_with_ollama(companies, news, bnc_balance, mercosur_balance, top_n)
            if llm_report:
                return llm_report

        data = self.rank_companies(companies, news, history=history)
        ranking = self._attach_purchase_plan(data["ranking"], mercosur_balance)
        balance_value = _safe_float(mercosur_balance, 0.0)
        has_balance = mercosur_balance is not None and balance_value > 0
        result = {
            "ranking": ranking,
            "evaluated": ranking,
            "excluded": data["excluded"],
            "sentiment": data["sentiment"],
            "total_market_cash": data["total_market_cash"],
            "analyzed": data["analyzed"],
            "history_used": data.get("history_used", False),
            "positions": list(positions or []),
            "news": news,
        }
        return self._build_full_report(result, balance_value, has_balance, bnc_balance)

    def get_recommended_orders(self, companies, mercosur_balance=None):
        """Órdenes de compra sugeridas (compatibilidad con el flujo de ejecución automática)."""
        budget = _safe_float(mercosur_balance, 0.0)
        if budget <= 0:
            return []

        orders = []
        for item in self.rank_companies(companies, news=None)["ranking"]:
            if "COMPRAR" not in item["action"]:
                continue
            quantity = self._qty_for(item["price"], budget)
            if quantity > 0:
                orders.append({
                    "order_type": "COMPRA",
                    "symbol": item["symbol"],
                    "quantity": quantity,
                    "price": item["price"],
                    "score_q": item["score"],
                })
            if len(orders) >= 1:
                break
        return orders


# Alias de compatibilidad
InvestmentAdvisor = InvestmentAIAdvisor







