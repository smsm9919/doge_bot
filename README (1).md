
# تشغيل بوت BingX على Render + طبقة حماية ضد الصفقات العكسية

## نظرة عامة
هذا الدليل يوضح كيف تشغّل البوت كما هو **بدون تعديل الدوال الأساسية**، مع إضافة:
- `strategy_guard.py`: طبقة حوكمة تمنع الصفقات العكسية/العشوائية وتقوّي الدخول.
- `bingx_balance.py`: قراءة رصيد USDT من BingX (Futures/Spot) بثبات.

> اللفة (guard) تعمل عبر **monkeypatch** وقت التشغيل؛ لا تغيّر توقيعات `place_order` أو `close_position` أو باقي المنطق.

---

## الملفات
- `strategy_guard.py` — Anti-flip, تبريد بعد الإغلاق، حد صفقات/ساعة، Idempotency، فلاتر اتجاه (EMA200/ADX/RSI/ATR Spike)، ضبط استخدام رأس المال بنسبة 60%.
- `bingx_balance.py` — دالة `get_balance_usdt()` تقرأ الرصيد من API وتطبع سبب أي فشل.
- (اختياري) `runner.py` — إن أردت تشغيل البوت بملف وسيط؛ وإلا استخدم ملفك الرئيسي.

---

## المتطلبات
- Python 3.10+
- Render Web Service (خدمة واحدة تكفي).
- Env Vars (في Render → **Environment**):
  - `BINGX_API_KEY`
  - `BINGX_API_SECRET`
  - (اختياري للتوليف):
    - `MAX_TRADES_PER_HOUR=3`
    - `COOLDOWN_AFTER_CLOSE=300`
    - `MIN_BARS_BETWEEN_FLIPS=5`
    - `USE_DIRECTION_FILTERS=true`
    - `MIN_ADX=25`
    - `RSI_BUY_MIN=55`
    - `RSI_SELL_MAX=45`
    - `SPIKE_ATR_MULT=1.8`
    - `MIN_TP_PERCENT=0.75`
    - `ENFORCE_TRADE_PORTION=true`
    - `TARGET_TRADE_PORTION=0.60`

> تأكد أن مفاتيحك **Futures/Swap** لو البوت يتداول عقود، وأن في رصيد USDT متاح في **Futures Wallet**.

---

## دمج سريع مع البوت (بدون تعديل دوالك)
في ملف التشغيل الخاص بك (الذي يملك `app` و `main_bot_loop()`):
```python
import your_bot_module as userbot  # استبدل باسم ملف البوت بدون .py
from strategy_guard import attach_guard
attach_guard(userbot)              # تفعيل الحارس

# شغّل حلقة التداول والـ Flask كما تفعل عادةً
# مثال:
# from threading import Thread
# Thread(target=userbot.main_bot_loop, daemon=True).start()
# userbot.app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
```

سترى في اللوج عند البدء:
```
✅ strategy_guard attached (anti-reverse, cooldown, filters, 60% capital).
```

---

## نشر على Render (خطوات عملية)
1) ارفع المشروع إلى GitHub ويشمل ملفاتك + `strategy_guard.py` + `bingx_balance.py`.
2) أنشئ **Web Service** من المستودع.
3) **Start Command** المقترح (إنتاجي):  
   ```bash
   gunicorn -w 1 -b 0.0.0.0:$PORT runner:main
   ```
   أو إن كنت تشغّل من ملفك مباشرة:
   ```bash
   python your_entry_file.py
   ```
4) أضف Env Vars المذكورة أعلاه ثم **Deploy**.

> لو تستخدم `runner.py` ذكي يدعم `BOT_MODULE`:
> - `BOT_MODULE=اسم_ملف_البوت_بدون_.py` (افتراضي: `bot`).

---

## ما الذي يمنعه/يفرضه الحارس؟
- **Anti-Flip**: لا قلب BUY↔SELL قبل مرور عدد شموع (`MIN_BARS_BETWEEN_FLIPS`).
- **Cooldown بعد الإغلاق** (`COOLDOWN_AFTER_CLOSE` ثواني).
- **حدّ صفقات/ساعة** (`MAX_TRADES_PER_HOUR`).
- **Idempotency**: عدم تكرار نفس الإشارة/السعر.
- **فلترة اتجاه/زخم**: EMA200 + ADX + RSI + منع Spike (ATR).
- **R:R حد أدنى**: `MIN_TP_PERCENT` كنسبة من السعر.
- **إدارة مال**: يفرض استخدام **60%** من رأس المال كحد أقصى للصفقة (`TARGET_TRADE_PORTION`).

كلها قابلة للضبط عبر Env Vars بدون تغيير الكود.

---

## التتبّع في اللوج
أمثلة رسائل:
- `⛔ Prevent fast flip — wait bars`
- `⛔ Max trades/hour — skip`
- `⛔ BUY blocked: price ≤ EMA200`
- `[balance] swap.v2 USDT = ...` أو `[balance] spot USDT = ...`

---

## troubleshooting (مختصر)
- **ModuleNotFoundError: bot** → إمّا أعد تسمية ملفك إلى `bot.py` أو اضبط `BOT_MODULE` في Env Vars.
- **Error: Initial balance is not positive** → مفاتيح API غير صحيحة/ليست Futures، أو الرصيد صفر في Futures Wallet.
- **Flask warning (development server)** → شغّل بـ **gunicorn** كما في أمر الإنتاج.
- **أوامر لا تنفّذ** → راجع رسائل الحارس في اللوج؛ قد يمنعها بسبب فلتر أو تبريد أو حدود.

---

## أمان
- لا تضع المفاتيح في الكود/الريبو. استخدم Env Vars فقط.
- فعّل **IP Whitelist** في BingX لو أمكن.
- قلّل صلاحيات المفاتيح إلى **Trade + Read Market** فقط بدون سحب.

---

## تواصل
لو عايز إعدادات أدق لاستراتيجيتك (مثلاً عتبات مختلفة لكل فريم، أو دمج Supertrend/ATR ديناميكي)، حدّد المطلوب وأنا أضبط الـ Env Vars/الحارس بما يناسب.
