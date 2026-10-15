"""
smc/structure.py
كشف BOS (Break of Structure) و CHOCH (Change of Character).
+ دعم break_direction (bullish/bearish).
"""

import pandas as pd
import numpy as np


def find_swing_points(
    df: pd.DataFrame,
    swing_left: int = 5,
    swing_right: int = 5,
) -> pd.DataFrame:
    """
    تحديد نقاط الانعكاس (Swing Highs و Swing Lows).
    """
    df = df.copy()
    df["swing_high"] = False
    df["swing_low"] = False

    highs = df["high"].values
    lows = df["low"].values

    for i in range(swing_left, len(df) - swing_right):
        # Swing High
        left_highs = highs[i - swing_left:i]
        right_highs = highs[i + 1:i + swing_right + 1]
        if (highs[i] > left_highs).all() and (highs[i] > right_highs).all():
            df.iloc[i, df.columns.get_loc("swing_high")] = True

        # Swing Low
        left_lows = lows[i - swing_left:i]
        right_lows = lows[i + 1:i + swing_right + 1]
        if (lows[i] < left_lows).all() and (lows[i] < right_lows).all():
            df.iloc[i, df.columns.get_loc("swing_low")] = True

    return df


def detect_bos_choch(
    df: pd.DataFrame,
    window: int = 10,
    swing_left: int = None,
    swing_right: int = None,
) -> pd.DataFrame:
    """
    كشف BOS و CHOCH.
    
    ✅ يدعم window + swing_left/swing_right.
    ✅ يُنتج break_direction (bullish/bearish).
    """
    # تحديد قيم swing
    if swing_left is None:
        swing_left = max(1, window // 2)
    if swing_right is None:
        swing_right = max(1, window // 2)

    out = find_swing_points(df, swing_left, swing_right)
    out["trend"] = "neutral"
    out["bos"] = False
    out["choch"] = False
    out["bos_choch_level"] = np.nan
    out["break_direction"] = None

    last_swing_high = None
    last_swing_low = None
    current_trend = "neutral"

    for i in range(len(out)):
        row = out.iloc[i]

        # تحديث آخر قمة وقاع
        if row["swing_high"]:
            last_swing_high = row["high"]
        if row["swing_low"]:
            last_swing_low = row["low"]

        # كشف BOS و CHOCH
        if last_swing_high is not None and last_swing_low is not None:
            close = row["close"]

            # كسر القمة (BOS صاعد أو CHOCH)
            if close > last_swing_high:
                if current_trend == "bullish":
                    out.iloc[i, out.columns.get_loc("bos")] = True
                    out.iloc[i, out.columns.get_loc("bos_choch_level")] = last_swing_high
                    out.iloc[i, out.columns.get_loc("break_direction")] = "bullish"
                else:
                    out.iloc[i, out.columns.get_loc("choch")] = True
                    out.iloc[i, out.columns.get_loc("bos_choch_level")] = last_swing_high
                    out.iloc[i, out.columns.get_loc("break_direction")] = "bullish"
                    current_trend = "bullish"

                last_swing_high = None

            # كسر القاع (BOS هابط أو CHOCH)
            elif close < last_swing_low:
                if current_trend == "bearish":
                    out.iloc[i, out.columns.get_loc("bos")] = True
                    out.iloc[i, out.columns.get_loc("bos_choch_level")] = last_swing_low
                    out.iloc[i, out.columns.get_loc("break_direction")] = "bearish"
                else:
                    out.iloc[i, out.columns.get_loc("choch")] = True
                    out.iloc[i, out.columns.get_loc("bos_choch_level")] = last_swing_low
                    out.iloc[i, out.columns.get_loc("break_direction")] = "bearish"
                    current_trend = "bearish"

                last_swing_low = None

        out.iloc[i, out.columns.get_loc("trend")] = current_trend

    return out
