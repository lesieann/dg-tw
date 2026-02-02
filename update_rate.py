import requests
import json
from datetime import datetime
import pytz

def get_rate():
    # 使用免費 API 取得 CNY 對 TWD 的即期匯率 (這也是支付寶的基礎參考價)
    # 這裡使用一個不需要 Key 的公共 API 作為範例
    url = "https://open.er-api.com/v6/latest/CNY"
    
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data["result"] == "success":
            # 取得 TWD 的匯率 (即 1 CNY 等於多少 TWD)
            rate = data["rates"]["TWD"]
            
            tw_tz = pytz.timezone('Asia/Taipei')
            now = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
            
            return {"rate": round(rate, 4), "time": now, "source": "Real-time Market Rate"}
            
        print("API 回傳失敗")
    except Exception as e:
        print(f"抓取發生錯誤: {e}")
    return None

# 執行
data = get_rate()
if data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"成功更新！匯率：{data['rate']}")
else:
    print("更新失敗")
