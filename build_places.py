"""Merge curated + scraped places into places.js (window.PLACES)."""
import json, os

def merge(raw, curated):
    by_name = {}
    out = []
    for p in curated:
        key = p['name'].strip().lower()
        by_name[key] = True
        out.append(p)
    for p in raw:
        key = p['name'].strip().lower()
        if key in by_name:
            continue  # curated wins
        out.append(p)
    return out

def to_js(places):
    return 'window.PLACES = ' + json.dumps(places, ensure_ascii=False, indent=0) + ';\n'

def _load(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return []

def main():
    raw = _load('places_raw.json')
    curated = _load('places_curated.json')
    places = merge(raw, curated)
    with open('places.js', 'w', encoding='utf-8') as f:
        f.write(to_js(places))
    print(f"wrote places.js with {len(places)} places ({len(curated)} curated, {len(raw)} raw)")

if __name__ == '__main__':
    main()
