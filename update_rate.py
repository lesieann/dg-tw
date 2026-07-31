import json
import os
from datetime import datetime, timedelta

import pytz
import requests

TW_TZ = pytz.timezone('Asia/Taipei')

# 台銀無法取得時，最多沿用幾天前的台銀牌告（涵蓋週末與連假）
MAX_CARRY_OVER_DAYS = 7


def now_dt():
    return datetime.now(TW_TZ)


def fmt(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def first_value_after(cols, label):
    """回傳 cols 中第一個等於 label 的欄位後面那個數值。"""
    for i, cell in enumerate(cols):
        if cell == label and i + 1 < len(cols):
            return float(cols[i + 1])
    raise ValueError(f'{label} not found in row: {cols}')


def get_bot_rate():
    """台灣銀行牌告匯率 CSV，取人民幣「現金買入/賣出」中間價。

    這個端點沒有標題列，每一列的格式固定為
        幣別,本行買入,現金買入,本行買入,即期買入,遠期×7,
             本行賣出,現金賣出,本行賣出,即期賣出,遠期×7
    因此用「本行買入 / 本行賣出」標籤後面的第一個數值定位現金買賣價，
    不依賴欄位索引，台銀日後調整欄位也不會抓錯。
    """
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0 (anvia-rate-bot)'})
    response.raise_for_status()

    # 台銀未必在標頭指明編碼，requests 此時會退回 ISO-8859-1 而讓中文變亂碼，
    # 所以自行嘗試常見編碼，取第一個能解出「本行買入」的結果
    text = ''
    for encoding in ('utf-8', 'big5', 'cp950'):
        try:
            decoded = response.content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if '本行買入' in decoded:
            text = decoded
            break
    if not text:
        raise ValueError('BoT CSV could not be decoded as utf-8/big5/cp950')

    for line in text.splitlines():
        cols = [c.strip() for c in line.split(',')]
        if cols and cols[0] == 'CNY':
            cash_buy = first_value_after(cols, '本行買入')
            cash_sell = first_value_after(cols, '本行賣出')
            # 合理範圍檢查，避免台銀改版或回傳異常值
            if not (2 < cash_buy < 10 and 2 < cash_sell < 10 and cash_buy < cash_sell):
                raise ValueError(f'BoT CNY rate out of range: buy={cash_buy}, sell={cash_sell}')
            now = now_dt()
            mid = (cash_buy + cash_sell) / 2
            return {
                "rate": round(mid, 4),
                "time": fmt(now),
                "source": "台銀",
                "rate_date": now.strftime('%Y-%m-%d'),
            }
    raise ValueError('CNY row not found in BoT CSV')


def carry_over_bot_rate():
    """台銀取不到時（週末、國定假日或端點異常）沿用上一次的台銀牌告。

    只更新檢查時間，rate 與 rate_date 保持不變，讓網站能顯示這筆匯率
    實際上是哪一天的牌告。超過 MAX_CARRY_OVER_DAYS 就不再沿用。
    """
    if not os.path.exists('rate.json'):
        raise ValueError('no previous rate.json to carry over')

    with open('rate.json', encoding='utf-8') as f:
        prev = json.load(f)

    if prev.get('source') != '台銀' or not prev.get('rate'):
        raise ValueError('previous rate.json is not a BoT rate')

    # 舊格式沒有 rate_date 時，用 time 的日期部分當作牌告日
    rate_date = prev.get('rate_date') or str(prev.get('time', ''))[:10]
    try:
        rate_dt = TW_TZ.localize(datetime.strptime(rate_date, '%Y-%m-%d'))
    except ValueError:
        raise ValueError(f'previous rate_date unusable: {rate_date!r}')

    age = now_dt() - rate_dt
    if age > timedelta(days=MAX_CARRY_OVER_DAYS):
        raise ValueError(f'previous BoT rate too old ({rate_date})')

    return {
        "rate": prev['rate'],
        "time": fmt(now_dt()),
        "source": "台銀",
        "rate_date": rate_date,
    }


def get_erapi_rate():
    # 最後手段：全球通用匯率 API (CNY 對 TWD，市場中間價，每日更新一次)
    url = "https://open.er-api.com/v6/latest/CNY"
    response = requests.get(url, timeout=30)
    data = response.json()
    if data["result"] == "success":
        now = now_dt()
        return {
            "rate": round(data["rates"]["TWD"], 4),
            "time": fmt(now),
            "source": "exchangerate",
            "rate_date": now.strftime('%Y-%m-%d'),
        }
    raise ValueError('er-api returned non-success result')


data = None
for label, getter in (
    ('BoT', get_bot_rate),
    ('carry-over', carry_over_bot_rate),
    ('er-api', get_erapi_rate),
):
    try:
        data = getter()
        break
    except Exception as e:
        print(f'{label} unavailable: {e}')

if data:
    with open('rate.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f'Updated: {data}')
else:
    print('All rate sources failed; rate.json left unchanged')
