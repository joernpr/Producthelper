#!/usr/bin/env python3
"""Liest den Veranstaltungskalender von phoenixcontact.com und schreibt termine.json.

Aufruf:  python scripts/termine.py [Zieldatei]          (Standard: termine.json)
         python scripts/termine.py termine.json --browser   (Abruf über Chromium/Playwright)
Exit-Codes: 0 = ok, 2 = Seite blockiert/nicht erreichbar, 3 = Seite geändert (zu wenige Termine)
Bei einem Fehler bleibt die bisherige termine.json unverändert.
"""
import html, json, re, sys, urllib.request, datetime, os

URL = 'https://www.phoenixcontact.com/de-de/events-und-news/events-und-seminare'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0')


def fetch_plain():
    req = urllib.request.Request(URL, headers={
        'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def fetch_browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA, locale='de-DE')
        pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
        pg.wait_for_selector('a.ex-do-item', timeout=60000)
        h = pg.content()
        b.close()
        return h


def text(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def field(block, cls):
    m = re.search(r'<(\w+)[^>]*class="[^"]*\b' + re.escape(cls) + r'\b[^"]*"[^>]*>(.*?)</\1>', block, re.S)
    return text(m.group(2)) if m else ''


def parse(page):
    events = []
    for m in re.finditer(r'<a\s+class="ex-do-item\b([^"]*)"([^>]*)>(.*?)</a>', page, re.S):
        cls, attrs, block = m.groups()
        href = re.search(r'href="([^"]*)"', attrs)
        u = html.unescape(href.group(1)) if href else ''
        if u.startswith('/'):
            u = 'https://www.phoenixcontact.com' + u
        dates = re.findall(r'<div class="ex-do-item__text-content__date( ex-do-item__text-content__date-to)?">\s*([0-9.]+)\s*</div>', block)
        start = next((d for to, d in dates if not to), '')
        end = next((d for to, d in dates if to), None)
        title = field(block, 'ex-do-item__headline__title')
        if not title or not re.match(r'\d{2}\.\d{2}\.\d{4}$', start):
            continue
        typ = re.search(r'ex-teaser-type-(\w+)', cls)
        events.append({'title': title, 'place': field(block, 'ex-do-item__headline__location'),
                       'start': start, 'end': end, 'desc': field(block, 'ex-do-item__text-content__text'),
                       'u': u, 'typ': typ.group(1) if typ else ''})
    return events


def main():
    out = next((a for a in sys.argv[1:] if not a.startswith('--')), 'termine.json')
    try:
        page = fetch_browser() if '--browser' in sys.argv else fetch_plain()
    except Exception as e:  # 403 (Bot-Schutz), Zeitüberschreitung …
        print('Abruf fehlgeschlagen:', e)
        return 2
    ev = parse(page)
    print('Gefundene Termine:', len(ev))
    if len(ev) < 5:
        print('Zu wenige Termine – Seite blockiert oder geändert. termine.json bleibt unverändert.')
        return 2 if ('Access Denied' in page or len(page) < 20000) else 3
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
    data = {'stand': now.strftime('%d.%m.%Y'), 'quelle': URL, 'events': ev}
    old = None
    if os.path.exists(out):
        try:
            old = json.load(open(out, encoding='utf-8'))
        except Exception:
            pass
    if old and old.get('events') == ev and old.get('stand') == data['stand']:
        print('Keine Änderung.')
        return 0
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('Geschrieben:', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
