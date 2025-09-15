
import os, time, hashlib
from collections import deque

def _get_env_float(key, default):
    try:
        return float(os.getenv(key, default))
    except Exception:
        return float(default)

def _get_env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except Exception:
        return int(default)

def _idempotent_key(symbol, tf, side, price):
    payload = f"{symbol}|{tf}|{side}|{round(float(price or 0),6)}"
    return hashlib.sha1(payload.encode()).hexdigest()

def attach_guard(userbot):
    MAX_TRADES_PER_HOUR    = _get_env_int("MAX_TRADES_PER_HOUR", 3)
    COOLDOWN_AFTER_CLOSE   = _get_env_int("COOLDOWN_AFTER_CLOSE", 300)  # seconds
    MIN_BARS_BETWEEN_FLIPS = _get_env_int("MIN_BARS_BETWEEN_FLIPS", 5)

    recent_trades_ts = deque()
    seen_signal_keys = deque(maxlen=100)
    state = {"last_close_time": 0.0, "last_flip_bar_index": -10}

    def _too_many_trades_per_hour():
        now = time.time()
        while recent_trades_ts and now - recent_trades_ts[0] > 3600:
            recent_trades_ts.popleft()
        return len(recent_trades_ts) >= MAX_TRADES_PER_HOUR

    _orig_close_position = userbot.close_position
    def _wrapped_close_position(reason, exit_price):
        ok = _orig_close_position(reason, exit_price)
        if ok:
            state["last_close_time"] = time.time()
        return ok
    userbot.close_position = _wrapped_close_position

    _orig_place_order = userbot.place_order
    def _wrapped_place_order(side, quantity):
        since_close = time.time() - state["last_close_time"]
        if since_close < COOLDOWN_AFTER_CLOSE:
            print(f"🕒 Post-close cooldown {int(COOLDOWN_AFTER_CLOSE - since_close)}s — skipping")
            return False

        if _too_many_trades_per_hour():
            print("⛔ Max trades/hour reached — skipping")
            return False

        try:
            price = float(getattr(userbot, "current_price", 0.0) or 0.0)
        except Exception:
            price = 0.0
        sym = getattr(userbot, "SYMBOL", "DOGE-USDT")
        tf  = getattr(userbot, "INTERVAL", "15m")
        key = _idempotent_key(sym, tf, side, price)
        if key in seen_signal_keys:
            print("⛔ Duplicate signal key — skipping")
            return False

        try:
            df = userbot.get_klines()
            bar_index = len(df) - 1 if df is not None and len(df) else 0
        except Exception:
            bar_index = 0

        last_dir = getattr(userbot, "last_direction", None)
        if last_dir and ((side == "BUY" and last_dir == "SELL") or (side == "SELL" and last_dir == "BUY")):
            if (bar_index - state["last_flip_bar_index"]) < MIN_BARS_BETWEEN_FLIPS:
                print("⛔ Prevent fast flip — waiting more bars")
                return False

        ok = _orig_place_order(side, quantity)
        if ok:
            seen_signal_keys.append(key)
            recent_trades_ts.append(time.time())
            if last_dir and ((side == "BUY" and last_dir == "SELL") or (side == "SELL" and last_dir == "BUY")):
                state["last_flip_bar_index"] = bar_index
        return ok

    userbot.place_order = _wrapped_place_order
    print("✅ Guard wrapper attached (anti-flip, cooldown, rate-limit, idempotency).")
