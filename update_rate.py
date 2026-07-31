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


def get_bot_rate():
    """台灣銀行牌告匯率 CSV，取人民幣「現金買入/賣出」中間價。

    標題列格式為 幣別,匯率,現金,匯率,即期,遠期...,匯率,現金,匯率,即期,遠期...
    前半段是本行買入、後半段是本行賣出，所以兩個「現金」欄位分別對應
    現金買入與現金賣出。用標題定位而非寫死索引，台銀調整欄位也不會抓錯。
    """
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # 台銀未必在標頭指明編碼，requests 此時會退回 ISO-8859-1 而讓中文變亂碼，
    # 所以自行嘗試常見編碼，取第一個能解出「現金」的結果
    text = ''
    for encoding in ('utf-8', 'big5', 'cp950'):
        try:
            decoded = response.content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if '現金' in decoded:
            text = decoded
            break
    if not text:
        raise ValueError('BoT CSV could not be decoded as utf-8/big5/cp950')

    lines = text.splitlines()
    header = [c.strip() for c in lines[0].split(',')]
    cash_cols = [i for i, name in enumerate(header) if name == '現金']
    if len(cash_cols) < 2:
        raise ValueError(f'BoT CSV header unrecognised: {header}')
    buy_col, sell_col = cash_cols[0], cash_cols[1]

    for line in lines[1:]:
        cols = line.split(',')
        if cols and cols[0].strip() == 'CNY':
            cash_buy = float(cols[buy_col])
            cash_sell = float(cols[sell_col])
            # 合理範圍檢查，避免欄位位移或台銀回傳異常值
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
