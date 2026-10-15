"""
smc/levels.py
استخراج الدعم والمقاومة والمناطق الصالحة لكل إطار زمني على حدة.
"""

import pandas as pd

from smc.engine import analyze


def _collect_zones(df: pd.DataFrame) -> list:
    """جمع مناطق OB و FVG التي لم يُغلق السعر خلفها (غير ملغاة)."""
    df = df.reset_index(drop=True)
    closes = df["close"].values
    zones = []

    def add(mask, ztype, top_col, bottom_col, kind):
        for i in df.index[mask]:
            top = df.at[i, top_col]
            bottom = df.at[i, bottom_col]
            if pd.isna(top) or pd.isna(bottom):
                continue
            top, bottom = float(top), float(bottom)
            if top < bottom:
                top, bottom = bottom, top

            later = closes[i + 1:]
            if len(later):
                if ztype == "bullish" and later.min() < bottom:
                    continue
                if ztype == "bearish" and later.max() > top:
                    continue

            zones.append({
                "type": f"{ztype}_{kind}",
                "side": ztype,
                "top": top,
                "bottom": bottom,
                "start_idx": int(i),
                "start_time": str(df.at[i, "timestamp"]),
            })

    add(df["bullish_ob"].fillna(False).astype(bool), "bullish", "ob_high", "ob_low", "ob")
    add(df["bearish_ob"].fillna(False).astype(bool), "bearish", "ob_high", "ob_low", "ob")
    add(df["bullish_fvg"].fillna(False).astype(bool), "bullish", "fvg_top", "fvg_bottom", "fvg")
    add(df["bearish_fvg"].fillna(False).astype(bool), "bearish", "fvg_top", "fvg_bottom", "fvg")
    return zones


def extract_levels(df: pd.DataFrame, max_zones_per_side: int = 2) -> dict:
    """تحليل إطار زمني واحد وإرجاع مستوياته الخاصة."""
    df = analyze(df.reset_index(drop=True))
    price = float(df["close"].iloc[-1])

    zones = _collect_zones(df)

    def dist(z):
        if z["bottom"] <= price <= z["top"]:
            return 0.0
        return min(abs(z["bottom"] - price), abs(z["top"] - price))

    demand = sorted([z for z in zones if z["side"] == "bullish"], key=dist)[:max_zones_per_side]
    supply = sorted([z for z in zones if z["side"] == "bearish"], key=dist)[:max_zones_per_side]

    liq = df[(df["buy_liquidity"] | df["sell_liquidity"]) & (~df["liq_swept"])]
    bsl = [float(x) for x in liq.loc[liq["buy_liquidity"], "liq_level"] if x > price]
    ssl = [float(x) for x in liq.loc[liq["sell_liquidity"], "liq_level"] if x < price]

    res_candidates = list(bsl)
    for z in supply:
        if z["top"] > price:
            res_candidates.append(z["bottom"] if z["bottom"] > price else z["top"])

    sup_candidates = list(ssl)
    for z in demand:
        if z["bottom"] < price:
            sup_candidates.append(z["top"] if z["top"] < price else z["bottom"])

    res_candidates = [x for x in res_candidates if pd.notna(x)]
    sup_candidates = [x for x in sup_candidates if pd.notna(x)]

    return {
        "current_price": price,
        "last_timestamp": str(df["timestamp"].iloc[-1]),
        "trend": str(df["trend"].iloc[-1]),
        "nearest_resistance": round(min(res_candidates), 2) if res_candidates else None,
        "nearest_support": round(max(sup_candidates), 2) if sup_candidates else None,
        "zones": demand + supply,
    }