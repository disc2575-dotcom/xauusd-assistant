"""
smc/engine.py
محرك SMC الموحد — يدمج:
- BOS/CHOCH
- Order Blocks
- FVG
- Liquidity
- Confirmation (نماذج الشموع + BOS Confirmed)
- Patterns (النماذج السعرية)

يوفّر:
- analyze: التحليل الشامل
- summarize: ملخص كامل (متوافق مع signal_generator)
- count_signals: إحصائيات سريعة
- get_last_trend / get_last_price: دوال مساعدة
"""

import pandas as pd
import numpy as np

from smc.structure import detect_bos_choch
from smc.order_blocks import detect_order_blocks
from smc.fvg import detect_fvg
from smc.liquidity import detect_liquidity
from smc.confirmation import detect_confirmation
from smc.patterns import detect_patterns


# ============================================================
# التحليل الشامل
# ============================================================
def analyze(
    df: pd.DataFrame,
    window: int = 10,
    fvg_min_pct: float = 0.2,
    ob_window: int = 5,
    liq_window: int = 10,
) -> pd.DataFrame:
    """
    التحليل الشامل لبيانات OHLCV.

    المعاملات:
        df: DataFrame يحتوي على OHLCV.
        window: نافذة BOS/CHOCH.
        fvg_min_pct: الحد الأدنى لحجم FVG (%).
        ob_window: نافذة Order Blocks.
        liq_window: نافذة Liquidity.

    الإرجاع:
        DataFrame مع كل التحليلات.
    """
    if df is None or df.empty:
        return df

    # 1. BOS/CHOCH
    try:
        df = detect_bos_choch(df, window=window)
    except TypeError:
        df = detect_bos_choch(df)

    # 2. Order Blocks
    try:
        df = detect_order_blocks(df, window=ob_window)
    except TypeError:
        df = detect_order_blocks(df)

    # 3. FVG
    try:
        df = detect_fvg(df, min_size_ratio=fvg_min_pct / 100)
    except TypeError:
        try:
            df = detect_fvg(df)
        except Exception:
            pass

    # 4. Liquidity
    try:
        df = detect_liquidity(df, window=liq_window)
    except TypeError:
        df = detect_liquidity(df)

    # 5. Confirmation (نماذج الشموع + تأكيد BOS)
    try:
        df = detect_confirmation(df)
    except Exception as e:
        print(f"⚠️ فشل detect_confirmation: {e}")

    # 6. Patterns (النماذج السعرية)
    try:
        df = detect_patterns(df)
    except Exception as e:
        print(f"⚠️ فشل detect_patterns: {e}")

    return df


