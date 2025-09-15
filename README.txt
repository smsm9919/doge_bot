
نشر سريع على Render بدون تعديل ملف البوت:

1) ضع ملف البوت الأصلي بجانب هذه الملفات.
2) إن لم يكن اسمه bot.py، أضف متغير بيئة على Render:
   BOT_MODULE = اسم_ملفك_بدون_.py  (مثال: doge_bot)
3) أضف مفاتيح BingX كـ Env Vars:
   BINGX_API_KEY, BINGX_API_SECRET
   (اختياري) MAX_TRADES_PER_HOUR, COOLDOWN_AFTER_CLOSE, MIN_BARS_BETWEEN_FLIPS
4) اعمل Deploy وسيبدأ:
   - حلقة التداول (Thread)
   - لوحة الويب على PORT

الـ Guard يمنع القلب العكسي/العشوائي ويطبق تبريد وحد صفقات وIdempotency
بدون تغيير أي توقيع دالة في سكربتك.
