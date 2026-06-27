"""Best-effort scraper for the Venetian / Grand Canal Shoppes directory.
parse_directory() is pure + tested; main() fetches with urllib and tolerates failure.
The curated set (places_curated.json) is the real backbone; this fills the browse long-tail."""
import json, re, sys, urllib.request
from html.parser import HTMLParser

SOURCES = [
    # (url, area). URLs may change / be JS-rendered; failure is tolerated.
    ("https://www.grandcanalshoppes.com/en/stores.html", "Grand Canal Shoppes"),
]

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

# Order matters: a strong "sit-down" signal (e.g. raw_cat "Restaurant") must win
# over an incidental 'cafe' substring in the name (e.g. "Grand Lux Cafe").
def categorize(name, raw_cat):
    t = f"{name} {raw_cat}".lower()
    if any(w in t for w in ['restaurant', 'grill', 'kitchen', 'trattoria', 'steak', 'dining', 'bar']): return 'sitdown'
    if any(w in t for w in ['cafe', 'coffee', 'bakery', 'espresso', 'starbucks']): return 'coffee'
    if any(w in t for w in ['pizza', 'burger', 'taco', 'food', 'snack', 'gelato', 'ice cream', 'noodle']): return 'food'
    if any(w in t for w in ['pharmacy', 'walgreens', 'cvs', 'sundries', 'drug']): return 'essentials'
    return 'shop'

class _Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_card = False
        self._cat = ''
        self._capture = None       # 'name' | 'cat' | None
        self._capture_tag = None   # the tag that opened the current capture
        self._name = ''
        self._catt = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '').split()   # token match, not substring (avoids "flashcard")
        if 'card' in cls:
            self._in_card = True; self._cat = a.get('data-category', ''); self._name=''; self._catt=''
        elif self._in_card and 'name' in cls:
            self._capture = 'name'; self._capture_tag = tag
        elif self._in_card and 'cat' in cls:
            self._capture = 'cat'; self._capture_tag = tag
    def handle_data(self, data):
        if self._capture == 'name': self._name += data
        elif self._capture == 'cat': self._catt += data
    def handle_endtag(self, tag):
        # Only end the capture when ITS element closes, so nested inline markup
        # (e.g. <a class="name"><strong>X</strong> Y</a>) keeps the full text.
        if self._capture and tag == self._capture_tag:
            self._capture = None; self._capture_tag = None
        if self._in_card and tag == 'li':
            name = self._name.strip()
            if name:
                self.rows.append((name, (self._catt or self._cat).strip()))
            self._in_card = False

def parse_directory(html, area):
    p = _Cards(); p.feed(html)
    out = []
    for name, raw_cat in p.rows:
        out.append({
            'id': f"{slugify(area)[:4]}-{slugify(name)}",
            'name': name,
            'cat': categorize(name, raw_cat),
            'sub': raw_cat or '',
            'area': area,
            'placed': False,
        })
    return out

def main():
    rows = []
    for url, area in SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                html = r.read().decode('utf-8', 'replace')
            rows.extend(parse_directory(html, area))
        except Exception as e:
            print(f"WARN: fetch failed for {url}: {e}", file=sys.stderr)
    with open('places_raw.json', 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)
    print(f"wrote places_raw.json with {len(rows)} rows")

if __name__ == '__main__':
    main()
