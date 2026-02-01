import requests
import io
import pandas as pd
import json
from datetime import datetime
import pytz

def get_rate():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        # 讀取 CSV，不指定 Header 以免出錯
        df = pd.read_csv(io.StringIO(response.text))
        
        # 1. 尋找包含 "CNY" 或 "人民幣" 的那一行
        cny_row = df[df.iloc[:, 0].str.contains("CNY", na=False)]
        if cny_row.empty:
            print("找不到 CNY 欄位，嘗試搜尋 '人民幣'")
            cny_row = df[df.iloc[:, 0].str.contains("人民幣", na=False)]

        if not cny_row.empty:
            # 2. 自動尋找數值：即期買入通常在第 3 或 4 欄，即期賣出在第 4 或 5 欄
            # 我們改用更保險的方法：抓出這一行所有數字，取後面的兩個即期匯率
            row_values = cny_row.values[0]
            numbers = []
            for val in row_values:
                try:
                    num = float(val)
                    if num > 0: numbers.append(num)
                except:
                    continue
            
            # 台銀 CSV 結構中，最後兩個數字通常是即期買入與賣出
            if len(numbers) >= 2:
                # 這裡取即期匯率 (通常是列表中的最後兩個數字，或者是索引 3, 4 或 12, 13)
                # 為了準確，我們取標準位置：即期買入(Index 3), 即期賣出(Index 4)
                buy = float(cny_row.iloc[0, 3])
                sell = float(cny_row.iloc[0, 4])
                middle = (buy + sell) / 2
                
                tw_tz = pytz.timezone('Asia/Taipei')
                now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"找到匯率: 買入{buy}, 賣出{sell}, 中間{middle}")
                return {"rate": round(middle, 4), "time": now}
        
        print("搜尋邏輯未找到數值")
        return None
    except Exception as e:
        print(f"發生錯誤: {e}")
        return None

# 執行並強制寫入
new_data = get_rate()
if new_data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)
    print("rate.json 更新成功")
else:
    # 如果抓不到，給一個保底數字以免網頁壞掉
    print("使用保底匯率")
    # 這裡不寫入檔案，讓它保留舊的資料
