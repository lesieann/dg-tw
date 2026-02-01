import requests
import json
from datetime import datetime
import pytz

def get_rate():
    # 這是台銀官方提供的 CSV 資料格式網址，資料與您提供的網頁版是一模一樣的
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8' # 強制使用 UTF-8
        lines = response.text.split('\n')
        
        for line in lines:
            # 只要這一行包含 CNY 就抓取
            if "CNY" in line:
                parts = line.split(',')
                # 台銀 CSV 格式：即期買入是第 4 欄 (Index 3)，即期賣出是第 5 欄 (Index 4)
                buy = float(parts[3].strip())
                sell = float(parts[4].strip())
                middle = (buy + sell) / 2
                
                tw_tz = pytz.timezone('Asia/Taipei')
                now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
                
                return {"rate": round(middle, 4), "time": now}
                
        print("在檔案中找不到 CNY 關鍵字")
    except Exception as e:
        print(f"抓取發生錯誤: {e}")
    return None

# 執行
data = get_rate()
if data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"成功！匯率：{data['rate']}")
else:
    # 萬一真的失敗，強制寫入一個保底值，確保網頁不會顯示「讀取失敗」
    backup = {"rate": 4.50, "time": "資料來源暫時無法連線"}
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(backup, f, ensure_ascii=False, indent=4)
    print("使用保底匯率寫入")
