"""Backtesting del motor de puntaje con el histórico SQLite (Bloque B8).

Responde a la pregunta: "¿el ranking del motor realmente anticipa retornos?".
Para cada rueda t con futuro suficiente (t+horizon) recalcula el score con los
datos de esa rueda y compara el retorno del Top-N contra el promedio del mercado
(edge = ventaja del motor frente a comprar cualquier instrumento).

También permite un grid-search de los pesos de liquidez/variación para ajustarlos
con datos en lugar de a ojo.
"""
from typing import Any, Dict, List, Optional

try:
    from src.config import (
        BACKTEST_HORIZON,
        BACKTEST_TOP_N,
        SCORE_WEIGHT_DIVIDEND,
        SCORE_WEIGHT_LIQUIDITY,
        SCORE_WEIGHT_VARIATION,
    )
except Exception:  # pragma: no cover
    BACKTEST_HORIZON, BACKTEST_TOP_N = 3, 3
    SCORE_WEIGHT_LIQUIDITY, SCORE_WEIGHT_VARIATION, SCORE_WEIGHT_DIVIDEND = 0.50, 0.30, 20.0

from src.ai.dividends import get_dividend_info
from src.ai.investment_advisor import InvestmentAIAdvisor

BASE_WEIGHTS = {
    "liquidity": SCORE_WEIGHT_LIQUIDITY,
    "variation": SCORE_WEIGHT_VARIATION,
    "trend": 0.0,      # el backtesting compara ruedas sueltas: sin tendencia
    "dividend": SCORE_WEIGHT_DIVIDEND,
    "news": 0.0,       # no hay noticias históricas guardadas
}


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pays_dividends(symbol: str) -> bool:
    info = get_dividend_info(symbol)
    return str(info.get("pays_dividends", "")).strip().lower() in (
        "yes", "sí", "si", "true", "1",
    )


