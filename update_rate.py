import requests
import io
import pandas as pd
import json
from datetime import datetime
import pytz

def get_rate():
    # 模擬瀏覽器身份，防止被台銀阻擋
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"台銀拒絕連線，狀態碼: {response.status_code}")
            return None
            
        df = pd.read_csv(io.StringIO(response.text))
        cny = df[df.iloc[:, 0].str.contains("CNY", na=False)]
        
        # 即期買入是第4欄 (index 3), 賣出是第5欄 (index 4)
        buy = float(cny.iloc[0, 3])
        sell = float(cny.iloc[0, 4])
        middle = (buy + sell) / 2
        
        tw_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        return {"rate": round(middle, 4), "time": now}
    except Exception as e:
        print(f"發生錯誤: {e}")
        return None

# 執行
new_data = get_rate()
if new_data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    print(f"成功更新匯率: {new_data['rate']}")
else:
    print("抓取失敗，保持舊資料")
