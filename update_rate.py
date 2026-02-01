import requests
import io
import pandas as pd
import json
from datetime import datetime
import pytz

def get_rate():
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    try:
        # 增加 Timeout 防止卡死
        response = requests.get(url, timeout=30)
        response.encoding = 'utf-8'
        df = pd.read_csv(io.StringIO(response.text))
        
        # 搜尋 CNY
        cny = df[df.iloc[:, 0].str.contains("CNY", na=False)]
        
        # 取得即期買入(索引3)與賣出(索引4)
        buy = float(cny.iloc[0, 3])
        sell = float(cny.iloc[0, 4])
        middle = (buy + sell) / 2
        
        # 台灣時間
        tw_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        return {"rate": round(middle, 4), "time": now}
    except Exception as e:
        print(f"Error fetching rate: {e}")
        return None

# 執行並儲存
new_data = get_rate()
if new_data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
else:
    print("Keep old rate because current fetch failed.")