def build_scores(rows: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """Calcula el score del motor para las filas de una rueda (sin noticias ni tendencia)."""
    total_cash = sum(_to_float(row.get("cash_amount")) for row in rows) or 1.0
    scored = []
    for row in rows:
        price = _to_float(row.get("price"))
        if price <= 0:
            continue
        symbol = str(row.get("symbol", "")).upper()
        traded_cash = _to_float(row.get("cash_amount"))
        liquidity_share = (traded_cash / total_cash) * 100.0
        score = InvestmentAIAdvisor.score_value(
            liquidity_share=liquidity_share,
            var_pct=_to_float(row.get("var_pct")),
            pays_dividends=_pays_dividends(symbol),
            weights=weights or BASE_WEIGHTS,
        )
        scored.append({"symbol": symbol, "price": price, "score": round(score, 4)})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def backtest_scoring(history, horizon: Optional[int] = None, top_n: Optional[int] = None,
                     weights: Optional[Dict[str, float]] = None,
                     min_instruments: int = 3) -> Dict[str, Any]:
    """Backtest del motor: retorno del Top-N vs promedio del mercado por rueda."""
    horizon = int(horizon or BACKTEST_HORIZON or 3)
    top_n = int(top_n or BACKTEST_TOP_N or 3)
    ruedas = [str(rueda) for rueda in history.available_ruedas()]

    result: Dict[str, Any] = {
        "ruedas": len(ruedas),
        "horizon": horizon,
        "top_n": top_n,
        "weights": dict(weights or BASE_WEIGHTS),
        "evaluations": [],
        "runs": 0,
        "hit_rate": 0.0,
        "avg_return_top": 0.0,
        "avg_return_market": 0.0,
        "edge": 0.0,
        "message": "",
    }

    if len(ruedas) <= horizon:
        result["message"] = (
            f"Se necesitan más de {horizon} ruedas guardadas (hay {len(ruedas)}). "
            "Ejecuta el bot a diario para acumular histórico."
        )
        return result

    evaluations = []
    for index in range(len(ruedas) - horizon):
        current, future = ruedas[index], ruedas[index + horizon]
        rows = history.market_snapshot(current)
        if len(rows) < min_instruments:
            continue

        future_prices = {
            str(row["symbol"]).upper(): _to_float(row.get("price"))
            for row in history.market_snapshot(future)
        }
        current_prices = {str(row["symbol"]).upper(): _to_float(row.get("price")) for row in rows}

        scored = build_scores(rows, weights)
        returns = {}
        for symbol, price in current_prices.items():
            future_price = future_prices.get(symbol)
            if price > 0 and future_price and future_price > 0:
                returns[symbol] = (future_price / price - 1.0) * 100.0
        if not returns:
            continue

        picks = [item["symbol"] for item in scored if item["symbol"] in returns][:top_n]
        if not picks:
            continue

        top_return = sum(returns[symbol] for symbol in picks) / len(picks)
        market_return = sum(returns.values()) / len(returns)
        evaluated = len(returns)

        evaluations.append({
            "rueda": current,
            "rueda_futura": future,
            "picks": picks,
            "return_top": round(top_return, 3),
            "return_market": round(market_return, 3),
            "edge": round(top_return - market_return, 3),
            "win": top_return > market_return,
            "evaluated": evaluated,
        })

    result["evaluations"] = evaluations
    result["runs"] = len(evaluations)
    if not evaluations:
        result["message"] = "No hay ruedas comparables con suficiente información para evaluar."
        return result

    result["hit_rate"] = round(
        100.0 * sum(1 for item in evaluations if item["win"]) / len(evaluations), 2
    )
    result["avg_return_top"] = round(
        sum(item["return_top"] for item in evaluations) / len(evaluations), 3
    )
    result["avg_return_market"] = round(
        sum(item["return_market"] for item in evaluations) / len(evaluations), 3
    )
    result["edge"] = round(result["avg_return_top"] - result["avg_return_market"], 3)
    result["message"] = "Backtest completado."
    return result


def grid_search_weights(history, horizon: Optional[int] = None, top_n: Optional[int] = None,
                        liquidity_values=(0.30, 0.50, 0.70),
                        variation_values=(0.10, 0.30, 0.50)) -> Dict[str, Any]:
    """Prueba combinaciones de pesos y devuelve la de mayor edge (ajuste con datos)."""
    horizon = int(horizon or BACKTEST_HORIZON or 3)
    top_n = int(top_n or BACKTEST_TOP_N or 3)
    baseline = backtest_scoring(history, horizon=horizon, top_n=top_n)

    candidates = []
    for liquidity in liquidity_values:
        for variation in variation_values:
            weights = dict(BASE_WEIGHTS)
            weights["liquidity"] = float(liquidity)
            weights["variation"] = float(variation)
            outcome = backtest_scoring(history, horizon=horizon, top_n=top_n, weights=weights)
            candidates.append({
                "liquidity": float(liquidity),
                "variation": float(variation),
                "edge": outcome.get("edge", 0.0),
                "hit_rate": outcome.get("hit_rate", 0.0),
                "runs": outcome.get("runs", 0),
            })

    usable = [item for item in candidates if item["runs"] > 0]
    usable.sort(key=lambda item: (item["edge"], item["hit_rate"]), reverse=True)
    return {
        "baseline": {
            "liquidity": baseline["weights"].get("liquidity"),
            "variation": baseline["weights"].get("variation"),
            "edge": baseline.get("edge", 0.0),
            "hit_rate": baseline.get("hit_rate", 0.0),
            "runs": baseline.get("runs", 0),
        },
        "candidates": candidates,
        "best": usable[0] if usable else None,
    }


def format_backtest_report(result: Dict[str, Any]) -> str:
    """Informe Markdown del backtest para consola/archivo."""
    lines = ["# 🧪 Backtesting del motor de puntaje", ""]
    lines.append(
        f"> Ruedas guardadas: `{result['ruedas']}` | Horizonte: `{result['horizon']}` ruedas | "
        f"Top-N: `{result['top_n']}` | Pesos: liquidez `{result['weights']['liquidity']}` · "
        f"variación `{result['weights']['variation']}` · dividendo `{result['weights']['dividend']}`"
    )
    if result.get("runs", 0) == 0:
        lines.append("")
        lines.append(f"⚠️ {result.get('message', 'Sin datos suficientes.')}")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"## Resultado ({result['runs']} ruedas evaluadas)")
    lines.append("")
    lines.append(f"- **Aciertos (Top-{result['top_n']} mejor que el mercado):** `{result['hit_rate']:.2f}%`")
    lines.append(f"- **Retorno medio del Top-{result['top_n']}:** `{result['avg_return_top']:+.2f}%`")
    lines.append(f"- **Retorno medio del mercado:** `{result['avg_return_market']:+.2f}%`")
    lines.append(f"- **Ventaja del motor (edge):** `{result['edge']:+.2f}%`")
    lines.append("")
    lines.append("## Detalle por rueda")
    lines.append("")
    for evaluation in result["evaluations"][:15]:
        mark = "✅" if evaluation["win"] else "❌"
        lines.append(
            f"- {mark} `{evaluation['rueda']}` → `{evaluation['rueda_futura']}` | "
            f"picks: {', '.join(evaluation['picks'])} | top `{evaluation['return_top']:+.2f}%` vs "
            f"mercado `{evaluation['return_market']:+.2f}%` (edge `{evaluation['edge']:+.2f}%`)"
        )
    lines.append("")
    lines.append("## Interpretación")
    lines.append("")
    if result["edge"] > 0 and result["hit_rate"] >= 50:
        lines.append("- El motor **aporta valor**: el Top-N supera al promedio del mercado en más de la mitad de las ruedas.")
    elif result["edge"] > 0:
        lines.append("- El motor supera al mercado en promedio, pero con baja consistencia: amplía la muestra.")
    else:
        lines.append("- El motor **no supera** al promedio del mercado con los pesos actuales. Revisa los pesos con "
                     "el ajuste (grid-search) o prioriza instrumentos de alta liquidez.")
    lines.append("")
    lines.append("> Muestra basada en tus propias ruedas guardadas; el histórico se enriquece en cada ejecución.")
    return "\n".join(lines)