# ============================================================
# ملخص كامل (متوافق مع signal_generator و run_day2)
# ============================================================
def summarize(df: pd.DataFrame) -> dict:
    """
    استخراج ملخص آخر حالة من DataFrame.

    البنية المُرجَعة متوافقة مع ما يتوقعه signal_generator.py
    من snapshot (current_trend, last_close, totals, events, ...).

    الإرجاع:
        {
            "current_trend": str,
            "last_close": float,
            "last_timestamp": str,
            "totals": {"events": int, "fvgs": int, "order_blocks": int, "liquidity": int},
            "events": [...],       # آخر 5
            "fvgs": [...],         # آخر 5
            "order_blocks": [...], # آخر 5
            "liquidity": [...],    # آخر 5
        }
    """
    if df is None or df.empty:
        return {"error": "empty_dataframe"}

    last = df.iloc[-1]

    # ---------- أعمدة موجودة؟ ----------
    has_bos = "bos" in df.columns
    has_choch = "choch" in df.columns
    has_bull_fvg = "bullish_fvg" in df.columns
    has_bear_fvg = "bearish_fvg" in df.columns
    has_bull_ob = "bullish_ob" in df.columns
    has_bear_ob = "bearish_ob" in df.columns
    has_buy_liq = "buy_liquidity" in df.columns
    has_sell_liq = "sell_liquidity" in df.columns

    # ---------- الأعداد الكلية ----------
    total_events = 0
    if has_bos or has_choch:
        mask = pd.Series(False, index=df.index)
        if has_bos:
            mask = mask | df["bos"].fillna(False)
        if has_choch:
            mask = mask | df["choch"].fillna(False)
        total_events = int(mask.sum())

    total_fvgs = 0
    if has_bull_fvg or has_bear_fvg:
        mask = pd.Series(False, index=df.index)
        if has_bull_fvg:
            mask = mask | df["bullish_fvg"].fillna(False)
        if has_bear_fvg:
            mask = mask | df["bearish_fvg"].fillna(False)
        total_fvgs = int(mask.sum())

    total_obs = 0
    if has_bull_ob or has_bear_ob:
        mask = pd.Series(False, index=df.index)
        if has_bull_ob:
            mask = mask | df["bullish_ob"].fillna(False)
        if has_bear_ob:
            mask = mask | df["bearish_ob"].fillna(False)
        total_obs = int(mask.sum())

    total_liqs = 0
    if has_buy_liq or has_sell_liq:
        mask = pd.Series(False, index=df.index)
        if has_buy_liq:
            mask = mask | df["buy_liquidity"].fillna(False)
        if has_sell_liq:
            mask = mask | df["sell_liquidity"].fillna(False)
        total_liqs = int(mask.sum())

    # ---------- آخر 5 أحداث BOS/CHOCH ----------
    events_list = []
    if has_bos or has_choch:
        mask = pd.Series(False, index=df.index)
        if has_bos:
            mask = mask | df["bos"].fillna(False)
        if has_choch:
            mask = mask | df["choch"].fillna(False)
        events = df[mask].tail(5)
        for _, row in events.iterrows():
            direction = "unknown"
            if "break_direction" in df.columns and pd.notna(row.get("break_direction")):
                direction = str(row["break_direction"])
            level = None
            if "bos_choch_level" in df.columns and pd.notna(row.get("bos_choch_level")):
                level = float(row["bos_choch_level"])
            events_list.append({
                "timestamp": str(row["timestamp"]),
                "type": "CHOCH" if row.get("choch", False) else "BOS",
                "direction": direction,
                "level": level,
            })

    # ---------- آخر 5 FVG ----------
    fvgs_list = []
    if has_bull_fvg or has_bear_fvg:
        mask = pd.Series(False, index=df.index)
        if has_bull_fvg:
            mask = mask | df["bullish_fvg"].fillna(False)
        if has_bear_fvg:
            mask = mask | df["bearish_fvg"].fillna(False)
        fvgs = df[mask].tail(5)
        for _, row in fvgs.iterrows():
            top = float(row["fvg_top"]) if "fvg_top" in df.columns and pd.notna(row.get("fvg_top")) else None
            bottom = float(row["fvg_bottom"]) if "fvg_bottom" in df.columns and pd.notna(row.get("fvg_bottom")) else None
            size = float(row["fvg_size"]) if "fvg_size" in df.columns and pd.notna(row.get("fvg_size")) else None
            fvgs_list.append({
                "timestamp": str(row["timestamp"]),
                "type": "bullish" if row.get("bullish_fvg", False) else "bearish",
                "top": top,
                "bottom": bottom,
                "size": size,
            })

    # ---------- آخر 5 Order Blocks (الصالحة فقط إن وُجد ob_valid) ----------
    obs_list = []
    if has_bull_ob or has_bear_ob:
        mask = pd.Series(False, index=df.index)
        if has_bull_ob:
            mask = mask | df["bullish_ob"].fillna(False)
        if has_bear_ob:
            mask = mask | df["bearish_ob"].fillna(False)
        if "ob_valid" in df.columns:
            mask = mask & df["ob_valid"].fillna(False)
        obs = df[mask].tail(5)
        for _, row in obs.iterrows():
            top = float(row["ob_high"]) if "ob_high" in df.columns and pd.notna(row.get("ob_high")) else None
            bottom = float(row["ob_low"]) if "ob_low" in df.columns and pd.notna(row.get("ob_low")) else None
            obs_list.append({
                "timestamp": str(row["timestamp"]),
                "type": "bullish_ob" if row.get("bullish_ob", False) else "bearish_ob",
                "top": top,
                "bottom": bottom,
            })

    # ---------- آخر 5 مناطق سيولة (غير الممسوحة) ----------
    liqs_list = []
    if has_buy_liq or has_sell_liq:
        mask = pd.Series(False, index=df.index)
        if has_buy_liq:
            mask = mask | df["buy_liquidity"].fillna(False)
        if has_sell_liq:
            mask = mask | df["sell_liquidity"].fillna(False)
        if "liq_swept" in df.columns:
            mask = mask & (~df["liq_swept"].fillna(False))
        liqs = df[mask].tail(5)
        for _, row in liqs.iterrows():
            level = float(row["liq_level"]) if "liq_level" in df.columns and pd.notna(row.get("liq_level")) else None
            liqs_list.append({
                "timestamp": str(row["timestamp"]),
                "type": "buy_side" if row.get("buy_liquidity", False) else "sell_side",
                "level": level,
            })

    # ---------- البنية النهائية ----------
    return {
        "current_trend": str(last.get("trend", "neutral")),
        "last_close": float(last["close"]),
        "last_timestamp": str(last["timestamp"]),
        "totals": {
            "events": total_events,
            "fvgs": total_fvgs,
            "order_blocks": total_obs,
            "liquidity": total_liqs,
        },
        "events": events_list,
        "fvgs": fvgs_list,
        "order_blocks": obs_list,
        "liquidity": liqs_list,
    }


