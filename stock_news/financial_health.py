"""Normalize IndianAPI statement data for a small, factual financial overview.

The /stock financials CAS/BAL/INC amounts are INR crore; per-share values
are INR. keyMetrics monetary amounts use a different scale and are never
used in statement arithmetic. Only dimensionless ratios and per-share
metrics are read from keyMetrics.
"""

import math
import re
from datetime import date


def number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _fields(rows):
    return {_key(row.get("key")): number(row.get("value"))
            for row in rows if isinstance(row, dict)} if isinstance(rows, list) else {}


def _get(fields, *keys):
    return next((fields[_key(key)] for key in keys
                 if fields.get(_key(key)) is not None), None)


def _ratio(a, b, scale=1):
    if a is None or b is None or b <= 0:
        return None
    result = a / b * scale
    return result if math.isfinite(result) else None


def _annual_values(statement):
    maps = statement.get("stockFinancialMap") or {}
    if not isinstance(maps, dict):
        return {}
    inc, bal, cash = (_fields(maps.get(group)) for group in ("INC", "BAL", "CAS"))
    cash_period_length = _get(cash, "periodLength")
    if cash_period_length is not None and cash_period_length != 12:
        cash = {}
    revenue = _get(inc, "TotalRevenue", "Revenue")
    profit = _get(inc, "NetIncome")
    operating = _get(inc, "OperatingIncome")
    debt = _get(bal, "TotalDebt")
    # These are separate components in the provider's BAL statement.
    cash_amount, equivalents = _get(bal, "Cash"), _get(bal, "CashEquivalents")
    cash_total = cash_amount + equivalents if cash_amount is not None and equivalents is not None else None
    ocf, capex = _get(cash, "CashfromOperatingActivities"), _get(cash, "CapitalExpenditures")
    # The statement convention is a negative investing outflow. Positive
    # capital expenditures are ambiguous (e.g. proceeds): do not infer FCF.
    capex_outflow = -capex if capex is not None and capex <= 0 else None
    return {
        "revenue": revenue, "operating_profit": operating, "net_profit": profit,
        "eps": _get(inc, "DilutedEPSExcludingExtraOrdItems", "DilutedEPSExcludingExtraordinaryItems", "DilutedEPSIncludingExtraOrdItems"),
        "operating_margin": _ratio(operating, revenue, 100),
        "net_margin": _ratio(profit, revenue, 100),
        "debt": debt, "cash": cash_total,
        "net_debt": debt - cash_total if debt is not None and cash_total is not None else None,
        "debt_equity": _ratio(debt, _get(bal, "TotalEquity")),
        "ocf": ocf, "capex": capex_outflow,
        "fcf": ocf - capex_outflow if ocf is not None and capex_outflow is not None else None,
    }


GROUPS = (
    ("Growth", (("revenue", "Revenue", "₹ cr"), ("operating_profit", "Operating profit", "₹ cr"),
                ("net_profit", "Net profit", "₹ cr"), ("eps", "Diluted EPS", "₹"))),
    ("Profitability", (("operating_margin", "Operating margin", "%"), ("net_margin", "Net margin", "%"),
                       ("roe", "Return on equity", "%"), ("roa", "Return on assets", "%"))),
    ("Balance sheet", (("debt", "Total debt", "₹ cr"), ("cash", "Cash & equivalents", "₹ cr"),
                       ("net_debt", "Net debt", "₹ cr"), ("debt_equity", "Debt / equity", "×"),
                       ("interest_coverage", "Interest coverage", "×"))),
    ("Cash generation", (("ocf", "Operating cash flow", "₹ cr"), ("capex", "Capital expenditure", "₹ cr"),
                         ("fcf", "Free cash flow", "₹ cr"), ("cfps", "Cash flow / share", "₹"))),
)
METRIC_IDS = {item[0] for _, items in GROUPS for item in items}


def _metric_tones(metric, value, change, change_label):
    """Color comparable changes, without implying every increase is a gain."""
    tone = "neutral"
    if change_label in ("Returned to profit", "Loss narrowed"):
        tone = "positive"
    elif change_label in ("Turned to loss", "Loss widened"):
        tone = "negative"
    elif change is not None and change != 0:
        if metric in ("debt", "net_debt", "debt_equity"):
            tone = "caution" if change > 0 else "positive"
        elif metric in ("revenue", "operating_profit", "net_profit", "eps", "operating_margin",
                        "net_margin", "cash", "ocf", "fcf"):
            tone = "positive" if change > 0 else "negative"
        # Capital expenditure is investment, so its direction stays neutral.
    value_tone = tone
    if value < 0 and metric in ("operating_profit", "net_profit", "eps", "operating_margin", "net_margin", "ocf", "fcf"):
        value_tone = "negative"
    return tone, value_tone


def _sparkline(history):
    if len(history) < 3:
        return None
    values = [point["value"] for point in history]
    low, high = min(values), max(values)
    dates = [date.fromisoformat(point["period"]).toordinal() for point in history]
    return " ".join(f"{2 + (dates[i] - dates[0]) * 60 / (dates[-1] - dates[0]):.1f},{12 if high == low else 22 - (v - low) / (high - low) * 20:.1f}"
                    for i, v in enumerate(values))


