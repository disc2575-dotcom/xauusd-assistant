"""
smc/levels.py
استخراج الدعم والمقاومة والمناطق الصالحة لكل إطار زمني على حدة.

التحسينات:
- إضافة Swing Highs/Lows (القمم/القيعان التاريخية) كمصدر إضافي للمستويات.
- هذا يحل مشكلة عدم ظهور القمم المهمة (مثل قمة الهبوط الكبيرة) التي
  ليست Order Blocks ولكنها مستويات مهمة.
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


def _collect_swing_levels(df: pd.DataFrame, n: int = 5) -> dict:
    """
    استخراج آخر n قمم وقيعان تاريخية (Swing Highs/Lows).

    Swing High = قمة محلية (is_swing_high=True في structure.py).
    هذه تُستخدم كمصدر إضافي للمقاومة (عندما لا توجد OB/FVG قريبة).

    Returns:
        {"highs": [...], "lows": [...]}
    """
    highs = []
    lows = []

    # نحتاج أعمدة is_swing_high و is_swing_low (تأتي من analyze → detect_swings)
    if "is_swing_high" in df.columns:
        swing_highs = df[df["is_swing_high"]].tail(n)
        for idx, row in swing_highs.iterrows():
            highs.append({
                "type": "swing_high",
                "side": "bearish",
                "level": float(row["high"]),
                "timestamp": str(row["timestamp"]),
                "index": int(idx),
            })

    if "is_swing_low" in df.columns:
        swing_lows = df[df["is_swing_low"]].tail(n)
        for idx, row in swing_lows.iterrows():
            lows.append({
                "type": "swing_low",
                "side": "bullish",
                "level": float(row["low"]),
                "timestamp": str(row["timestamp"]),
                "index": int(idx),
            })

    return {"highs": highs, "lows": lows}


def extract_levels(df: pd.DataFrame, max_zones_per_side: int = 2) -> dict:
    """
    تحليل إطار زمني واحد وإرجاع مستوياته الخاصة.

    df: أعمدة timestamp, open, high, low, close (ترتيب زمني تصاعدي).
    """
    df = analyze(df.reset_index(drop=True))
    price = float(df["close"].iloc[-1])

    zones = _collect_zones(df)
    swing_levels = _collect_swing_levels(df, n=5)

    def dist(z):
        if z["bottom"] <= price <= z["top"]:
            return 0.0
        return min(abs(z["bottom"] - price), abs(z["top"] - price))

    demand = sorted([z for z in zones if z["side"] == "bullish"], key=dist)[:max_zones_per_side]
    supply = sorted([z for z in zones if z["side"] == "bearish"], key=dist)[:max_zones_per_side]

    # السيولة غير الممسوحة فقط
    liq = df[(df["buy_liquidity"] | df["sell_liquidity"]) & (~df["liq_swept"])]
    bsl = [float(x) for x in liq.loc[liq["buy_liquidity"], "liq_level"] if x > price]
    ssl = [float(x) for x in liq.loc[liq["sell_liquidity"], "liq_level"] if x < price]

    # ============ مرشحات المقاومة ============
    res_candidates = list(bsl)

    # من Order Blocks/FVG
    for z in supply:
        if z["top"] > price:
            res_candidates.append(z["bottom"] if z["bottom"] > price else z["top"])

    # من Swing Highs (الجديد)
    for sh in swing_levels["highs"]:
        if sh["level"] > price:
            res_candidates.append(sh["level"])

    # ============ مرشحات الدعم ============
    sup_candidates = list(ssl)

    # من Order Blocks/FVG
    for z in demand:
        if z["bottom"] < price:
            sup_candidates.append(z["top"] if z["top"] < price else z["bottom"])

    # من Swing Lows (الجديد)
    for sl in swing_levels["lows"]:
        if sl["level"] < price:
            sup_candidates.append(sl["level"])

    # فلترة NaN
    res_candidates = [x for x in res_candidates if pd.notna(x)]
    sup_candidates = [x for x in sup_candidates if pd.notna(x)]

    return {
        "current_price": price,
        "last_timestamp": str(df["timestamp"].iloc[-1]),
        "trend": str(df["trend"].iloc[-1]),
        "nearest_resistance": round(min(res_candidates), 2) if res_candidates else None,
        "nearest_support": round(max(sup_candidates), 2) if sup_candidates else None,
        "zones": demand + supply,
        "swing_highs": swing_levels["highs"],
        "swing_lows": swing_levels["lows"],
    }