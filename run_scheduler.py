"""
run_scheduler.py
تشغيل Scheduler للتحديث التلقائي.
- بدون args: يعمل بشكل مستمر.
- مع --once: يعمل دورة واحدة فقط.
"""

from core.scheduler import main


if __name__ == "__main__":
    main()
