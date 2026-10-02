#!/usr/bin/env python3
"""下載台股上市＋上櫃每日行情與加權指數，累積成 data/history.csv（只用標準函式庫）。
用法：python update_data.py [--days 150]
第一次執行會回補最近 N 個平日（約 15~20 分鐘，因為要避開證交所的流量限制），之後每天只補新的一天。"""
import argparse, csv, json, re, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA = Path('data'); HIST = DATA / 'history.csv'; SKIP = DATA / 'holidays.txt'; INDF = DATA / 'industry.json'
COLS = ['date', 'code', 'name', 'industry', 'open', 'high', 'low', 'close', 'volume']
SLEEP = 3.5
UA = {'User-Agent': 'Mozilla/5.0 (tw-screener)'}
IND = dict(x.split('=') for x in ('01=水泥工業,02=食品工業,03=塑膠工業,04=紡織纖維,05=電機機械,06=電器電纜,08=玻璃陶瓷,09=造紙工業,'
  '10=鋼鐵工業,11=橡膠工業,12=汽車工業,14=建材營造,15=航運業,16=觀光餐旅,17=金融保險,18=貿易百貨,19=綜合,20=其他,21=化學工業,'
  '22=生技醫療,23=油電燃氣,24=半導體,25=電腦及週邊,26=光電,27=通信網路,28=電子零組件,29=電子通路,30=資訊服務,31=其他電子,'
  '32=文化創意,33=農業科技,34=電子商務,35=綠能環保,36=數位雲端,37=運動休閒,38=居家生活').split(','))
URL = {
 'twse': 'https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={:%Y%m%d}&type=ALLBUT0999&response=json',
 'tpex': 'https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?date={:%Y/%m/%d}&type=EW&response=json',
 'taiex': 'https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={:%Y%m}01&response=json',
 'ind': ['https://openapi.twse.com.tw/v1/opendata/t187ap03_L', 'https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O'],
}

def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                body = r.read().decode('utf-8')
            time.sleep(SLEEP)
            return json.loads(body)
        except Exception as e:
            print(f'  重試 {i+1}: {e}', file=sys.stderr); time.sleep(5 * (i + 1))
    return None

def num(s):
    try: return float(str(s).replace(',', '').strip())
    except ValueError: return None

def col(fields, *keys):
    for k in keys:
        for i, f in enumerate(fields):
            if k in f: return i
    return None

def quotes(market, d):
    """回傳某市場某日所有 4 位數代號股票的 OHLCV；沒資料（假日、停市）回傳 []。"""
    js = get(URL[market].format(d))
    for t in (js or {}).get('tables') or []:
        f, data = t.get('fields') or [], t.get('data') or []
        ic, ix = col(f, '代號'), col(f, '收盤')
        if ic is None or ix is None or not data: continue
        inm, io, ih, il, iv = col(f, '名稱'), col(f, '開盤'), col(f, '最高'), col(f, '最低'), col(f, '成交股數', '成交量')
        out = []
        for r in data:
            code = str(r[ic]).strip()
            if not re.fullmatch(r'\d{4}', code): continue          # 排除 ETF、權證、特別股
            o, h, l, c, v = (num(r[i]) for i in (io, ih, il, ix, iv))
            if None in (o, h, l, c, v) or v <= 0: continue          # 停牌或未成交
            out.append(dict(date=d.isoformat(), code=code, name=str(r[inm]).strip().replace(',', ' '), industry='',
                            open=o, high=h, low=l, close=c, volume=int(v)))
        return out
    return []

def taiex_month(d):
    js = get(URL['taiex'].format(d)) or {}
    if not js.get('fields') and js.get('tables'): js = js['tables'][0]
    f, data = js.get('fields') or [], js.get('data') or []
    if not f: return []
    idt, io, ih, il, ic = col(f, '日期'), col(f, '開盤'), col(f, '最高'), col(f, '最低'), col(f, '收盤')
    out = []
    for r in data:
        y, m, dd = (int(x) for x in str(r[idt]).split('/'))
        o, h, l, c = (num(r[i]) for i in (io, ih, il, ic))
        if None in (o, h, l, c): continue
        out.append(dict(date=date(y + 1911 if y < 1911 else y, m, dd).isoformat(), code='TAIEX', name='加權指數',
                        industry='指數', open=o, high=h, low=l, close=c, volume=0))
    return out

def industry_map():
    m = json.loads(INDF.read_text(encoding='utf-8')) if INDF.exists() else {}
    for url in URL['ind']:
        for r in get(url) or []:
            code = next((v for k, v in r.items() if re.search('公司代號|Code', k)), None)
            ind = next((v for k, v in r.items() if re.search('產業別|Industry', k)), None)
            if code and ind: m[str(code).strip()] = IND.get(str(ind).strip(), str(ind).strip())
    INDF.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
    return m

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=150); a = ap.parse_args(argv)
    DATA.mkdir(exist_ok=True)
    today = datetime.now(timezone(timedelta(hours=8))).date()
    want, d = [], today
    while len(want) < a.days:
        if d.weekday() < 5: want.append(d)
        d -= timedelta(days=1)
    want.sort()
    rows = {}
    if HIST.exists():
        for r in csv.DictReader(HIST.open(encoding='utf-8')): rows[(r['date'], r['code'])] = r
    have = {k[0] for k in rows if k[1] != 'TAIEX'}
    skip = set(SKIP.read_text().split()) if SKIP.exists() else set()
    for d in want:
        s = d.isoformat()
        if s in have or s in skip: continue
        print('下載', s, flush=True)
        got = quotes('twse', d)
        if not got:
            if d < today: skip.add(s)                              # 過去的空資料日＝休市，記下來不再重抓
            continue
        tp = quotes('tpex', d)
        if not tp: print('  警告：上櫃沒有資料', file=sys.stderr)
        for r in got + tp: rows[(s, r['code'])] = r
    SKIP.write_text('\n'.join(sorted(skip)), encoding='utf-8')
    cut = want[0].isoformat()
    for ym in sorted({(d.year, d.month) for d in want}):
        for r in taiex_month(date(ym[0], ym[1], 1)):
            if cut <= r['date'] <= today.isoformat(): rows[(r['date'], 'TAIEX')] = r
    rows = {k: v for k, v in rows.items() if k[0] >= cut}
    im = industry_map()
    for r in rows.values():
        if r['code'] != 'TAIEX': r['industry'] = im.get(r['code'], '其他')
    with HIST.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, COLS); w.writeheader()
        for k in sorted(rows, key=lambda k: (k[1], k[0])): w.writerow({c: rows[k][c] for c in COLS})
    print(f'完成：{len(rows)} 列，{len({k[1] for k in rows})} 檔（含 TAIEX）')

if __name__ == '__main__': main()
