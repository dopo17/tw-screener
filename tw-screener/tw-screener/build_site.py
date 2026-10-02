#!/usr/bin/env python3
"""讀 data/history.csv，把資料嵌進 template.html，輸出 docs/index.html（GitHub Pages 用）。"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path

K, MIN_DAYS, MIN_AVG_LOTS = 130, 70, 500      # 保留天數／最少天數／20 日均量下限（張）

def main():
    rows = defaultdict(list)
    for r in csv.DictReader(open('data/history.csv', encoding='utf-8')): rows[r['code']].append(r)
    last = max(r['date'] for c, a in rows.items() if c != 'TAIEX' for r in a)
    stocks, idx = [], []
    for code, a in sorted(rows.items()):
        a.sort(key=lambda r: r['date']); a = a[-K:]
        if code == 'TAIEX': idx = [round(float(r['close']), 2) for r in a]; continue
        if len(a) < MIN_DAYS or a[-1]['date'] != last: continue
        v = [int(r['volume']) / 1000 for r in a]
        if sum(v[-20:]) / 20 < MIN_AVG_LOTS: continue
        q = lambda k: [round(float(r[k]), 2) for r in a]
        stocks.append(dict(code=code, name=a[-1]['name'], ind=a[-1]['industry'], o=q('open'), h=q('high'),
                           l=q('low'), c=q('close'), v=[round(x) for x in v]))
    if len(idx) < 60 or len(stocks) < 20:
        sys.exit(f'資料不足（大盤 {len(idx)} 天、合格股票 {len(stocks)} 檔），先不產生網頁。請用預設天數完整回補一次。')
    blob = json.dumps(dict(s=stocks, x=idx, d=last), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    t = Path('template.html').read_text(encoding='utf-8')
    assert t.count('const EMB=null;') == 1
    Path('docs').mkdir(exist_ok=True)
    Path('docs/index.html').write_text(t.replace('const EMB=null;', f'const EMB={blob};'), encoding='utf-8')
    print(f'已輸出 docs/index.html：{len(stocks)} 檔，截至 {last}，約 {len(blob)//1024} KB')

if __name__ == '__main__': main()
