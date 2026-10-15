"""
smc/patterns.py
كشف النماذج السعرية الكلاسيكية:
- Head & Shoulders (انعكاس هبوطي)
- Inverse Head & Shoulders (انعكاس صاعد)
- Double Top (انعكاس هبوطي)
- Double Bottom (انعكاس صاعد)
"""

import pandas as pd
import numpy as np


# ============================================================
# Head & Shoulders
# ============================================================
def detect_head_and_shoulders(
    df: pd.DataFrame,
    tolerance: float = 0.05,
) -> pd.Series:
    """
    كشف Head & Shoulders:
    - 3 قمم متتالية: LS < Head > RS.
    - LS ≈ RS (فرق < tolerance).
    - Head أعلى من الاثنين.
    """
    result = pd.Series([False] * len(df), index=df.index)

    if "swing_high" not in df.columns:
        return result

    swing_highs = df[df["swing_high"] == True]

    if len(swing_highs) < 3:
        return result

    indices = swing_highs.index.tolist()
    highs = swing_highs["high"].tolist()

    for i in range(2, len(indices)):
        ls = highs[i - 2]
        head = highs[i - 1]
        rs = highs[i]

        # الشروط
        if (head > ls * (1 + tolerance) and
            head > rs * (1 + tolerance) and
            abs(ls - rs) / ls < tolerance):
            result.iloc[indices[i]] = True

    return result


# ============================================================
# Inverse Head & Shoulders
# ============================================================
def detect_inverse_head_and_shoulders(
    df: pd.DataFrame,
    tolerance: float = 0.05,
) -> pd.Series:
    """
    كشف Inverse Head & Shoulders:
    - 3 قيعان متتالية: LS > Head < RS.
    - LS ≈ RS.
    - Head أقل من الاثنين.
    """
    result = pd.Series([False] * len(df), index=df.index)

    if "swing_low" not in df.columns:
        return result

    swing_lows = df[df["swing_low"] == True]

    if len(swing_lows) < 3:
        return result

    indices = swing_lows.index.tolist()
    lows = swing_lows["low"].tolist()

    for i in range(2, len(indices)):
        ls = lows[i - 2]
        head = lows[i - 1]
        rs = lows[i]

        if (head < ls * (1 - tolerance) and
            head < rs * (1 - tolerance) and
            abs(ls - rs) / ls < tolerance):
            result.iloc[indices[i]] = True

    return result


# ============================================================
# Double Top
# ============================================================
def detect_double_top(
    df: pd.DataFrame,
    tolerance: float = 0.02,
    min_bars_between: int = 5,
) -> pd.Series:
    """
    كشف Double Top:
    - قمتان متتاليتان متساويتان تقريباً.
    - الفرق < tolerance.
    - بينهما على الأقل min_bars_between.
    """
    result = pd.Series([False] * len(df), index=df.index)

    if "swing_high" not in df.columns:
        return result

    swing_highs = df[df["swing_high"] == True]

    if len(swing_highs) < 2:
        return result

    indices = swing_highs.index.tolist()
    highs = swing_highs["high"].tolist()

    for i in range(1, len(indices)):
        h1 = highs[i - 1]
        h2 = highs[i]

        # الشروط
        if (abs(h1 - h2) / h1 < tolerance and
            (indices[i] - indices[i - 1]) >= min_bars_between):
            result.iloc[indices[i]] = True

    return result


# ============================================================
# Double Bottom
# ============================================================
def detect_double_bottom(
    df: pd.DataFrame,
    tolerance: float = 0.02,
    min_bars_between: int = 5,
) -> pd.Series:
    """
    كشف Double Bottom:
    - قاعان متتاليان متساويان تقريباً.
    - الفرق < tolerance.
    - بينهما على الأقل min_bars_between.
    """
    result = pd.Series([False] * len(df), index=df.index)

    if "swing_low" not in df.columns:
        return result

    swing_lows = df[df["swing_low"] == True]

    if len(swing_lows) < 2:
        return result

    indices = swing_lows.index.tolist()
    lows = swing_lows["low"].tolist()

    for i in range(1, len(indices)):
        l1 = lows[i - 1]
        l2 = lows[i]

        if (abs(l1 - l2) / l1 < tolerance and
            (indices[i] - indices[i - 1]) >= min_bars_between):
            result.iloc[indices[i]] = True

    return result


# ============================================================
# الواجهة الموحدة
# ============================================================
def detect_patterns(
    df: pd.DataFrame,
    hs_tolerance: float = 0.05,
    dt_tolerance: float = 0.02,
) -> pd.DataFrame:
    """
    كشف كل النماذج السعرية.
    
    الإرجاع:
        DataFrame مع الأعمدة:
        - head_and_shoulders
        - inverse_head_and_shoulders
        - double_top
        - double_bottom
    """
    df = df.copy()

    df["head_and_shoulders"] = detect_head_and_shoulders(df, hs_tolerance)
    df["inverse_head_and_shoulders"] = detect_inverse_head_and_shoulders(df, hs_tolerance)
    df["double_top"] = detect_double_top(df, dt_tolerance)
    df["double_bottom"] = detect_double_bottom(df, dt_tolerance)

    return df


def extract_patterns(df: pd.DataFrame, limit: int = 10) -> list:
    """
    استخراج آخر النماذج السعرية.
    """
    if df is None or df.empty:
        return []

    patterns = []
    last_rows = df.tail(200)

    for _, row in last_rows.iterrows():
        ts = str(row.get("timestamp", ""))

        if row.get("head_and_shoulders", False):
            patterns.append({
                "type": "head_and_shoulders",
                "label": "Head & Shoulders (انعكاس هبوطي)",
                "timestamp": ts,
            })

        if row.get("inverse_head_and_shoulders", False):
            patterns.append({
                "type": "inverse_head_and_shoulders",
                "label": "Inverse Head & Shoulders (انعكاس صاعد)",
                "timestamp": ts,
            })

        if row.get("double_top", False):
            patterns.append({
                "type": "double_top",
                "label": "Double Top (انعكاس هبوطي)",
                "timestamp": ts,
            })

        if row.get("double_bottom", False):
            patterns.append({
                "type": "double_bottom",
                "label": "Double Bottom (انعكاس صاعد)",
                "timestamp": ts,
            })

    return patterns[-limit:]


# ============================================================
# اختبار
# ============================================================
if __name__ == "__main__":
    import sqlite3
    from core.config import DB_PATH, SYMBOL_DB

    print("📊 اختبار patterns.py")
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql(
        f'SELECT * FROM (SELECT * FROM "{SYMBOL_DB}_H1" ORDER BY timestamp DESC LIMIT 1000) ORDER BY timestamp ASC',
        conn, parse_dates=["timestamp"],
    )
    conn.close()

    # نحتاج swing_high/low أولاً
    from smc.structure import detect_bos_choch
    df = detect_bos_choch(df, window=10)

    result = detect_patterns(df)

    print(f"عدد الشموع: {len(df)}")
    print("\nالنماذج المكتشفة:")
    print(f"  Head & Shoulders:         {result['head_and_shoulders'].sum()}")
    print(f"  Inverse H&S:              {result['inverse_head_and_shoulders'].sum()}")
    print(f"  Double Top:               {result['double_top'].sum()}")
    print(f"  Double Bottom:            {result['double_bottom'].sum()}")

    print("\nآخر 5 نماذج:")
    patterns = extract_patterns(result)
    for p in patterns[-5:]:
        print(f"  • {p['label']} — {p['timestamp'][:16]}")
