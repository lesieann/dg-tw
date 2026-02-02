import requests
import json
from datetime import datetime
import pytz

def get_rate():
    # 使用全球通用匯率 API (CNY 對 TWD)
    url = "https://open.er-api.com/v6/latest/CNY"
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        if data["result"] == "success":
            rate = data["rates"]["TWD"]
            tw_tz = pytz.timezone('Asia/Taipei')
            now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
            return {"rate": round(rate, 4), "time": now}
    except Exception as e:
        print(f"Error: {e}")
    return None

data = get_rate()
if data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