def format_weights_report(grid: Dict[str, Any]) -> str:
    """Informe Markdown del ajuste de pesos sugerido."""
    lines = ["# ⚖️ Ajuste de pesos sugerido (grid-search)", ""]
    base = grid["baseline"]
    lines.append(
        f"> **Pesos actuales:** liquidez `{base['liquidity']}` · variación `{base['variation']}` → "
        f"edge `{base['edge']:+.2f}%` en `{base['runs']}` ruedas"
    )
    lines.append("")

    best = grid.get("best")
    if not best:
        lines.append("⚠️ No hay suficiente histórico para recomendar pesos. Sigue ejecutando el bot a diario.")
        return "\n".join(lines)

    lines.append(f"## 🏆 Mejor combinación: liquidez `{best['liquidity']}` · variación `{best['variation']}`")
    lines.append("")
    lines.append(f"- Edge `{best['edge']:+.2f}%` | aciertos `{best['hit_rate']:.2f}%` en `{best['runs']}` ruedas")
    if best["edge"] > base["edge"]:
        lines.append(f"- Mejora de `{best['edge'] - base['edge']:+.2f}%` frente a los pesos actuales.")
        lines.append("")
        lines.append("**Aplicar (opcional) en tu `.env`:**")
        lines.append("```")
        lines.append(f"SCORE_WEIGHT_LIQUIDITY={best['liquidity']}")
        lines.append(f"SCORE_WEIGHT_VARIATION={best['variation']}")
        lines.append("```")
    else:
        lines.append("- Los pesos actuales ya son los mejores del conjunto probado: **no cambies nada**.")
    lines.append("")
    lines.append("## Combinaciones probadas")
    lines.append("")
    for candidate in sorted(grid["candidates"], key=lambda item: item["edge"], reverse=True):
        lines.append(
            f"- liquidez `{candidate['liquidity']}` · variación `{candidate['variation']}` → "
            f"edge `{candidate['edge']:+.2f}%` | aciertos `{candidate['hit_rate']:.2f}%` | "
            f"ruedas `{candidate['runs']}`"
        )
    lines.append("")
    lines.append("> Con muestras pequeñas los pesos son orientativos: cuantas más ruedas acumules, más fiable el ajuste.")
    return "\n".join(lines)


