"""
smc/engine.py
محرك SMC الموحد — يدمج:
- BOS/CHOCH
- Order Blocks
- FVG
- Liquidity
- Confirmation (نماذج الشموع + BOS Confirmed)
- Patterns (النماذج السعرية)
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
    """إحصائيات الإشارات."""
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

    print("\nالإحصائيات:")
    stats = count_signals(result)
    for key, value in stats.items():
        print(f"  {key}: {value}")
