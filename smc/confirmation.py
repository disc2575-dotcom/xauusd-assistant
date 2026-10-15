"""
smc/confirmation.py
كشف نماذج الشموع + تأكيد BOS.
"""

import pandas as pd
import numpy as np


# ============================================================
# نماذج الشموع
# ============================================================
def detect_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    """
    شمعة ابتلاعية صاعدة:
    - الشمعة السابقة هابطة.
    - الشمعة الحالية صاعدة.
    - تغلف جسم الشمعة السابقة.
    """
    prev = df.shift(1)

    body_curr = df["close"] - df["open"]
    body_prev = prev["open"] - prev["close"]

    return (
        (body_prev > 0) &  # السابقة هابطة
        (body_curr > 0) &  # الحالية صاعدة
        (df["open"] <= prev["close"]) &
        (df["close"] >= prev["open"])
    )


def detect_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    """شمعة ابتلاعية هابطة."""
    prev = df.shift(1)

    body_curr = df["open"] - df["close"]
    body_prev = prev["close"] - prev["open"]

    return (
        (body_prev > 0) &
        (body_curr > 0) &
        (df["open"] >= prev["close"]) &
        (df["close"] <= prev["open"])
    )


def detect_bullish_pin_bar(df: pd.DataFrame) -> pd.Series:
    """
    مطرقة صاعدة:
    - جسم صغير.
    - ذيل سفلي طويل (2x).
    - ذيل علوي قصير.
    """
    body = abs(df["close"] - df["open"])
    candle_range = df["high"] - df["low"]

    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]
    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)

    return (
        (candle_range > 0) &
        (df["close"] > df["open"]) &  # صاعدة
        (lower_wick >= body * 2) &
        (upper_wick <= body * 0.5)
    )


def detect_bearish_pin_bar(df: pd.DataFrame) -> pd.Series:
    """شهاب هابط."""
    body = abs(df["close"] - df["open"])
    candle_range = df["high"] - df["low"]

    upper_wick = df["high"] - df[["open", "close"]].max(axis=1)
    lower_wick = df[["open", "close"]].min(axis=1) - df["low"]

    return (
        (candle_range > 0) &
        (df["close"] < df["open"]) &  # هابطة
        (upper_wick >= body * 2) &
        (lower_wick <= body * 0.5)
    )


def detect_doji(df: pd.DataFrame, threshold: float = 0.1) -> pd.Series:
    """
    شمعة دوجي:
    - الجسم صغير جداً.
    - الظلال طويلة.
    """
    body = abs(df["close"] - df["open"])
    candle_range = df["high"] - df["low"]

    return (
        (candle_range > 0) &
        (body <= candle_range * threshold)
    )


# ============================================================
# BOS Confirmation
# ============================================================
def detect_bos_confirmation(df: pd.DataFrame) -> pd.DataFrame:
    """
    تأكيد BOS:
    - الشمعة الحالية كسرت BOS.
    - + نموذج شموع مطابق (Engulfing / Pin Bar).
    """
    df = df.copy()

    # إذا لم يكن هناك BOS، نُعيد DataFrame فارغاً
    if "bos" not in df.columns:
        df["bos_confirmed"] = False
        df["bos_confirmation_type"] = None
        return df

    # كشف النماذج
    bull_engulf = detect_bullish_engulfing(df)
    bear_engulf = detect_bearish_engulfing(df)
    bull_pin = detect_bullish_pin_bar(df)
    bear_pin = detect_bearish_pin_bar(df)

    # BOS صاعد
    bos_bull = (
        (df["bos"] == True) &
        (df.get("break_direction", "") == "bullish")
    )

    # BOS هابط
    bos_bear = (
        (df["bos"] == True) &
        (df.get("break_direction", "") == "bearish")
    )

    # تأكيد BOS صاعد
    bull_confirmation = bos_bull & (bull_engulf | bull_pin)

    # تأكيد BOS هابط
    bear_confirmation = bos_bear & (bear_engulf | bear_pin)

    df["bos_confirmed"] = bull_confirmation | bear_confirmation

    # نوع التأكيد
    confirmation_type = np.where(
        bull_confirmation & bull_engulf, "Bullish Engulfing",
        np.where(
            bull_confirmation & bull_pin, "Bullish Pin Bar",
            np.where(
                bear_confirmation & bear_engulf, "Bearish Engulfing",
                np.where(
                    bear_confirmation & bear_pin, "Bearish Pin Bar",
                    None
                )
            )
        )
    )
    df["bos_confirmation_type"] = confirmation_type

    return df


# ============================================================
# الواجهة الموحدة
# ============================================================
def detect_confirmation(df: pd.DataFrame) -> pd.DataFrame:
    """
    الواجهة الموحدة:
    - كشف نماذج الشموع.
    - + BOS Confirmation.
    """
    df = df.copy()

    # نماذج الشموع
    df["bullish_engulfing"] = detect_bullish_engulfing(df)
    df["bearish_engulfing"] = detect_bearish_engulfing(df)
    df["bullish_pin_bar"] = detect_bullish_pin_bar(df)
    df["bearish_pin_bar"] = detect_bearish_pin_bar(df)
    df["doji"] = detect_doji(df)

    # BOS Confirmation
    df = detect_bos_confirmation(df)

    return df