# ============================================================
# دوال مساعدة
# ============================================================
def get_last_trend(df: pd.DataFrame) -> str:
    """الحصول على آخر اتجاه."""
    if df is None or df.empty:
        return "neutral"

    if "trend" in df.columns:
        return df.iloc[-1].get("trend", "neutral")

    return "neutral"


def get_last_price(df: pd.DataFrame) -> float:
    """الحصول على آخر سعر."""
    if df is None or df.empty:
        return 0.0

    return float(df.iloc[-1]["close"])


def count_signals(df: pd.DataFrame) -> dict:
    """إحصائيات الإشارات (سريعة، دون تفاصيل)."""
    if df is None or df.empty:
        return {
            "bos": 0,
            "choch": 0,
            "bullish_ob": 0,
            "bearish_ob": 0,
            "bullish_fvg": 0,
            "bearish_fvg": 0,
            "bullish_engulfing": 0,
            "bearish_engulfing": 0,
            "bullish_pin_bar": 0,
            "bearish_pin_bar": 0,
            "bos_confirmed": 0,
            "head_and_shoulders": 0,
            "inverse_head_and_shoulders": 0,
            "double_top": 0,
            "double_bottom": 0,
        }

    def safe_sum(col):
        if col in df.columns:
            return int(df[col].fillna(False).sum())
        return 0

    return {
        "bos": safe_sum("bos"),
        "choch": safe_sum("choch"),
        "bullish_ob": safe_sum("bullish_ob"),
        "bearish_ob": safe_sum("bearish_ob"),
        "bullish_fvg": safe_sum("bullish_fvg"),
        "bearish_fvg": safe_sum("bearish_fvg"),
        "bullish_engulfing": safe_sum("bullish_engulfing"),
        "bearish_engulfing": safe_sum("bearish_engulfing"),
        "bullish_pin_bar": safe_sum("bullish_pin_bar"),
        "bearish_pin_bar": safe_sum("bearish_pin_bar"),
        "bos_confirmed": safe_sum("bos_confirmed"),
        "head_and_shoulders": safe_sum("head_and_shoulders"),
        "inverse_head_and_shoulders": safe_sum("inverse_head_and_shoulders"),
        "double_top": safe_sum("double_top"),
        "double_bottom": safe_sum("double_bottom"),
    }


# ============================================================
# اختبار
# ============================================================
if __name__ == "__main__":
    import sqlite3
    from core.config import DB_PATH, SYMBOL_DB

    print("📊 اختبار engine.py")
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql(
        f'SELECT * FROM (SELECT * FROM "{SYMBOL_DB}_H1" ORDER BY timestamp DESC LIMIT 1000) ORDER BY timestamp ASC',
        conn, parse_dates=["timestamp"],
    )
    conn.close()

    print(f"عدد الشموع: {len(df)}")
    result = analyze(df)

    print("\nالأعمدة الجديدة:")
    new_cols = [
        "bullish_engulfing", "bearish_engulfing",
        "bullish_pin_bar", "bearish_pin_bar",
        "doji", "bos_confirmed", "bos_confirmation_type",
        "head_and_shoulders", "inverse_head_and_shoulders",
        "double_top", "double_bottom",
    ]
    for col in new_cols:
        status = "✅" if col in result.columns else "❌"
        print(f"  {status} {col}")

    print("\nالإحصائيات (count_signals):")
    stats = count_signals(result)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\nالملخص (summarize):")
    summary = summarize(result)
    if "error" in summary:
        print(f"  ⚠️ {summary['error']}")
    else:
        print(f"  الاتجاه: {summary['current_trend']}")
        print(f"  آخر إغلاق: {summary['last_close']}")
        print(f"  Totals: {summary['totals']}")
        print(f"  عدد الأحداث (آخر 5): {len(summary['events'])}")
        print(f"  عدد FVGs (آخر 5): {len(summary['fvgs'])}")
        print(f"  عدد OBs (آخر 5): {len(summary['order_blocks'])}")
        print(f"  عدد Liqs (آخر 5): {len(summary['liquidity'])}")