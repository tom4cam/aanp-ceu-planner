"""Merge curated (precise) + full directory into places.js (window.PLACES).
Curated entries win over directory entries that share the same official map number
or the same name, so the hand-placed precise pins replace the area-level directory rows."""
import json, os

def merge(extra, curated):
    by_name = {p['name'].strip().lower() for p in curated}
    by_num = {str(p['num']).strip() for p in curated if p.get('num')}
    out = list(curated)
    for p in extra:
        if str(p.get('num', '')).strip() and str(p['num']).strip() in by_num:
            continue  # curated has this venue precisely placed
        if p['name'].strip().lower() in by_name:
            continue
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
    directory = _load('places_directory.json')   # full venue list (placed:false, area-level + #num)
    raw = _load('places_raw.json')                # legacy best-effort scrape (usually empty)
    curated = _load('places_curated.json')        # hand-placed precise pins (placed:true)
    places = merge(directory + raw, curated)
    with open('places.js', 'w', encoding='utf-8') as f:
        f.write(to_js(places))
    print(f"wrote places.js with {len(places)} places ({len(curated)} curated + {len(directory)} directory, dedup applied)")

if __name__ == '__main__':
    main()
