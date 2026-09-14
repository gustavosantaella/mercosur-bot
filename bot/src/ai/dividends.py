"""
BVC Dividends database and metadata for Bolsa de Valores de Caracas companies.
"""

BVC_DIVIDEND_INFO = {
    "BNC": {
        "pays_dividends": "Yes",
        "frequency": "Biannual / Annual",
        "type": "Cash and Stock Dividends",
        "details": "Decrees cash dividends and stock capitalizations following Shareholder Meetings."
    },
    "BVL": {
        "pays_dividends": "Yes",
        "frequency": "Biannual / Annual",
        "type": "Cash",
        "details": "Banco de Venezuela pays recurring cash dividends approved by the General Assembly."
    },
    "BPV": {
        "pays_dividends": "Yes",
        "frequency": "Annual / Biannual",
        "type": "Cash and Stock",
        "details": "BBVA Banco Provincial decrees cash payments distributed in multiple annual installments."
    },
    "MVZ.A": {
        "pays_dividends": "Yes",
        "frequency": "Quarterly / Biannual",
        "type": "Cash and Stock",
        "details": "Mercantil Servicios Financieros holds a highly consistent dividend history."
    },
    "MVZ.B": {
        "pays_dividends": "Yes",
        "frequency": "Quarterly / Biannual",
        "type": "Cash and Stock",
        "details": "Mercantil Servicios Financieros Class B carries equal dividend rights to Class A."
    },
    "ABC.A": {
        "pays_dividends": "Yes",
        "frequency": "Biannual / Annual",
        "type": "Cash and Stock",
        "details": "Bancaribe decrees periodic dividends approved in Shareholder Assemblies."
    },
    "RST": {
        "pays_dividends": "Yes",
        "frequency": "Annual / Biannual",
        "type": "Cash and Stock",
        "details": "Ron Santa Teresa pays mixed dividends (cash and capitalization bonus shares)."
    },
    "RST.B": {
        "pays_dividends": "Yes",
        "frequency": "Annual / Biannual",
        "type": "Cash and Stock",
        "details": "Ron Santa Teresa Class B participates equally in dividend decrees."
    },
    "BVCC": {
        "pays_dividends": "Yes",
        "frequency": "Annual",
        "type": "Cash and Stock",
        "details": "Bolsa de Valores de Caracas approves annual dividend distribution."
    },
    "ENV": {
        "pays_dividends": "Yes",
        "frequency": "Annual / Eventual",
        "type": "Cash",
        "details": "Envases Venezolanos distributes dividends based on fiscal performance."
    },
    "TDV.D": {
        "pays_dividends": "Yes",
        "frequency": "Annual / Eventual",
        "type": "Cash",
        "details": "CANTV Class D decrees dividends subject to free cash flow."
    },
    "PTN": {
        "pays_dividends": "Yes",
        "frequency": "Annual",
        "type": "Cash",
        "details": "Protinal distributes shareholder earnings at fiscal year close."
    },
    "SVS": {
        "pays_dividends": "Variable / Subject to Assembly",
        "frequency": "Eventual",
        "type": "Cash / Stock",
        "details": "Sivensa decrees dividends subject to industrial and operating performance."
    },
    "FVI.A": {
        "pays_dividends": "Yes",
        "frequency": "Annual",
        "type": "Cash and Stock",
        "details": "Fondo de Valores Inmobiliarios combines stock and cash dividend distributions."
    },
    "FVI.B": {
        "pays_dividends": "Yes",
        "frequency": "Annual",
        "type": "Cash and Stock",
        "details": "Fondo de Valores Inmobiliarios Class B participates in corporate dividend decrees."
    }
}

DEFAULT_DIVIDEND_INFO = {
    "pays_dividends": "Subject to Assembly",
    "frequency": "Annual / Eventual",
    "type": "Cash or Stock",
    "details": "Dividend payouts depend on approval during the issuer's Shareholder Assembly."
}

def get_dividend_info(symbol: str) -> dict:
    """
    Retrieves dividend policy metadata for a specific BVC stock symbol.
    """
    clean_sym = symbol.strip().upper() if symbol else ""
    return BVC_DIVIDEND_INFO.get(clean_sym, DEFAULT_DIVIDEND_INFO)