def build_financial_health(payload):
    if not isinstance(payload, dict):
        return None
    statements = payload.get("financials")
    if not isinstance(statements, list):
        statements = []
    annual = {}
    for statement in statements:
        if not isinstance(statement, dict) or str(statement.get("Type", "")).lower() != "annual":
            continue
        try:
            end = date.fromisoformat(statement.get("EndDate", ""))
        except (ValueError, TypeError):
            continue
        if end > date.today():
            continue
        statement_map = statement.get("stockFinancialMap")
        if not isinstance(statement_map, dict):
            continue
        fields = statement_map.get("INC", [])
        length = _get(_fields(fields), "periodLength")
        if length is not None and length != 12:
            continue
        values = _annual_values(statement)
        if any(value is not None for value in values.values()):
            annual[end.isoformat()] = {"period": end.isoformat(), "label": f"FY{statement.get('FiscalYear') or end.year}", "values": values}
    years = sorted(annual.values(), key=lambda item: item["period"])[-5:]
    latest = years[-1] if years else {"label": "Latest FY", "period": "", "values": {}}
    metrics = dict(latest["values"])
    periods = {key: latest["label"] for key in metrics}
    key_metrics = payload.get("keyMetrics") or {}
    if not isinstance(key_metrics, dict):
        key_metrics = {}
    provider_ratios = {}
    for rows in key_metrics.values():
        provider_ratios.update(_fields(rows))
    for metric, ttm_key, annual_key in (
        ("roe", "returnOnAverageEquityTrailing12Month", "returnOnAverageEquityMostRecentFiscalYear"),
        ("roa", "returnOnAverageAssetsTrailing12Month", "returnOnAverageAssetsMostRecenFiscalYear"),
        ("interest_coverage", "netInterestCoverageTrailing12Month", "netInterestCoverageMostRecentFiscalYear"),
        ("cfps", "cashFlowPerShareTrailing12Month", "cashflowPerShareMostRecentFiscalYear"),
    ):
        value = _get(provider_ratios, ttm_key)
        metrics[metric] = value if value is not None else _get(provider_ratios, annual_key)
        periods[metric] = "TTM" if value is not None else latest["label"]
    industry = str(payload.get("industry") or "")[:120]
    financial = bool(re.search(r"bank|insurance|financial|consumer financ|investment servic|investment trust|capital market|lending|credit institution|asset management|brokerage|mortgage", industry, re.I))
    groups = []
    for title, definitions in GROUPS:
        if financial and title in ("Balance sheet", "Cash generation"):
            continue
        rows = []
        for metric, label, unit in definitions:
            if financial and metric in ("operating_profit", "operating_margin", "net_margin"):
                continue
            value = metrics.get(metric)
            if value is None:
                continue
            history = [{"period": year["period"], "value": year["values"][metric]}
                       for year in years if year["values"].get(metric) is not None]
            change, change_label = None, ""
            if len(years) > 1:
                previous = years[-2]["values"].get(metric)
                days = (date.fromisoformat(latest["period"]) - date.fromisoformat(years[-2]["period"])).days
                if previous is not None and 330 <= days <= 400:
                    if unit == "%":
                        change = value - previous
                        change_label = f"{change:+.1f} pp YoY"
                    elif previous > 0:
                        change = (value / previous - 1) * 100
                        change_label = f"{change:+.1f}% YoY" if title == "Growth" else f"{change:+.1f}% vs prior FY"
                    elif metric in ("net_profit", "operating_profit", "eps"):
                        change_label = "Returned to profit" if previous < 0 < value else "Loss widened" if value < previous < 0 else "Loss narrowed" if previous < value < 0 else ""
                    if metric in ("net_profit", "operating_profit", "eps") and previous > 0 and value < 0:
                        change_label = "Turned to loss"
            change_tone, value_tone = _metric_tones(metric, value, change, change_label)
            rows.append({"id": metric, "label": label, "value": value, "unit": unit,
                         "change_tone": change_tone, "value_tone": value_tone,
                         "period": periods[metric], "history": history, "change": change,
                         "change_label": change_label,
                         "sparkline": _sparkline(history) if metric in ("operating_margin", "net_margin", "debt", "ocf", "fcf") else None,
                         "display": f"{value:,.0f}" if unit == "₹ cr" else f"{value:,.2f}"})
        if rows:
            groups.append({"title": title, "metrics": rows})
    if not groups:
        return None
    comparisons = {}
    if not financial and metrics.get("ocf") is not None and metrics.get("capex") is not None:
        comparisons["operating_cash_flow_covers_capex"] = metrics["ocf"] >= metrics["capex"]
    return {"period": latest["label"], "end_date": latest["period"], "industry": industry,
            "financial_institution": financial, "groups": groups,
            "comparisons": comparisons,
            "note": "Bank-specific capital and asset-quality measures are not covered." if financial else "Free cash flow = operating cash flow less capital expenditure. Net debt excludes short-term investments."}
