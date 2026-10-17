"""
bot/chart_generator.py
توليد رسوم بيانية لـ 3 أطر: D1, H1, M15 — مع مستويات محسوبة لكل إطار على حدة.

التغييرات:
1. الدعم/المقاومة/المناطق تُحسب لكل إطار من بياناته (smc.levels.extract_levels).
2. العنوان العلوي موحّد (suptitle) بلا تداخل.
3. المناطق تبدأ من شمعة تكوّنها ولا تمتد على كامل الشارت، والملغاة لا تُرسم.
4. تنبيه على الشارت إذا كانت البيانات قديمة.
5. بدون فجوات عطلة وبمحور زمني مرتّب.
6. استخدام النصوص الإنجليزية على الشارت لتفادي مشكلة تشويه العربية في matplotlib.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf

from core.config import DB_PATH, SYMBOL_DB
from smc.levels import extract_levels


SUPPORTED_TIMEFRAMES = ["D1", "H1", "M15"]

BARS_PER_TF = {"D1": 100, "H1": 200, "M15": 300}

# أقصى عمر مقبول لآخر شمعة (بالساعات) قبل إظهار تنبيه "بيانات قديمة"
STALE_AFTER_HOURS = {"D1": 72, "H1": 6, "M15": 2}

DATE_FORMAT = {"D1": "%b %d", "H1": "%b %d %H:%M", "M15": "%b %d %H:%M"}


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


def _is_stale(last_ts: pd.Timestamp, timeframe: str) -> bool:
    now = pd.Timestamp.now(tz=last_ts.tz) if last_ts.tzinfo else pd.Timestamp.now()
    age_h = (now - last_ts).total_seconds() / 3600
    return age_h > STALE_AFTER_HOURS.get(timeframe, 6)


def _hline(ax, y, color, ls, lw, alpha, label):
    ax.axhline(y=y, color=color, linestyle=ls, linewidth=lw, alpha=alpha, label=label)


def generate_chart(signal: dict, timeframe: str) -> str:
    """توليد صورة رسم بياني لإطار واحد. الإرجاع: مسار الصورة أو None."""
    if timeframe not in SUPPORTED_TIMEFRAMES:
        print(f"⚠️ الإطار {timeframe} غير مدعوم")
        return None

    signal = signal or {}

    try:
        # 1. تحميل البيانات
        raw = load_data(timeframe)
        if raw.empty:
            print(f"⚠️ لا توجد بيانات لـ {timeframe}")
            return None

        # 2. مستويات هذا الإطار فقط (من بياناته نفسها)
        try:
            tf_levels = extract_levels(raw[["timestamp", "open", "high", "low", "close"]].copy())
        except Exception as e:
            print(f"⚠️ تعذّر حساب مستويات {timeframe}: {e}")
            tf_levels = {"current_price": float(raw["close"].iloc[-1]),
                         "nearest_resistance": None, "nearest_support": None, "zones": []}

        last_ts = pd.Timestamp(raw["timestamp"].iloc[-1])
        stale = _is_stale(last_ts, timeframe)

        # 3. تجهيز البيانات
        df = raw.set_index("timestamp").rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        n = len(df)

        # 4. النمط
        mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", edge="inherit", wick="inherit")
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

        # 5. رسم الشموع (بدون title داخلي لتفادي التداخل)
        fig, axes = mpf.plot(
            df,
            type="candle",
            style=style,
            volume=False,
            ylabel="Price (USD)",
            figsize=(16, 9),
            returnfig=True,
            tight_layout=False,
            show_nontrading=False,
            datetime_format=DATE_FORMAT[timeframe],
            xrotation=30,
        )
        ax = axes[0]
        ax.tick_params(axis="both", labelsize=12)
        ax.yaxis.label.set_size(13)

        # 6. المناطق: تبدأ من شمعة التكوّن وتمتد لليمين فقط
        for zone in tf_levels.get("zones", []):
            color = "#26a69a" if zone["side"] == "bullish" else "#ef5350"
            x0 = max(0, min(zone["start_idx"], n - 1))
            ax.fill_between([x0, n + 2], zone["bottom"], zone["top"],
                            color=color, alpha=0.15, linewidth=0)

        # 7. المستويات
        cp = tf_levels.get("current_price")
        if cp:
            _hline(ax, cp, "#2196f3", "-", 1.5, 0.8, f"Price: {cp:.2f}")

        r = tf_levels.get("nearest_resistance")
        if r:
            _hline(ax, r, "#ef5350", "--", 1.2, 0.85, f"Resistance: {r:.2f}")

        s = tf_levels.get("nearest_support")
        if s:
            _hline(ax, s, "#26a69a", "--", 1.2, 0.85, f"Support: {s:.2f}")

        # مستويات الصفقة (من الإشارة) إن وُجدت
        sig_levels = signal.get("levels", {}) or {}
        if sig_levels.get("entry"):
            _hline(ax, sig_levels["entry"], "#ff9800", "-", 1.8, 0.9, f"Entry: {sig_levels['entry']}")
        if sig_levels.get("stop_loss"):
            _hline(ax, sig_levels["stop_loss"], "#d32f2f", ":", 1.3, 0.8, f"SL: {sig_levels['stop_loss']}")
        for i, tp in enumerate(sig_levels.get("targets", []) or [], 1):
            _hline(ax, tp, "#388e3c", ":", 1.2, 0.8, f"TP{i}: {tp}")

        ax.set_xlim(-1, n + 3)

        ax.legend(loc="upper left", fontsize=11, facecolor="#1e222d",
                  edgecolor="#2a2e39", labelcolor="#d1d4dc", framealpha=0.95, borderpad=1)

        # 8. العنوان + معلومات الإشارة (سطران منفصلان، بلا تداخل)
        sig = signal.get("signal", "WAIT")
        conf = signal.get("confidence", 0)
        bias = signal.get("bias") or tf_levels.get("trend", "N/A")

        fig.suptitle(f"XAUUSD - {timeframe}", fontsize=18, color="#d1d4dc", y=0.97)
        fig.text(0.5, 0.925,
                 f"Signal: {sig}  |  Conf: {conf}%  |  Bias: {bias}",
                 ha="center", fontsize=13, color="#d1d4dc", weight="bold")

        footer = f"Last candle: {last_ts:%Y-%m-%d %H:%M}"
        if stale:
            footer += "  [STALE DATA]"
        fig.text(0.5, 0.895, footer, ha="center", fontsize=11,
                 color="#ff9800" if stale else "#787b86")

        fig.subplots_adjust(top=0.87)

        # 9. حفظ
        output_path = Path(f"data/chart_{timeframe}.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor="#131722", edgecolor="none", pad_inches=0.3)
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