"""
core/data_updater.py
تحديث البيانات من TwelveData.
+ إصلاح: تحديث القيم الموجودة (keep="last")
"""

import os
import time
import sqlite3
import requests
import pandas as pd
from dotenv import load_dotenv

from core.config import (
    DB_PATH, SYMBOL_TWELVEDATA, SYMBOL_DB,
    BARS_PER_TIMEFRAME, TIMEFRAMES,
)

load_dotenv()

TWELVEDATA_TF_MAP = {
    "D1": "1day",
    "H4": "4h",
    "H1": "1h",
    "M30": "30min",
    "M15": "15min",
    "M5": "5min",
}


def fetch_latest(timeframe: str, bars: int = None) -> pd.DataFrame:
    """جلب أحدث البيانات من TwelveData."""
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        raise ValueError("❌ TWELVEDATA_API_KEY غير موجود")

    if bars is None:
        bars = BARS_PER_TIMEFRAME[timeframe]

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL_TWELVEDATA,
        "interval": TWELVEDATA_TF_MAP[timeframe],
        "outputsize": bars,
        "apikey": api_key,
        "timezone": "UTC",
    }

    r = requests.get(url, params=params, timeout=60)
    data = r.json()

    if "values" not in data:
        raise ValueError(f"❌ خطأ: {data.get('message', data)}")

    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    df["volume"] = df["volume"].astype(float) if "volume" in df.columns else 0.0

    return df.sort_values("timestamp").reset_index(drop=True)[
        ["timestamp", "open", "high", "low", "close", "volume"]
    ]


def update_table(timeframe: str, new_df: pd.DataFrame):
    """
    دمج البيانات الجديدة مع الموجودة.
    ✅ الإصلاح: تحديث القيم الموجودة (keep="last")
    """
    table_name = f"{SYMBOL_DB}_{timeframe}"
    conn = sqlite3.connect(str(DB_PATH))

    try:
        # قراءة البيانات الموجودة
        existing = pd.read_sql(
            f'SELECT * FROM "{table_name}"',
            conn,
            parse_dates=["timestamp"],
        )

        # ✅ إزالة الصفوف القديمة التي ستُحدَّث
        existing_filtered = existing[
            ~existing["timestamp"].isin(new_df["timestamp"])
        ]

        # ✅ دمج الجديد + القديم (بدون تكرار)
        combined = pd.concat([existing_filtered, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset="timestamp", keep="last")
        combined = combined.sort_values("timestamp").reset_index(drop=True)

        # حفظ
        combined.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.execute(
            f'CREATE INDEX IF NOT EXISTS idx_{table_name}_ts ON "{table_name}"(timestamp)'
        )
        conn.commit()

        # حساب الصفوف الجديدة
        new_timestamps = set(new_df["timestamp"]) - set(existing["timestamp"])
        new_rows = len(new_timestamps)

        return new_rows, len(combined)
    finally:
        conn.close()


def update_all_timeframes():
    """تحديث جميع الأطر الزمنية."""
    print("=" * 60)
    print("🔄 تحديث market.db")
    print("=" * 60)

    for tf in TIMEFRAMES:
        try:
            print(f"\n📊 {tf}...")
            new_df = fetch_latest(tf)
            new_rows, total = update_table(tf, new_df)
            print(f"   ✅ {new_rows} صف جديد | المجموع: {total}")
            time.sleep(8)
        except Exception as e:
            print(f"   ⚠️ {tf}: {e}")

    print("\n" + "=" * 60)
    print("✅ انتهى التحديث")
    print("=" * 60)


if __name__ == "__main__":
    update_all_timeframes()
