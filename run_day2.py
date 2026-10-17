"""
run_day2.py
تشغيل تحليل SMC الكامل على كل الأطر الزمنية وحفظ النتائج.

يشمل:
1. تحليل كل إطار (analyze) + ملخص (summarize) → smc_snapshot.json
2. توليد الإشارة العامة (generate_signal) → signal.json
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

from core.config import SYMBOL_DB as SYMBOL, TIMEFRAMES, DB_PATH
from smc.engine import analyze, summarize
from smc.signal_generator import generate_signal


def load_from_db(symbol: str, timeframe: str, db_path) -> pd.DataFrame:
    """تحميل الشموع لإطار زمني واحد من قاعدة البيانات."""
    table = f"{symbol}_{timeframe}"
    conn = sqlite3.connect(str(db_path))
    try:
        df = pd.read_sql(
            f'SELECT * FROM "{table}" ORDER BY timestamp ASC',
            conn,
            parse_dates=["timestamp"],
        )
    finally:
        conn.close()
    return df


def main():
    results = {}

    # ============================================
    # 1) تحليل كل إطار زمني
    # ============================================
    for tf in TIMEFRAMES:
        print(f"--- {tf} ---")
        try:
            df = load_from_db(SYMBOL, tf, DB_PATH)

            if df.empty:
                print(f"⚠️ لا توجد بيانات لـ {tf}\n")
                results[tf] = {"error": "empty_table"}
                continue

            # التحليل الكامل
            df = analyze(df)

            # ملخص
            summary = summarize(df)
            results[tf] = summary

            print(f"  الاتجاه الحالي : {summary['current_trend']}")
            print(f"  آخر إغلاق      : {summary['last_close']:.2f}")
            print(f"  أحداث BOS/CHOCH: {len(summary['events'])}")
            print(f"  FVG نشطة       : {len(summary['fvgs'])}")
            print(f"  Order Blocks   : {len(summary['order_blocks'])}")
            print(f"  مناطق سيولة    : {len(summary['liquidity'])}")
            print()

        except Exception as e:
            print(f"❌ خطأ في {tf}: {e}\n")
            results[tf] = {"error": str(e)}

    # ============================================
    # 2) حفظ Snapshot التحليل
    # ============================================
    out_path = Path("data/smc_snapshot.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"✅ تم حفظ النتائج في {out_path}")

    # ============================================
    # 3) توليد الإشارة العامة (Signal)
    # ============================================
    try:
        signal = generate_signal(results)

        signal_path = Path("data/signal.json")
        with open(signal_path, "w", encoding="utf-8") as f:
            json.dump(signal, f, indent=2, ensure_ascii=False, default=str)

        print()
        print("=" * 60)
        print("📊 الإشارة العامة:")
        print("=" * 60)
        print(f"  الإشارة   : {signal.get('signal', 'N/A')}")
        print(f"  الثقة     : {signal.get('confidence', 0)}%")
        print(f"  الاتجاه   : {signal.get('bias', 'N/A')}")
        print(f"  Score     : {signal.get('bias_score', 0)}")
        print(f"  الأطر     : {signal.get('valid_timeframes', 0)} صالحة")
        print(f"  حفظ في    : {signal_path}")
        print("=" * 60)

        # عرض التحذيرات إن وجدت
        warnings = signal.get("warnings", [])
        if warnings:
            print("⚠️ التحذيرات:")
            for w in warnings:
                print(f"  - {w}")

        # عرض المستويات
        levels = signal.get("levels", {})
        if levels:
            print("📈 المستويات:")
            print(f"  السعر الحالي : {levels.get('current_price', 'N/A')}")
            print(f"  دخول         : {levels.get('entry', 'N/A')}")
            print(f"  وقف الخسارة  : {levels.get('stop_loss', 'N/A')}")
            print(f"  الأهداف      : {levels.get('targets', [])}")
            print(f"  دعم          : {levels.get('nearest_support', 'N/A')}")
            print(f"  مقاومة       : {levels.get('nearest_resistance', 'N/A')}")

    except Exception as e:
        print(f"❌ خطأ في توليد الإشارة: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()