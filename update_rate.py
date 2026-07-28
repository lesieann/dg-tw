import requests
import json
from datetime import datetime
import pytz


def now_str():
    return datetime.now(pytz.timezone('Asia/Taipei')).strftime('%Y-%m-%d %H:%M:%S')


def get_bot_rate():
    # 台灣銀行牌告匯率 CSV，取人民幣「現金買入/賣出」中間價
    # 欄位：0=幣別, 2=現金買入, 12=現金賣出
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    for line in response.text.splitlines():
        cols = line.split(',')
        if cols and cols[0].strip() == 'CNY':
            cash_buy = float(cols[2])
            cash_sell = float(cols[12])
            # 合理範圍檢查，避免欄位位移抓錯值
            if not (2 < cash_buy < 10 and 2 < cash_sell < 10 and cash_buy < cash_sell):
                raise ValueError(f'BoT CNY rate out of range: buy={cash_buy}, sell={cash_sell}')
            mid = (cash_buy + cash_sell) / 2
            return {"rate": round(mid, 4), "time": now_str(), "source": "台銀"}
    raise ValueError('CNY row not found in BoT CSV')


def get_erapi_rate():
    # 備援：全球通用匯率 API (CNY 對 TWD，市場中間價，每日更新一次)
    url = "https://open.er-api.com/v6/latest/CNY"
    response = requests.get(url, timeout=30)
    data = response.json()
    if data["result"] == "success":
        rate = data["rates"]["TWD"]
        return {"rate": round(rate, 4), "time": now_str(), "source": "exchangerate"}
    raise ValueError('er-api returned non-success result')


data = None
try:
    data = get_bot_rate()
except Exception as e:
    print(f"BoT error: {e}")
    try:
        data = get_erapi_rate()
    except Exception as e2:
        print(f"er-api error: {e2}")

if data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Updated: {data}")
else:
    print("All rate sources failed; rate.json left unchanged")
