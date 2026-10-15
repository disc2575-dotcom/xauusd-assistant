import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def test():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    print("=" * 50)
    print(f"Token: {token[:20]}..." if token else "❌ Token missing")
    print(f"Chat ID: {chat_id}" if chat_id else "❌ Chat ID missing")
    print("=" * 50)

    if not token or not chat_id:
        print("❌ معلومات ناقصة في .env")
        return

    bot = Bot(token=token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text="🧪 اختبار من PythonAnywhere\n✅ البوت يعمل!",
        )
        print("✅ تم الإرسال بنجاح")
    except Exception as e:
        print(f"❌ خطأ: {e}")

asyncio.run(test())
