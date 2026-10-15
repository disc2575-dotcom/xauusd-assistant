"""
bot/chart_generator.py
توليد رسوم بيانية عالية الدقة لـ 3 أطر: D1, H1, M15.
"""

import sys
from pathlib import Path

# ✅ إضافة مسار المشروع إلى sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf

from core.config import DB_PATH, SYMBOL_DB


# ============================================================
# الأطر المدعومة
# ============================================================
SUPPORTED_TIMEFRAMES = ["D1", "H1", "M15"]

# عدد الشموع لكل إطار
BARS_PER_TF = {
    "D1": 100,
    "H1": 200,
    "M15": 300,
}


def load_data(timeframe: str, bars: int = None) -> pd.DataFrame:
    """تحميل بيانات إطار زمني."""
    if bars is None:
        bars = BARS_PER_TF.get(timeframe, 200)

    table = f"{SYMBOL_DB}_{timeframe}"
    conn = sqlite3.connect(str(DB_PATH))
    try:
        df = pd.read_sql(
            f'SELECT * FROM ('
            f'  SELECT * FROM "{table}" ORDER BY timestamp DESC LIMIT {bars}'
            f') ORDER BY timestamp ASC',
            conn,
            parse_dates=["timestamp"],
        )
    finally:
        conn.close()

    return df


def generate_chart(signal: dict, timeframe: str) -> str:
    """
    توليد صورة رسم بياني عالية الدقة لإطار واحد.
    
    الإرجاع:
        مسار الصورة أو None.
    """
    if timeframe not in SUPPORTED_TIMEFRAMES:
        print(f"⚠️ الإطار {timeframe} غير مدعوم")
        return None

    try:
        # 1. تحميل البيانات
        df = load_data(timeframe)
        if df.empty:
            print(f"⚠️ لا توجد بيانات لـ {timeframe}")
            return None

        # 2. تجهيز البيانات
        df = df.set_index("timestamp")
        df = df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        })

        # 3. النمط (Style)
        mc = mpf.make_marketcolors(
            up="#26a69a",
            down="#ef5350",
            edge="inherit",
            wick="inherit",
        )

        style = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor="#131722",
            gridcolor="#2a2e39",
            figcolor="#131722",
            rc={
                "axes.labelcolor": "#d1d4dc",
                "xtick.color": "#d1d4dc",
                "ytick.color": "#d1d4dc",
                "text.color": "#d1d4dc",
                "axes.edgecolor": "#2a2e39",
                "font.size": 11,
            },
        )

        # 4. رسم الشموع
        fig, axes = mpf.plot(
            df,
            type="candle",
            style=style,
            volume=False,
            title=f"\n\nXAUUSD - {timeframe}",
            ylabel="السعر (USD)",
            figsize=(16, 9),
            returnfig=True,
            tight_layout=False,
            scale_padding={"left": 1.5, "right": 1.5, "top": 1.5, "bottom": 1.5},
        )

        ax = axes[0]

        # تكبير الخطوط
        ax.tick_params(axis="both", labelsize=12)
        ax.title.set_size(18)
        ax.yaxis.label.set_size(13)

        # 5. إضافة المستويات
        if signal:
            levels = signal.get("levels", {})

            cp = levels.get("current_price") or signal.get("current_price")
            if cp:
                ax.axhline(
                    y=cp,
                    color="#2196f3",
                    linestyle="-",
                    linewidth=1.5,
                    alpha=0.8,
                    label=f"السعر: {cp}",
                )

            r = levels.get("nearest_resistance")
            if r:
                ax.axhline(
                    y=r,
                    color="#ef5350",
                    linestyle="--",
                    linewidth=1.2,
                    alpha=0.8,
                    label=f"مقاومة: {r}",
                )

            s = levels.get("nearest_support")
            if s:
                ax.axhline(
                    y=s,
                    color="#26a69a",
                    linestyle="--",
                    linewidth=1.2,
                    alpha=0.8,
                    label=f"دعم: {s}",
                )

            entry = levels.get("entry")
            if entry:
                ax.axhline(
                    y=entry,
                    color="#ff9800",
                    linestyle="-",
                    linewidth=1.8,
                    alpha=0.9,
                    label=f"دخول: {entry}",
                )

            sl = levels.get("stop_loss")
            if sl:
                ax.axhline(
                    y=sl,
                    color="#d32f2f",
                    linestyle=":",
                    linewidth=1.3,
                    alpha=0.8,
                    label=f"وقف: {sl}",
                )

            targets = levels.get("targets", [])
            for i, tp in enumerate(targets, 1):
                ax.axhline(
                    y=tp,
                    color="#388e3c",
                    linestyle=":",
                    linewidth=1.2,
                    alpha=0.8,
                    label=f"TP{i}: {tp}",
                )

        # 6. مناطق OB/FVG
        if signal:
            zones = signal.get("zones", [])
            for zone in zones:
                z_type = zone.get("type", "")
                z_top = zone.get("top")
                z_bottom = zone.get("bottom")

                if z_top is None or z_bottom is None:
                    continue

                if "bullish" in z_type:
                    color = "#26a69a"
                    alpha = 0.12
                elif "bearish" in z_type:
                    color = "#ef5350"
                    alpha = 0.12
                else:
                    continue

                ax.axhspan(z_bottom, z_top, color=color, alpha=alpha)

        # 7. Legend
        ax.legend(
            loc="upper left",
            fontsize=11,
            facecolor="#1e222d",
            edgecolor="#2a2e39",
            labelcolor="#d1d4dc",
            framealpha=0.95,
            borderpad=1,
        )

        # 8. معلومات الإشارة في الأعلى
        sig = signal.get("signal", "WAIT")
        conf = signal.get("confidence", 0)
        bias = signal.get("bias", "N/A")

        info_text = f"الإشارة: {sig}  |  الثقة: {conf}%  |  الاتجاه: {bias}"
        fig.text(
            0.5, 0.94,
            info_text,
            ha="center",
            fontsize=13,
            color="#d1d4dc",
            weight="bold",
        )

        # 9. حفظ الصورة
        output_path = Path(f"data/chart_{timeframe}.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fig.savefig(
            output_path,
            dpi=150,
            bbox_inches="tight",
            facecolor="#131722",
            edgecolor="none",
            pad_inches=0.3,
        )
        plt.close(fig)

        print(f"✅ تم توليد {timeframe}: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"❌ خطأ في {timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_all_charts(signal: dict) -> list:
    """توليد 3 رسوم بيانية."""
    paths = []
    for tf in SUPPORTED_TIMEFRAMES:
        path = generate_chart(signal, tf)
        if path:
            paths.append(path)
    return paths


if __name__ == "__main__":
    import json

    signal_path = Path("data/signal.json")
    if signal_path.exists():
        with open(signal_path, "r", encoding="utf-8") as f:
            signal = json.load(f)
    else:
        signal = {}

    generate_all_charts(signal)
