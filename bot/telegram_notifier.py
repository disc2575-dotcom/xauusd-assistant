"""
bot/telegram_notifier.py
إرسال التقارير الكاملة + 3 رسوم بيانية إلى Telegram.
+ رابط للواجهة الكاملة على Streamlit Cloud.
+ التأكيدات (BOS Confirmed + نماذج الشموع).
+ النماذج السعرية (Head & Shoulders, Double Top/Bottom).
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# ✅ إضافة مسار المشروع إلى sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SIGNAL_PATH = Path("data/signal.json")

# ============================================================
# رابط الواجهة الكاملة (Streamlit Cloud)
# ============================================================
STREAMLIT_URL = "https://xauusd-assistant.streamlit.app"


def format_short_message(signal: dict) -> str:
    """تنسيق رسالة مختصرة."""
    if not signal:
        return "⚠️ لا توجد إشارة."

    sig = signal.get("signal", "WAIT")
    if sig == "BUY":
        emoji = "🟢"
    elif sig == "SELL":
        emoji = "🔴"
    else:
        emoji = "⏸️"

    levels = signal.get("levels", {})
    news = signal.get("news_analysis", {})

    lines = [
        f"🥇 *إشارة XAUUSD*",
        f"🕒 {signal.get('updated_at', 'N/A')[:19]}",
        "",
        f"{emoji} *{sig}* | الثقة: *{signal.get('confidence', 0)}%*",
        f"📈 الاتجاه: *{signal.get('bias', 'N/A').upper()}*",
        f"💰 السعر: *{signal.get('current_price', 'N/A')}*",
        "",
    ]

    if levels.get("entry"):
        lines.append("🎯 *خطة الدخول*")
        lines.append(f"• دخول: `{levels.get('entry')}`")
        lines.append(f"• وقف: `{levels.get('stop_loss')}`")
        targets = levels.get("targets", [])
        for i, tp in enumerate(targets, 1):
            lines.append(f"• TP{i}: `{tp}`")
        lines.append("")

    lines.append("💰 *المستويات*")
    lines.append(f"• مقاومة: `{levels.get('nearest_resistance', 'N/A')}`")
    lines.append(f"• دعم: `{levels.get('nearest_support', 'N/A')}`")
    lines.append("")

    if news:
        sentiment = news.get("sentiment", "neutral")
        if sentiment == "bullish":
            nemoji = "🟢"
        elif sentiment == "bearish":
            nemoji = "🔴"
        else:
            nemoji = "⚪"
        lines.append(f"📰 الأخبار: {nemoji} {sentiment} ({news.get('score', 0)})")

    # ✅ التأكيدات
    confirmations = signal.get("confirmations", [])
    if confirmations:
        lines.append("")
        lines.append("🔔 *التأكيدات:*")
        for c in confirmations[-3:]:
            lines.append(f"• {c.get('label', 'N/A')}")

    # ✅ النماذج السعرية
    patterns = signal.get("patterns", [])
    if patterns:
        lines.append("")
        lines.append("🟦 *النماذج السعرية:*")
        for p in patterns[-3:]:
            lines.append(f"• {p.get('label', 'N/A')}")

    # رابط الواجهة الكاملة
    lines.append("")
    lines.append(f"📊 [عرض التقرير الكامل]({STREAMLIT_URL})")

    return "\n".join(lines)


def format_full_report(signal: dict) -> str:
    """تنسيق التقرير الكامل."""
    lines = ["📋 *التقرير الكامل*", ""]

    # الأطر الزمنية
    timeframes = signal.get("timeframes", {})
    if timeframes:
        lines.append("📊 *الأطر الزمنية*")
        for tf, data in timeframes.items():
            lines.append(f"• {tf}: {data.get('trend', 'N/A')} (وزن: {data.get('weight', 0)})")
        lines.append("")

    # الأخبار
    news = signal.get("news_analysis", {})
    if news:
        lines.append("📰 *تفاصيل الأخبار*")
        lines.append(f"• التحليل: {news.get('reasoning', 'N/A')}")
        lines.append("")

        topics = news.get("key_topics", [])
        if topics:
            lines.append("• المواضيع:")
            for t in topics[:5]:
                lines.append(f"  - {t}")
            lines.append("")

        headlines = news.get("headlines", [])
        if headlines:
            lines.append("• العناوين:")
            for h in headlines[:5]:
                lines.append(f"  - {h}")
            lines.append("")

    # OB/FVG
    zones = signal.get("zones", [])
    if zones:
        lines.append("📋 *مناطق OB/FVG*")
        for z in zones[:10]:
            lines.append(
                f"• {z.get('label', 'N/A')}: "
                f"{z.get('bottom', 'N/A')} → {z.get('top', 'N/A')}"
            )
        lines.append("")

    # ✅ التأكيدات
    confirmations = signal.get("confirmations", [])
    if confirmations:
        lines.append("🔔 *التأكيدات*")
        for c in confirmations:
            ts = c.get('timestamp', 'N/A')
            if ts and ts != 'N/A':
                ts = ts[:16]
            lines.append(f"• {c.get('label', 'N/A')} — {ts}")
        lines.append("")

    # ✅ النماذج السعرية
    patterns = signal.get("patterns", [])
    if patterns:
        lines.append("🟦 *النماذج السعرية*")
        for p in patterns:
            ts = p.get('timestamp', 'N/A')
            if ts and ts != 'N/A':
                ts = ts[:16]
            lines.append(f"• {p.get('label', 'N/A')} — {ts}")
        lines.append("")

    # السيناريوهات
    scenarios = signal.get("conditional_scenarios", [])
    if scenarios:
        lines.append("🎬 *السيناريوهات*")
        for s in scenarios:
            lines.append(f"• {s.get('condition', 'N/A')}")
            lines.append(f"  → {s.get('action', 'N/A')} @ `{s.get('entry', 'N/A')}`")
        lines.append("")

    # رابط الواجهة الكاملة
    lines.append("")
    lines.append(f"📊 [عرض التقرير الكامل]({STREAMLIT_URL})")

    return "\n".join(lines)


async def send_telegram_async(signal: dict = None, send_charts: bool = True) -> bool:
    """إرسال الإشارة والرسوم إلى Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID غير موجود")
        return False

    if signal is None:
        if not SIGNAL_PATH.exists():
            print("❌ لا يوجد signal.json")
            return False
        with open(SIGNAL_PATH, "r", encoding="utf-8") as f:
            signal = json.load(f)

    # ✅ Bot بدون request_kwargs
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        # 1. الرسالة المختصرة
        short_msg = format_short_message(signal)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=short_msg,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
        )
        print("✅ تم إرسال الرسالة المختصرة")

        # 2. التقرير الكامل
        full_report = format_full_report(signal)
        max_len = 4000

        if len(full_report) > max_len:
            for i in range(0, len(full_report), max_len):
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=full_report[i:i + max_len],
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=False,
                )
                await asyncio.sleep(1)
        else:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=full_report,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
        print("✅ تم إرسال التقرير الكامل")

        # 3. الرسوم البيانية (3 أطر)
        if send_charts:
            try:
                from bot.chart_generator import generate_all_charts
                print("📊 توليد الرسوم البيانية...")
                chart_paths = generate_all_charts(signal)

                for path in chart_paths:
                    if path and Path(path).exists():
                        tf = Path(path).stem.replace("chart_", "")

                        try:
                            with open(path, "rb") as photo:
                                await bot.send_photo(
                                    chat_id=TELEGRAM_CHAT_ID,
                                    photo=photo,
                                    caption=f"📈 XAUUSD - {tf}",
                                )
                            print(f"✅ تم إرسال رسم {tf}")
                        except Exception as e:
                            print(f"⚠️ فشل رسم {tf}: {e}")
                            continue

                        await asyncio.sleep(2)

            except Exception as e:
                print(f"⚠️ فشل إرسال الرسوم: {e}")
                import traceback
                traceback.print_exc()

        print("✅ تم إرسال كل شيء إلى Telegram")
        return True

    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_telegram(signal: dict = None, send_charts: bool = True) -> bool:
    """نسخة متزامنة."""
    try:
        return asyncio.run(send_telegram_async(signal, send_charts))
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return False


if __name__ == "__main__":
    send_telegram()
