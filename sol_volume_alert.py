"""
تنبيه حجم تداول سولانا اليومي (DEX 24h) عبر تلكرام.

التشغيل:
  python sol_volume_alert.py --test    # يبعث رسالة تجريبية
  python sol_volume_alert.py           # فحص مرة وحدة
  python sol_volume_alert.py --loop    # فحص كل نص ساعة بدون توقف

المتطلبات: pip install requests
متغيرات البيئة: TELEGRAM_TOKEN و TELEGRAM_CHAT_ID
"""
import json
import os
import sys
import time
from datetime import datetime

import requests

API_URL = "https://api.llama.fi/overview/dexs/solana"
CHECK_EVERY = 30 * 60        # كل 30 دقيقة
COOLDOWN = 2 * 3600          # أقل فاصل بين إشعارين
TREND_WINDOW = 6 * 3600      # نقارن الحجم الحالي بقراءة قبل ~6 ساعات
STATE_FILE = "state.json"

COLD, GOOD_LOW, GOOD_HIGH = 2e9, 3e9, 6e9   # حدود المناطق (دولار)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def fetch_volume() -> float:
    r = requests.get(
        API_URL,
        params={"excludeTotalDataChart": "true", "excludeTotalDataChartBreakdown": "true"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("total24h") is None:
        raise ValueError(f"الحقل total24h غير موجود. الحقول المتوفرة: {list(data)[:12]}")
    return float(data["total24h"])


def zone(v: float) -> str:
    if v < COLD:
        return "cold"
    if v < GOOD_LOW:
        return "mid"
    if v <= GOOD_HIGH:
        return "good"
    return "hot"


def trend_arrow(history: list, now: float, v: float) -> str:
    old = [h for h in history if now - h[0] >= TREND_WINDOW]
    if not old:
        return "؟"
    ref = old[-1][1]
    change = (v - ref) / ref
    return "↑ طالع" if change > 0.03 else "↓ نازل" if change < -0.03 else "→ ثابت"


def send_telegram(text: str) -> None:
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("ضيف TELEGRAM_TOKEN و TELEGRAM_CHAT_ID كمتغيرات بيئة")
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=30,
    )
    r.raise_for_status()


def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"history": [], "notified_zone": None, "notified_at": 0}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def check() -> None:
    now = time.time()
    state = load_state()
    v = fetch_volume()
    z = zone(v)
    arrow = trend_arrow(state["history"], now, v)

    state["history"] = [h for h in state["history"] if now - h[0] < 48 * 3600] + [[now, v]]

    print(f"{datetime.now():%Y-%m-%d %H:%M} | {v / 1e9:.2f} مليار | {z} | {arrow}")

    if z not in ("good", "hot"):
        state["notified_zone"] = None   # نعيد التهيئة حتى ينبه عند الدخول مرة ثانية
    elif z != state["notified_zone"] and now - state["notified_at"] >= COOLDOWN:
        if z == "good":
            msg = f"✅ حجم سولانا اليومي دخل النطاق الجيد: {v / 1e9:.2f} مليار دولار ({arrow})"
        else:
            msg = f"⚠️ الحجم فوق 6 مليار: {v / 1e9:.2f} مليار ({arrow}). السوق محموم، خفف حجم صفقاتك."
        send_telegram(msg)
        state["notified_zone"], state["notified_at"] = z, now

    save_state(state)


def main() -> None:
    if "--test" in sys.argv:
        send_telegram("رسالة تجريبية: التنبيه شغال ✅")
        print("انبعثت الرسالة التجريبية")
        return
    if "--loop" not in sys.argv:
        check()
        return
    while True:
        try:
            check()
        except Exception as e:  # لا نوقف الحلقة بسبب خطأ شبكة مؤقت
            print(f"خطأ: {e}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
