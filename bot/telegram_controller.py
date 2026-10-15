"""
bot/telegram_controller.py
بوت تفاعلي للتحكم في Scheduler عبر Telegram.
"""

import os
import asyncio
import threading
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ============================================================
# حالة التشغيل
# ============================================================
_scheduler_thread = None
_scheduler_running = False


def is_authorized(update: Update) -> bool:
    """التحقق من أن المستخدم مصرح."""
    if not TELEGRAM_CHAT_ID:
        return True
    return str(update.effective_chat.id) == str(TELEGRAM_CHAT_ID)


def run_scheduler_in_thread():
    """تشغيل Scheduler في thread منفصل."""
    global _scheduler_running
    from core.scheduler import run_scheduler
    try:
        _scheduler_running = True
        run_scheduler()  # سيعمل باستمرار
    except Exception as e:
        print(f"❌ خطأ في Scheduler: {e}")
    finally:
        _scheduler_running = False


# ============================================================
# الأوامر
# ============================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء Scheduler."""
    global _scheduler_thread, _scheduler_running

    if not is_authorized(update):
        await update.message.reply_text("⛔ غير مصرح")
        return

    if _scheduler_running:
        await update.message.reply_text("▶️ Scheduler يعمل بالفعل!")
        return

    # تشغيل Scheduler في thread
    _scheduler_thread = threading.Thread(
        target=run_scheduler_in_thread,
        daemon=True,
    )
    _scheduler_thread.start()

    await update.message.reply_text(
        "✅ تم بدء Scheduler!\n"
        "📤 ستصلك التقارير كل 15 دقيقة.\n"
        "🛑 للإيقاف: /stop"
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف Scheduler."""
    global _scheduler_running

    if not is_authorized(update):
        await update.message.reply_text("⛔ غير مصرح")
        return

    if not _scheduler_running:
        await update.message.reply_text("⏹️ Scheduler متوقف بالفعل.")
        return

    from core.scheduler import stop_scheduler
    stop_scheduler()
    _scheduler_running = False

    await update.message.reply_text(
        "🛑 تم إيقاف Scheduler.\n"
        "▶️ لإعادة التشغيل: /start"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حالة النظام."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ غير مصرح")
        return

    status = "🟢 يعمل" if _scheduler_running else "🔴 متوقف"

    await update.message.reply_text(
        f"📊 *حالة النظام*\n\n"
        f"🔄 Scheduler: {status}\n"
        f"⏱️ الفاصل: 15 دقيقة\n"
        f"📊 الأطر: D1, H1, M15",
        parse_mode="Markdown",
    )


async def cmd_run_once(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تنفيذ دورة واحدة فوراً."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ غير مصرح")
        return

    await update.message.reply_text("⏳ جاري التنفيذ...")

    try:
        from core.scheduler import run_once
        run_once()
        await update.message.reply_text("✅ تم! استخدم /signal لرؤية الإشارة.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الإشارة الحالية."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ غير مصرح")
        return

    import json
    signal_path = Path("data/signal.json")

    if not signal_path.exists():
        await update.message.reply_text("⚠️ لا توجد إشارة. استخدم /run_once.")
        return

    with open(signal_path, "r", encoding="utf-8") as f:
        signal = json.load(f)

    msg = (
        f"🎯 *الإشارة*\n"
        f"📈 {signal.get('signal', 'N/A')}\n"
        f"🎚️ {signal.get('confidence', 0)}%\n"
        f"💰 {signal.get('current_price', 'N/A')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة الأوامر."""
    msg = (
        "📖 *الأوامر المتاحة*\n\n"
        "▶️ /start — بدء Scheduler\n"
        "🛑 /stop — إيقاف Scheduler\n"
        "📊 /status — حالة النظام\n"
        "🔄 /run_once — تنفيذ دورة فورية\n"
        "🎯 /signal — الإشارة الحالية\n"
        "❓ /help — هذه القائمة"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ============================================================
# التشغيل
# ============================================================
def main():
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN غير موجود")
        return

    print("=" * 60)
    print("🤖 Telegram Controller")
    print("=" * 60)
    print(f"   التوكن: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
    print("=" * 60)
    print("   الأوامر: /start, /stop, /status, /run_once, /signal, /help")
    print("   ⏹️ للإيقاف: Ctrl+C")
    print("=" * 60)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("run_once", cmd_run_once))
    app.add_handler(CommandHandler("signal", cmd_signal))
    app.add_handler(CommandHandler("help", cmd_help))

    print("\n✅ البوت يعمل. أرسل /help على Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
