# bingx_balance.py
import os, time, hmac, hashlib, requests, json

API_KEY    = os.getenv("BINGX_API_KEY", "")
API_SECRET = os.getenv("BINGX_API_SECRET", "")
BASE_URL   = os.getenv("BINGX_BASE_URL", "https://open-api.bingx.com")

def _sign(params: dict) -> str:
    query = "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def _req(method: str, path: str, params: dict):
    url = f"{BASE_URL}{path}"
    headers = {"X-BX-APIKEY": API_KEY}
    params = dict(params or {})
    params["timestamp"] = str(int(time.time() * 1000))
    params["signature"] = _sign(params)
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=params, timeout=10)
        else:
            r = requests.post(url, headers=headers, params=params, timeout=10)
    except Exception as e:
        print(f"[balance] HTTP error: {e}")
        return None, f"http_error:{e}"
    if r.status_code != 200:
        return None, f"http_{r.status_code}:{r.text}"
    try:
        return r.json(), None
    except json.JSONDecodeError:
        return None, f"json_error:{r.text}"

def get_balance_usdt() -> float:
    if not API_KEY or not API_SECRET:
        print("[balance] Missing BINGX_API_KEY / BINGX_API_SECRET")
        return 0.0

    data, err = _req("GET", "/openApi/swap/v2/user/balance", {})
    if data and isinstance(data, dict) and data.get("code") == 0:
        bal = data.get("data", {}).get("balance")
        if isinstance(bal, list):
            for a in bal:
                if a.get("asset") == "USDT":
                    v = float(a.get("availableBalance") or a.get("availableMargin") or 0.0)
                    print(f"[balance] swap.v2 USDT = {v}")
                    return v
        if isinstance(bal, dict) and bal.get("asset") == "USDT":
            v = float(bal.get("availableMargin") or bal.get("availableBalance") or 0.0)
            print(f"[balance] swap.v2 USDT = {v}")
            return v
        print(f"[balance] swap.v2 no USDT field -> {bal}")
    else:
        if err:
            print(f"[balance] swap.v2 error: {err}")
        elif data:
            print(f"[balance] swap.v2 response: {data}")

    data, err = _req("GET", "/openApi/spot/v1/account/balance", {})
    if data and isinstance(data, dict) and data.get("code") == 0:
        for a in data.get("data", []):
            if a.get("asset") == "USDT":
                free = float(a.get("free", 0.0))
                print(f"[balance] spot USDT = {free}")
                return free
        print(f"[balance] spot no USDT in response")
    else:
        if err:
            print(f"[balance] spot error: {err}")
        elif data:
            print(f"[balance] spot response: {data}")

    return 0.0

if __name__ == "__main__":
    v = get_balance_usdt()
    print(f"[balance] USDT available = {v}")
