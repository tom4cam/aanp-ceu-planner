# Food & Shops Maps + Proximity Directions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browsable/searchable Venetian/Palazzo/Expo shops & restaurants directory that sorts by estimated walking distance from Sarah's next session, with maps, foot-injury-aware walk hints, and an "Open in Maps" handoff.

**Architecture:** Extend the existing static `index.html` app. Pure logic (map metadata, a hand-tuned cross-building zone graph, `walkBetween`, hint text, open-now, filter/sort) lives in a new dependency-free `places-engine.js` (UMD: `window.PlacesEngine` in browser, `require()` in Node). A Python pipeline (`scrape_places.py` + hand-authored `places_curated.json` → `build_places.py`) emits `places.js` (`window.PLACES`). The new **🍽️ Food & Shops** tab renders the directory and reuses the existing `.lvlmap` SVG + `openMapModal` fullscreen zoom for the map view.

**Tech Stack:** Vanilla JS (inline + `places-engine.js`), Python 3 stdlib (`urllib`, `html.parser`, `json`), no build step, no npm/pip deps. GitHub Pages static hosting.

## Testing strategy (repo-consistent)

- **Pure JS logic** (`places-engine.js`): automated with Node's built-in runner — `node --test tests/`. No DOM, no deps.
- **Python pipeline** (`scrape_places.py`, `build_places.py`): automated with stdlib `unittest` — `python3 -m unittest discover -s tests -p 'test_*.py'`.
- **Data** (`places_curated.json`, generated `places.js`): schema-validated by an automated test.
- **DOM/UI** (`index.html` edits): verified manually in the browser with explicit expected outcomes, plus cheap `grep` smoke checks. This matches the repo's established practice (no DOM test harness exists, and adding Playwright is disproportionate for this app).

## Global Constraints

- No new runtime dependencies (no npm, no pip). Browser code is plain `<script>`; Node/Python use built-ins only.
- All app state stays in `localStorage`; no backend; repo is **public** — never commit secrets, personal data, or the `/exec` URL.
- "Open in Maps" URLs carry only `<place name> Venetian Las Vegas` — no personal data in query strings.
- Phone-first; reuse existing CSS variables/classes and the existing `.lvlmap` / `openMapModal` / `setupZoom` map machinery.
- Cache-busting: every `<script src>` in `index.html` uses `?v=<version>`; bump `version.txt` (format `YYYY-MM-DD.N`) on deploy.
- Coordinates are normalized 0–1 floats per map image. Map ids: `expo2, expo3, expo4, expo5, gcs, palazzo`.
- Zones: `expo, palazzo, gcs, casino`. Walk times are honest estimates surfaced as "~N min".

---

## File Structure

- **Create** `places-engine.js` — pure: `MAP_META`, `ZONES`, `ZONE_LABEL`, `AREA_ANCHOR`, `zoneOf`, `walkBetween`, `formatHint`, `isOpenNow`, `filterPlaces`, `sortByWalk`.
- **Create** `places_curated.json` — hand-authored ~30–50 high-value places with precise coords.
- **Create** `scrape_places.py` — fetch + parse directory pages → `places_raw.json` (best-effort, fixture-tested).
- **Create** `build_places.py` — merge raw + curated → `places.js`.
- **Create** `maps/gcs.jpg`, `maps/palazzo.jpg` — retail/dining base maps (~150 KB each).
- **Create** `tests/places-engine.test.js`, `tests/places-data.test.js`, `tests/test_scrape_places.py`, `tests/test_build_places.py`.
- **Create** `places_raw.json` (generated), `places.js` (generated).
- **Modify** `index.html` — load scripts; generalize `LVL_IMG`→`PlacesEngine.MAP_META`; add `food` tab (markup + `show()`/`renderActive` + `renderFood` + origin selector + filters + place map view).
- **Modify** `version.txt` — bump.

---

### Task 1: Walk engine core — `MAP_META`, `ZONES`, `walkBetween`

**Files:**
- Create: `places-engine.js`
- Test: `tests/places-engine.test.js`

**Interfaces:**
- Consumes: nothing (leaf module).
- Produces (browser `window.PlacesEngine`, Node `module.exports`):
  - `MAP_META`: `{ [mapId]: {lvl:number, zone:string, img:string, label:string} }`
  - `ZONES`: `{ [zone]: { [zone]: minutes:number } }`
  - `ZONE_LABEL`: `{ [zone]: string }`
  - `zoneOf(mapId:string) -> string|null`
  - `walkBetween(a, b) -> {minutes:number, sameMap:boolean, zoneChange:boolean, far:boolean, from:string, to:string}` where `a`,`b` are `{mapId:string, x:number, y:number}`

- [ ] **Step 1: Write the failing test**

```js
// tests/places-engine.test.js
const test = require('node:test');
const assert = require('node:assert');
const E = require('../places-engine.js');

test('MAP_META covers all six maps with zone+img', () => {
  for (const id of ['expo2','expo3','expo4','expo5','prop1','prop2']) {
    assert.ok(E.MAP_META[id], `missing ${id}`);
    assert.equal(typeof E.MAP_META[id].zone, 'string');
    assert.match(E.MAP_META[id].img, /\.jpg$/);
  }
});

test('zoneOf maps id to zone', () => {
  assert.equal(E.zoneOf('expo4'), 'expo');
  assert.equal(E.zoneOf('prop2'), 'property');
  assert.equal(E.zoneOf('nope'), null);
});

test('walkBetween same map returns short, non-zoneChange', () => {
  const r = E.walkBetween({mapId:'expo3',x:0.3,y:0.2}, {mapId:'expo3',x:0.32,y:0.22});
  assert.equal(r.sameMap, true);
  assert.equal(r.zoneChange, false);
  assert.ok(r.minutes >= 1 && r.minutes < 4, `got ${r.minutes}`);
});

test('walkBetween same zone different level adds a level penalty', () => {
  const near = E.walkBetween({mapId:'expo3',x:0.5,y:0.5}, {mapId:'expo3',x:0.5,y:0.5}).minutes;
  const up = E.walkBetween({mapId:'expo3',x:0.5,y:0.5}, {mapId:'expo5',x:0.5,y:0.5}).minutes;
  assert.ok(up > near, `expected level change ${up} > ${near}`);
});

test('walkBetween across zones uses ZONES graph and flags far', () => {
  const r = E.walkBetween({mapId:'expo2',x:0.5,y:0.5}, {mapId:'prop2',x:0.5,y:0.5});
  assert.equal(r.zoneChange, true);
  assert.ok(r.minutes >= E.ZONES.expo.property, `got ${r.minutes}`);
  assert.equal(r.far, true);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/places-engine.test.js`
Expected: FAIL — `Cannot find module '../places-engine.js'`.

- [ ] **Step 3: Write minimal implementation**

```js
// places-engine.js
(function (root) {
  const MAP_META = {
    expo2:   { lvl:2, zone:'expo',     img:'floorplans/level2.jpg', label:'Expo Level 2' },
    expo3:   { lvl:3, zone:'expo',     img:'floorplans/level3.jpg', label:'Expo Level 3' },
    expo4:   { lvl:4, zone:'expo',     img:'floorplans/level4.jpg', label:'Expo Level 4' },
    expo5:   { lvl:5, zone:'expo',     img:'floorplans/level5.jpg', label:'Expo Level 5' },
    // Official Venetian/Palazzo property maps (two levels of one connected complex).
    prop1:   { lvl:1, zone:'property', img:'maps/prop1.jpg', label:'Venetian/Palazzo — Level 1' },
    prop2:   { lvl:2, zone:'property', img:'maps/prop2.jpg', label:'Grand Canal Shoppes — Level 2' }
  };
  // Hand-tuned walking minutes between zones (symmetric). Estimates, surfaced as "~N min".
  // The Expo Convention Center connects to the Venetian/Palazzo complex via the walkway (~7 min).
  // Within 'property', prop1<->prop2 is a level change (handled by the LEVEL_MIN penalty, not here).
  const ZONES = {
    expo:     { property:7 },
    property: { expo:7 }
  };
  const ZONE_LABEL = { expo:'Expo', property:'Venetian/Palazzo' };

  const UNIT_MIN = 8;   // minutes per 1.0 of normalized distance across a single map
  const LEVEL_MIN = 3;  // minutes per level change within a zone (elevator wait+ride)
  const FAR_MIN = 7;    // walks longer than this are "far" (foot-injury flag)

  function zoneOf(mapId){ return MAP_META[mapId] ? MAP_META[mapId].zone : null; }

  function sameMapMinutes(a, b){
    const dx=a.x-b.x, dy=a.y-b.y;
    return Math.sqrt(dx*dx+dy*dy) * UNIT_MIN;
  }

  function walkBetween(a, b){
    const za = zoneOf(a.mapId), zb = zoneOf(b.mapId);
    const ma = MAP_META[a.mapId], mb = MAP_META[b.mapId];
    let minutes, sameMap=false, zoneChange=false;
    if (a.mapId === b.mapId){
      sameMap = true;
      minutes = sameMapMinutes(a, b);
    } else if (za && zb && za === zb){
      // same zone, different map/level
      minutes = sameMapMinutes(a, b) + LEVEL_MIN * Math.abs((ma?ma.lvl:0) - (mb?mb.lvl:0));
    } else if (za && zb && ZONES[za] && ZONES[za][zb] != null){
      zoneChange = true;
      minutes = ZONES[za][zb] + 1; // +1 buffer for the two intra-map legs
    } else {
      zoneChange = true;
      minutes = 12; // unknown pairing fallback
    }
    minutes = Math.max(1, Math.round(minutes));
    return { minutes, sameMap, zoneChange, far: minutes > FAR_MIN, from: a.mapId, to: b.mapId };
  }

  const API = { MAP_META, ZONES, ZONE_LABEL, zoneOf, walkBetween };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.PlacesEngine = API;
})(typeof window !== 'undefined' ? window : globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/places-engine.test.js`
Expected: PASS — 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add places-engine.js tests/places-engine.test.js
git commit -m "feat(places): walk engine core (MAP_META, ZONES, walkBetween)"
```

---

### Task 2: Engine — `formatHint` + `isOpenNow`

**Files:**
- Modify: `places-engine.js`
- Test: `tests/places-engine.test.js` (append)

**Interfaces:**
- Consumes: Task 1 (`MAP_META`, `ZONE_LABEL`, `zoneOf`, `walkBetween` result shape).
- Produces:
  - `formatHint(result, opts) -> string` where `result` is a `walkBetween` return and `opts` is `{stepFree?:boolean}`.
  - `isOpenNow(place, now) -> boolean|null` where `now` is `{day:0..6, minutes:0..1439}` (0=Sunday) and `place.open` is either `[openMin, closeMin]` (daily) or `{ '0'..'6': [openMin, closeMin] }`; returns `null` when `place.open` is absent.

- [ ] **Step 1: Write the failing test**

```js
// append to tests/places-engine.test.js
test('formatHint same map mentions the map label and step-free', () => {
  const r = E.walkBetween({mapId:'expo3',x:0.2,y:0.2},{mapId:'expo3',x:0.3,y:0.3});
  const s = E.formatHint(r, {stepFree:true});
  assert.match(s, /~\d+ min/);
  assert.match(s, /Expo Level 3/);
  assert.match(s, /step-free/);
});

test('formatHint across zones shows from -> to zone labels', () => {
  const r = E.walkBetween({mapId:'expo2',x:0.5,y:0.5},{mapId:'gcs',x:0.5,y:0.5});
  const s = E.formatHint(r, {});
  assert.match(s, /Expo/);
  assert.match(s, /Grand Canal Shoppes/);
  assert.match(s, /→/);
});

test('isOpenNow handles daily array, per-day object, and missing', () => {
  assert.equal(E.isOpenNow({open:[600, 1320]}, {day:3, minutes:700}), true);   // 10:00–22:00, now 11:40
  assert.equal(E.isOpenNow({open:[600, 1320]}, {day:3, minutes:1380}), false);  // 23:00
  assert.equal(E.isOpenNow({open:{'3':[600,1320],'0':[0,0]}}, {day:0, minutes:700}), false); // closed Sun
  assert.equal(E.isOpenNow({}, {day:3, minutes:700}), null);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/places-engine.test.js`
Expected: FAIL — `E.formatHint is not a function`.

- [ ] **Step 3: Write minimal implementation**

Insert these functions inside the IIFE (before `const API`):

```js
  function formatHint(result, opts){
    opts = opts || {};
    const mins = `~${result.minutes} min`;
    let where;
    if (result.sameMap){
      where = MAP_META[result.from] ? MAP_META[result.from].label : '';
    } else if (zoneOf(result.from) === zoneOf(result.to)){
      const fl = MAP_META[result.from] ? MAP_META[result.from].label : '';
      const tl = MAP_META[result.to] ? MAP_META[result.to].label : '';
      where = `${fl} → ${tl} (elevator)`;
    } else {
      const fz = ZONE_LABEL[zoneOf(result.from)] || '';
      const tz = ZONE_LABEL[zoneOf(result.to)] || '';
      where = `${fz} → ${tz}`;
    }
    let s = `${mins} · ${where}`;
    if (opts.stepFree) s += ' · step-free';
    return s;
  }

  function isOpenNow(place, now){
    if (!place || !place.open) return null;
    let span = place.open;
    if (!Array.isArray(span)) span = span[String(now.day)];
    if (!span || span.length !== 2) return null;
    const [o, c] = span;
    if (o === c) return false; // closed all day
    return now.minutes >= o && now.minutes < c;
  }
```

Add `formatHint, isOpenNow` to the `API` object.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/places-engine.test.js`
Expected: PASS — all Task 1 + Task 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add places-engine.js tests/places-engine.test.js
git commit -m "feat(places): formatHint + isOpenNow"
```

---

### Task 3: Engine — `AREA_ANCHOR`, `filterPlaces`, `sortByWalk`

**Files:**
- Modify: `places-engine.js`
- Test: `tests/places-engine.test.js` (append)

**Interfaces:**
- Consumes: Task 1–2.
- Produces:
  - `AREA_ANCHOR`: `{ [area]: {mapId, x, y} }` — coarse location for long-tail (`placed:false`) places.
  - `placeLoc(place) -> {mapId,x,y}|null` — precise loc if `placed`, else `AREA_ANCHOR[place.area]`.
  - `filterPlaces(places, opts) -> place[]` where `opts` is `{q?:string, cats?:string[], areas?:string[], openNow?:boolean, stepFree?:boolean, now?:{day,minutes}}`.
  - `sortByWalk(places, originLoc) -> place[]` — returns a new array; each element is a shallow clone with `_walk` (a `walkBetween` result) added, ascending by `_walk.minutes`.

- [ ] **Step 1: Write the failing test**

```js
// append to tests/places-engine.test.js
const SAMPLE = [
  {id:'a', name:'Grand Lux Cafe', cat:'sitdown', area:'Grand Canal Shoppes', placed:true, map:'prop2', x:0.4, y:0.5, stepFree:true, open:[600,1320]},
  {id:'b', name:'Starbucks Expo', cat:'coffee', area:'Expo', placed:true, map:'expo2', x:0.5, y:0.5, open:[420,1080]},
  {id:'c', name:'Tory Burch', cat:'shop', area:'Grand Canal Shoppes', placed:false, open:[600,1260]}
];

test('placeLoc falls back to area anchor for unplaced', () => {
  assert.deepEqual(E.placeLoc(SAMPLE[1]), {mapId:'expo2', x:0.5, y:0.5});
  const c = E.placeLoc(SAMPLE[2]);
  assert.equal(c.mapId, E.AREA_ANCHOR['Grand Canal Shoppes'].mapId);
});

test('filterPlaces by category and query', () => {
  assert.deepEqual(E.filterPlaces(SAMPLE, {cats:['coffee']}).map(p=>p.id), ['b']);
  assert.deepEqual(E.filterPlaces(SAMPLE, {q:'tory'}).map(p=>p.id), ['c']);
});

test('filterPlaces stepFree keeps only step-free', () => {
  assert.deepEqual(E.filterPlaces(SAMPLE, {stepFree:true}).map(p=>p.id), ['a']);
});

test('filterPlaces openNow uses now and drops closed', () => {
  const out = E.filterPlaces(SAMPLE, {openNow:true, now:{day:3, minutes:300}}); // 5:00am, all closed
  assert.equal(out.length, 0);
});

test('sortByWalk orders by minutes from origin and adds _walk', () => {
  const origin = {mapId:'expo2', x:0.5, y:0.5};
  const out = E.sortByWalk(SAMPLE, origin);
  assert.equal(out[0].id, 'b'); // same map as origin → closest
  assert.ok(out[0]._walk.minutes <= out[1]._walk.minutes);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/places-engine.test.js`
Expected: FAIL — `E.sortByWalk is not a function`.

- [ ] **Step 3: Write minimal implementation**

Insert inside the IIFE (before `const API`):

```js
  const AREA_ANCHOR = {
    'Expo':                 {mapId:'expo2', x:0.50, y:0.50},
    'Grand Canal Shoppes':  {mapId:'prop2', x:0.50, y:0.50},
    'Venetian Level 1':     {mapId:'prop1', x:0.50, y:0.50},
    'Palazzo':              {mapId:'prop1', x:0.70, y:0.40},
    'Casino':               {mapId:'prop1', x:0.40, y:0.70}
  };

  function placeLoc(place){
    if (place.placed && place.map) return {mapId:place.map, x:place.x, y:place.y};
    return AREA_ANCHOR[place.area] || null;
  }

  function filterPlaces(places, opts){
    opts = opts || {};
    const q = (opts.q||'').trim().toLowerCase();
    const cats = opts.cats && opts.cats.length ? new Set(opts.cats) : null;
    const areas = opts.areas && opts.areas.length ? new Set(opts.areas) : null;
    return places.filter(p => {
      if (cats && !cats.has(p.cat)) return false;
      if (areas && !areas.has(p.area)) return false;
      if (opts.stepFree && !p.stepFree) return false;
      if (opts.openNow){ if (isOpenNow(p, opts.now) !== true) return false; }
      if (q){
        const hay = `${p.name} ${p.sub||''} ${p.area||''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }

  function sortByWalk(places, originLoc){
    return places.map(p => {
      const loc = placeLoc(p);
      const walk = (originLoc && loc) ? walkBetween(originLoc, loc) : {minutes:999, far:true, sameMap:false, zoneChange:true, from:'', to:''};
      return Object.assign({}, p, {_walk: walk});
    }).sort((a,b) => a._walk.minutes - b._walk.minutes);
  }
```

Add `AREA_ANCHOR, placeLoc, filterPlaces, sortByWalk` to `API`.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/places-engine.test.js`
Expected: PASS — all engine tests pass.

- [ ] **Step 5: Commit**

```bash
git add places-engine.js tests/places-engine.test.js
git commit -m "feat(places): filterPlaces + sortByWalk + area anchors"
```

---

### Task 4: Curated places seed + schema validation

**Files:**
- Create: `places_curated.json`
- Test: `tests/places-data.test.js`

**Interfaces:**
- Consumes: nothing (data file).
- Produces: `places_curated.json` — array of curated place objects matching the `PLACES` schema (all `placed:true`, with `map`/`x`/`y`).

- [ ] **Step 1: Write the failing test**

```js
// tests/places-data.test.js
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const E = require('../places-engine.js');

const CATS = new Set(['coffee','food','sitdown','essentials','restroom','shop','landmark']);

test('places_curated.json parses and every entry is valid + placed', () => {
  const arr = JSON.parse(fs.readFileSync(__dirname + '/../places_curated.json', 'utf8'));
  assert.ok(Array.isArray(arr) && arr.length >= 10, `expected >=10 curated, got ${arr.length}`);
  const ids = new Set();
  for (const p of arr){
    assert.ok(p.id && !ids.has(p.id), `dup/missing id: ${p.id}`); ids.add(p.id);
    assert.ok(p.name, `missing name on ${p.id}`);
    assert.ok(CATS.has(p.cat), `bad cat on ${p.id}: ${p.cat}`);
    assert.ok(E.AREA_ANCHOR[p.area], `bad area on ${p.id}: ${p.area}`);
    assert.equal(p.placed, true, `curated must be placed: ${p.id}`);
    assert.ok(E.MAP_META[p.map], `bad map on ${p.id}: ${p.map}`);
    assert.ok(p.x >= 0 && p.x <= 1 && p.y >= 0 && p.y <= 1, `bad coords on ${p.id}`);
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/places-data.test.js`
Expected: FAIL — `ENOENT … places_curated.json`.

- [ ] **Step 3: Create the curated seed**

Create `places_curated.json` with a starter set. Coordinates are approximate placements on each map (tune later by eye). Begin with this verified-structure seed (the executor extends toward ~30–50, but this passes the gate and is immediately usable):

```json
[
  {"id":"sbux-expo2","name":"Starbucks (Expo)","cat":"coffee","sub":"Coffee","area":"Expo","placed":true,"map":"expo2","x":0.78,"y":0.55,"price":"$","hours":"6a–6p","open":[360,1080],"stepFree":true,"note":"Closest coffee to the Expo halls."},
  {"id":"grandlux-prop2","name":"Grand Lux Cafe","cat":"sitdown","sub":"American","area":"Grand Canal Shoppes","placed":true,"map":"prop2","x":0.34,"y":0.42,"price":"$$","hours":"7a–11p","open":[420,1380],"stepFree":true,"note":"Reliable sit-down, broad menu."},
  {"id":"blacktap-prop2","name":"Black Tap","cat":"food","sub":"Burgers","area":"Grand Canal Shoppes","placed":true,"map":"prop2","x":0.55,"y":0.38,"price":"$$","hours":"11a–11p","open":[660,1380],"stepFree":true},
  {"id":"walgreens-prop1","name":"Walgreens","cat":"essentials","sub":"Pharmacy/Sundries","area":"Casino","placed":true,"map":"prop1","x":0.18,"y":0.82,"price":"$","hours":"Open 24h","open":[0,1440],"stepFree":true,"note":"Meds, snacks, water, blister care."},
  {"id":"restroom-expo2","name":"Restrooms — Expo Upper Lobby","cat":"restroom","sub":"Restroom","area":"Expo","placed":true,"map":"expo2","x":0.82,"y":0.63,"hours":"—","stepFree":true},
  {"id":"bouchon-prop2","name":"Bouchon Bakery","cat":"coffee","sub":"Bakery/Coffee","area":"Grand Canal Shoppes","placed":true,"map":"prop2","x":0.62,"y":0.30,"price":"$$","hours":"7a–6p","open":[420,1080],"stepFree":true}
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/places-data.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add places_curated.json tests/places-data.test.js
git commit -m "feat(places): curated places seed + schema test"
```

---

### Task 5: `scrape_places.py` — directory → `places_raw.json`

**Files:**
- Create: `scrape_places.py`
- Create: `tests/fixtures/gcs_sample.html`
- Test: `tests/test_scrape_places.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `parse_directory(html:str, area:str) -> list[dict]` returning `{id, name, cat, sub, area, placed:False}` entries; `main()` writes `places_raw.json`. `categorize(name:str, raw_cat:str) -> str` maps a site category/name to one of `coffee/food/sitdown/essentials/shop`.

**Note:** The live directory site may be JS-rendered or change markup. Scraping is **best-effort**: `parse_directory` is pure and fixture-tested; `main()` fetches with `urllib` and tolerates failure (writes/keeps a hand-maintainable `places_raw.json`). The curated set (Task 4) is the real backbone.

- [ ] **Step 1: Write the failing test + fixture**

`tests/fixtures/gcs_sample.html`:
```html
<ul class="directory">
  <li class="card" data-category="Dining"><a class="name">Grand Lux Cafe</a><span class="cat">Restaurant</span></li>
  <li class="card" data-category="Apparel"><a class="name">Tory Burch</a><span class="cat">Women's Apparel</span></li>
  <li class="card" data-category="Coffee"><a class="name">Bouchon Bakery</a><span class="cat">Cafe</span></li>
</ul>
```

`tests/test_scrape_places.py`:
```python
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import scrape_places as S

FIX = os.path.join(os.path.dirname(__file__), 'fixtures', 'gcs_sample.html')

class TestParse(unittest.TestCase):
    def setUp(self):
        with open(FIX, encoding='utf-8') as f:
            self.html = f.read()

    def test_parses_each_card(self):
        rows = S.parse_directory(self.html, 'Grand Canal Shoppes')
        names = sorted(r['name'] for r in rows)
        self.assertEqual(names, ['Bouchon Bakery', 'Grand Lux Cafe', 'Tory Burch'])

    def test_sets_area_and_unplaced(self):
        rows = S.parse_directory(self.html, 'Grand Canal Shoppes')
        self.assertTrue(all(r['area'] == 'Grand Canal Shoppes' for r in rows))
        self.assertTrue(all(r['placed'] is False for r in rows))

    def test_categorize_maps_to_known_buckets(self):
        self.assertEqual(S.categorize('Grand Lux Cafe', 'Restaurant'), 'sitdown')
        self.assertEqual(S.categorize('Bouchon Bakery', 'Cafe'), 'coffee')
        self.assertEqual(S.categorize('Tory Burch', "Women's Apparel"), 'shop')

    def test_ids_are_unique_slugs(self):
        rows = S.parse_directory(self.html, 'Grand Canal Shoppes')
        ids = [r['id'] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_scrape_places -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrape_places'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scrape_places.py
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

def categorize(name, raw_cat):
    t = f"{name} {raw_cat}".lower()
    if any(w in t for w in ['cafe', 'coffee', 'bakery', 'espresso', 'starbucks']): return 'coffee'
    if any(w in t for w in ['restaurant', 'grill', 'kitchen', 'trattoria', 'steak', 'dining', 'bar']): return 'sitdown'
    if any(w in t for w in ['pizza', 'burger', 'taco', 'food', 'snack', 'gelato', 'ice cream', 'noodle']): return 'food'
    if any(w in t for w in ['pharmacy', 'walgreens', 'cvs', 'sundries', 'drug']): return 'essentials'
    return 'shop'

class _Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_card = False
        self._cat = ''
        self._capture = None  # 'name' | 'cat' | None
        self._name = ''
        self._catt = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '')
        if 'card' in cls:
            self._in_card = True; self._cat = a.get('data-category', ''); self._name=''; self._catt=''
        elif self._in_card and 'name' in cls:
            self._capture = 'name'
        elif self._in_card and 'cat' in cls:
            self._capture = 'cat'
    def handle_data(self, data):
        if self._capture == 'name': self._name += data
        elif self._capture == 'cat': self._catt += data
    def handle_endtag(self, tag):
        if self._capture: self._capture = None
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_scrape_places -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Commit**

```bash
git add scrape_places.py tests/test_scrape_places.py tests/fixtures/gcs_sample.html
git commit -m "feat(places): best-effort directory scraper (fixture-tested)"
```

---

### Task 6: `build_places.py` — merge → `places.js`

**Files:**
- Create: `build_places.py`
- Test: `tests/test_build_places.py`

**Interfaces:**
- Consumes: `places_raw.json` (Task 5 output, optional) + `places_curated.json` (Task 4).
- Produces: `merge(raw:list, curated:list) -> list` (curated wins on name collision, case-insensitive; curated entries come first); `to_js(places:list) -> str` returning `window.PLACES = [...];`; `main()` reads both files and writes `places.js`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_places.py
import os, sys, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import build_places as B

class TestMerge(unittest.TestCase):
    def test_curated_wins_on_name_collision(self):
        raw = [{'id':'r1','name':'Grand Lux Cafe','cat':'sitdown','area':'Grand Canal Shoppes','placed':False}]
        cur = [{'id':'c1','name':'grand lux cafe','cat':'sitdown','area':'Grand Canal Shoppes','placed':True,'map':'gcs','x':0.3,'y':0.4}]
        out = B.merge(raw, cur)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0]['placed'])
        self.assertEqual(out[0]['id'], 'c1')

    def test_keeps_distinct_rows(self):
        raw = [{'id':'r1','name':'Tory Burch','cat':'shop','area':'Grand Canal Shoppes','placed':False}]
        cur = [{'id':'c1','name':'Starbucks','cat':'coffee','area':'Expo','placed':True,'map':'expo2','x':0.5,'y':0.5}]
        out = B.merge(raw, cur)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['id'], 'c1')  # curated first

    def test_to_js_emits_global_and_valid_json(self):
        js = B.to_js([{'id':'c1','name':'X','cat':'coffee','area':'Expo','placed':True}])
        self.assertTrue(js.startswith('window.PLACES = '))
        self.assertTrue(js.rstrip().endswith(';'))
        payload = js[len('window.PLACES = '):].rstrip().rstrip(';')
        json.loads(payload)  # must be valid JSON

if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_build_places -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_places'`.

- [ ] **Step 3: Write minimal implementation**

```python
# build_places.py
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
```

- [ ] **Step 4: Run test to verify it passes, then generate the real file**

Run: `python3 -m unittest tests.test_build_places -v`
Expected: PASS — 3 tests.

Then generate the real artifact and sanity-check it:
Run: `python3 scrape_places.py; python3 build_places.py && node -e "global.window={}; require('./places.js'); console.log('PLACES:', window.PLACES.length)"`
Expected: prints `wrote places.js …` and `PLACES: <n>` with n ≥ 6 (the curated seed; more if the scrape succeeded).

- [ ] **Step 5: Commit**

```bash
git add build_places.py tests/test_build_places.py places.js places_raw.json
git commit -m "feat(places): build_places merge -> places.js"
```

---

### Task 7: Property base maps (from the official PDF)

**Files:**
- Create: `maps/prop1.jpg`, `maps/prop2.jpg`
- Source: `/Users/tom.caswell/map.pdf` (2-page official Venetian/Palazzo map: page 1 = Level 1, page 2 = Level 2 / Grand Canal Shoppes)

**Interfaces:**
- Consumes: the source PDF.
- Produces: two JPG base images referenced by `MAP_META.prop1.img` / `MAP_META.prop2.img`, each **padded to a square** (so the existing `preserveAspectRatio="none"` 0–1 pin model doesn't distort them).

**Note:** Built entirely with macOS built-ins (`sips` + JavaScript-for-Automation/PDFKit) — no poppler/ghostscript. `sips` only rasterizes page 1, so page 2 is split out via PDFKit first. Each page is rendered, padded to square with a white border, resized, and JPEG-compressed to ~150–250 KB. The directory sidebar stays in the image (it's the official legend); curated pins are placed by eye on these squares and tuned later.

- [ ] **Step 1: Render both pages and pad to square**

```bash
cd "$(git rev-parse --show-toplevel)"
mkdir -p maps
SRC=/Users/tom.caswell/map.pdf
TMP=$(mktemp -d)
# Page 1 (Level 1): sips rasterizes the first page directly
sips -s format png "$SRC" --out "$TMP/p1.png" >/dev/null
# Page 2 (Level 2): split it into its own 1-page PDF via PDFKit, then rasterize
osascript -l JavaScript >/dev/null <<JXA
ObjC.import('PDFKit'); ObjC.import('Foundation');
var doc = \$.PDFDocument.alloc.initWithURL(\$.NSURL.fileURLWithPath('$SRC'));
var out = \$.PDFDocument.alloc.init;
out.insertPageAtIndex(doc.pageAtIndex(1), 0);
out.writeToFile('$TMP/p2.pdf');
JXA
sips -s format png "$TMP/p2.pdf" --out "$TMP/p2.png" >/dev/null
# Pad each to a white square (max of W/H), resize to 1500, JPEG ~quality to keep <250KB
for n in 1 2; do
  W=$(sips -g pixelWidth  "$TMP/p$n.png" | awk '/pixelWidth/{print $2}')
  H=$(sips -g pixelHeight "$TMP/p$n.png" | awk '/pixelHeight/{print $2}')
  S=$(( W > H ? W : H ))
  sips --padToHeightWidth "$S" "$S" --padColor FFFFFF "$TMP/p$n.png" --out "$TMP/sq$n.png" >/dev/null
  sips -Z 1500 -s format jpeg -s formatOptions 60 "$TMP/sq$n.png" --out "maps/prop$n.jpg" >/dev/null
done
echo "done"
```

- [ ] **Step 2: Verify presence, square-ish dimensions, size, and JPEG magic**

```bash
for n in 1 2; do
  f="maps/prop$n.jpg"; test -f "$f" || { echo "MISSING $f"; continue; }
  echo "$f $(wc -c < "$f") bytes $(sips -g pixelWidth -g pixelHeight "$f" | awk '/pixel/{printf "%s ",$2}')"
done
node -e "const fs=require('fs');['maps/prop1.jpg','maps/prop2.jpg'].forEach(f=>{const b=fs.readFileSync(f);if(b[0]!==0xFF||b[1]!==0xD8)throw new Error('not JPEG: '+f);console.log('JPEG ok',f)})"
```
Expected: both files exist, square (width == height, ~1500), each < 250000 bytes, both `JPEG ok`. If a file exceeds 250 KB, re-run Step 1 lowering `formatOptions` (e.g. 45).

- [ ] **Step 3: Eyeball the renders**

Open `maps/prop1.jpg` and `maps/prop2.jpg` (e.g. `open maps/prop1.jpg`). Confirm page 1 shows the **Level 1** property map + legend and page 2 shows the **Level 2 / Grand Canal Shoppes** map + legend, each centered on a white square with no clipping.

- [ ] **Step 4: Commit**

```bash
git add maps/prop1.jpg maps/prop2.jpg
git commit -m "feat(places): add official Venetian/Palazzo Level 1 + 2 base maps"
```

---

### Task 8: Wire scripts + generalize `LVL_IMG` → `MAP_META` (regression-safe)

**Files:**
- Modify: `index.html` (script tags near line 319–321; `LVL_IMG` at line 745 and its use in `dayMapHTML` ~752)

**Interfaces:**
- Consumes: `places-engine.js` (`window.PlacesEngine`), `places.js` (`window.PLACES`).
- Produces: `PlacesEngine` + `PLACES` available globally; `dayMapHTML` uses `PlacesEngine.MAP_META['expo'+lv].img` instead of the local `LVL_IMG`.

- [ ] **Step 1: Add the script tags**

After line 320 (`<script src="details.js?v=…"></script>`), add (use the current version string from `version.txt`):
```html
<script src="places-engine.js?v=2026-06-21.14"></script>
<script src="places.js?v=2026-06-21.14"></script>
```

- [ ] **Step 2: Replace the local `LVL_IMG` with the engine registry**

At line 745, replace:
```js
const LVL_IMG={2:'floorplans/level2.jpg',3:'floorplans/level3.jpg',4:'floorplans/level4.jpg',5:'floorplans/level5.jpg'};
```
with:
```js
// Expo floor images now come from the shared PlacesEngine.MAP_META registry.
const LVL_IMG={2:PlacesEngine.MAP_META.expo2.img,3:PlacesEngine.MAP_META.expo3.img,4:PlacesEngine.MAP_META.expo4.img,5:PlacesEngine.MAP_META.expo5.img};
```
(Keeping the `LVL_IMG` name means `dayMapHTML` and the rest of My Map are untouched — pure regression safety.)

- [ ] **Step 3: Smoke-check the wiring**

Run:
```bash
grep -q 'places-engine.js' index.html && grep -q 'places.js?v=' index.html && echo "scripts wired"
grep -q 'PlacesEngine.MAP_META.expo2.img' index.html && echo "LVL_IMG generalized"
node -e "global.window={};require('./places-engine.js');require('./places.js');console.log('globals ok', !!window.PlacesEngine, Array.isArray(window.PLACES))"
```
Expected: `scripts wired`, `LVL_IMG generalized`, `globals ok true true`.

- [ ] **Step 4: Manual regression check (My Map still works)**

Serve and open the app:
```bash
python3 -m http.server 8765 >/dev/null 2>&1 &  # then open http://localhost:8765/?plan=sarah
```
In the browser: open **My Map**. Expected: floor maps still render with numbered pins exactly as before (no blank images, no console errors). Stop the server when done (`kill %1`).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "refactor(map): source Expo floor images from PlacesEngine.MAP_META; load places scripts"
```

---

### Task 9: **🍽️ Food & Shops** tab — markup, wiring, list render

**Files:**
- Modify: `index.html` (tabs nav 293–300; views container; `renderActive` 1293–1301; add `renderFood`)

**Interfaces:**
- Consumes: `PlacesEngine.{filterPlaces,sortByWalk,formatHint,isOpenNow}`, `window.PLACES`, existing `geoOf`, `roomOf`, `homeLoc`, `state.picks`, `DATA`, `escapeHtml`, `escapeAttr`, `toast`, `save`.
- Produces: `foodOrigin()` → `{mapId,x,y,label}`; `nextSessionLoc()` → origin from next live pick; `renderFood()`; `state.foodFilters` + `state.foodOrigin` persisted.

- [ ] **Step 1: Add the tab button**

In the `<nav class="tabs">` block, after the `My Map` button (line 296 `<button data-tab="live" …>`), insert:
```html
  <button data-tab="food">🍽️ Food &amp; Shops</button>
```

- [ ] **Step 2: Add the view container**

Add a new view container next to the other `.view` sections (same structure/class as `view-live`, e.g. immediately after it):
```html
<section class="view" id="view-food" style="display:none"><div id="foodBody"></div></section>
```

- [ ] **Step 3: Wire `renderActive` and add origin/render logic**

In `renderActive` (line 1293), add before the closing brace:
```js
  else if(activeTab==='food') renderFood();
```

Then add these functions (near the other render functions, e.g. after `renderLive`):
```js
/* ---------- Food & Shops ---------- */
function nextSessionLoc(){
  // earliest live pick (by day+start) whose end hasn't passed; falls back to first live pick.
  const live = (window.DATA||[]).filter(s=>state.picks[s.id]==='live');
  if(!live.length) return null;
  live.sort((a,b)=> (a.day||'').localeCompare(b.day||'') || (a.start||'').localeCompare(b.start||''));
  const s = live[0];
  const g = geoOf(roomOf(s)); if(!g) return null;
  return {mapId:'expo'+g.lvl, x:g.x, y:g.y, label:'next session ('+(s.code||s.title||'')+')'};
}
function foodOrigin(){
  const mode = state.foodOrigin || 'next';
  if(mode==='home'){ const h=homeLoc(); return {mapId:'expo'+h.lvl, x:h.x, y:h.y, label:homeName()}; }
  const n = nextSessionLoc();
  if(n) return n;
  const h=homeLoc(); return {mapId:'expo'+h.lvl, x:h.x, y:h.y, label:homeName()}; // fallback
}
function foodNow(){
  const d=new Date();
  return {day:d.getDay(), minutes:d.getHours()*60+d.getMinutes()};
}
const FOOD_CATS=[['coffee','☕ Coffee'],['food','🍔 Food'],['sitdown','🍽️ Sit-down'],['essentials','🧴 Essentials'],['restroom','🚻 Restrooms'],['shop','🛍️ Shops']];
function renderFood(){
  const body=document.getElementById('foodBody'); if(!body) return;
  const f=state.foodFilters||(state.foodFilters={cats:[],openNow:false,stepFree:false,q:''});
  const origin=foodOrigin(), now=foodNow();
  const filtered=PlacesEngine.filterPlaces(window.PLACES||[], {q:f.q,cats:f.cats,openNow:f.openNow,stepFree:f.stepFree,now});
  const sorted=PlacesEngine.sortByWalk(filtered, origin);
  const chip=(key,label,on)=>`<button class="foodchip${on?' on':''}" data-cat="${key}">${label}</button>`;
  const rows=sorted.map(p=>{
    const open=PlacesEngine.isOpenNow(p, now);
    const badge=open===true?'<span class="open">Open</span>':open===false?'<span class="closed">Closed</span>':'';
    const hint=PlacesEngine.formatHint(p._walk, {stepFree:p.stepFree});
    const approx=p.placed?'':' <span class="approx">approx. area</span>';
    return `<div class="foodrow" data-id="${escapeAttr(p.id)}">
      <div class="fr-main"><b>${escapeHtml(p.name)}</b> ${badge}
        <div class="fr-sub">${escapeHtml(p.area)}${p.price?' · '+p.price:''}${p.hours?' · '+escapeHtml(p.hours):''}${approx}</div>
        <div class="fr-hint">🚶 ${escapeHtml(hint)}</div>
        ${p.note?`<div class="fr-note">${escapeHtml(p.note)}</div>`:''}
      </div>
      <button class="fr-map" data-id="${escapeAttr(p.id)}">Map ›</button>
    </div>`;
  }).join('');
  body.innerHTML=`
    <div class="foodbar">
      <div class="foodorigin">From: <select id="foodOriginSel">
        <option value="next"${(state.foodOrigin||'next')==='next'?' selected':''}>my next session</option>
        <option value="home"${state.foodOrigin==='home'?' selected':''}>my Palazzo suite</option>
      </select> <span class="origin-label">→ ${escapeHtml(origin.label)}</span></div>
      <input id="foodSearch" type="search" placeholder="Search shops &amp; restaurants…" value="${escapeAttr(f.q)}">
      <div class="foodchips">${FOOD_CATS.map(c=>chip(c[0],c[1],f.cats.includes(c[0]))).join('')}
        ${chip('__open','🕒 Open now',f.openNow)}${chip('__step','♿ Step-free',f.stepFree)}</div>
    </div>
    <div class="foodlist">${rows||'<p class="empty">No places match those filters.</p>'}</div>`;
  bindFood();
}
function bindFood(){
  const sel=document.getElementById('foodOriginSel'); if(sel) sel.onchange=()=>{ state.foodOrigin=sel.value; save(); renderFood(); };
  const q=document.getElementById('foodSearch'); if(q) q.oninput=()=>{ state.foodFilters.q=q.value; save(); renderFood(); };
  document.querySelectorAll('.foodchip').forEach(b=>b.onclick=()=>{
    const k=b.dataset.cat, f=state.foodFilters;
    if(k==='__open') f.openNow=!f.openNow;
    else if(k==='__step') f.stepFree=!f.stepFree;
    else { const i=f.cats.indexOf(k); if(i>=0) f.cats.splice(i,1); else f.cats.push(k); }
    save(); renderFood();
  });
  document.querySelectorAll('.fr-map').forEach(b=>b.onclick=()=>openPlaceMap(b.dataset.id));
}
```

- [ ] **Step 4: Add minimal CSS**

In the `<style>` block, add:
```css
.foodbar{padding:8px var(--gut)}
.foodbar input[type=search]{width:100%;padding:9px 11px;font-size:15px;border:1px solid #d4d8e0;border-radius:10px;margin:8px 0}
.foodchips{display:flex;flex-wrap:wrap;gap:6px}
.foodchip{border:1px solid #cdd3dd;background:#fff;border-radius:16px;padding:5px 10px;font-size:12.5px}
.foodchip.on{background:var(--brand);color:#fff;border-color:var(--brand)}
.foodrow{display:flex;align-items:center;gap:10px;padding:11px var(--gut);border-bottom:1px solid #eef1f5}
.fr-main{flex:1}.fr-sub{color:#5a6472;font-size:13px;margin-top:2px}
.fr-hint{font-size:13px;margin-top:3px}.fr-note{font-size:12.5px;color:#6b7280;margin-top:3px;font-style:italic}
.fr-map{flex:0 0 auto;border:1px solid var(--brand);color:var(--brand);background:#fff;border-radius:8px;padding:7px 10px;font-size:13px}
.foodrow .open{color:#1a8a4a;font-size:12px;font-weight:600}.foodrow .closed{color:#b23;font-size:12px}
.fr-sub .approx{color:#a06a00;font-size:11.5px}
.foodlist .empty{padding:20px var(--gut);color:#6b7280}
.origin-label{color:#5a6472;font-size:13px}
```

- [ ] **Step 5: Manual verification**

Serve (`python3 -m http.server 8765`) and open `http://localhost:8765/?plan=sarah`.
Expected:
- A **🍽️ Food & Shops** tab appears after My Map; tapping it shows the directory.
- Rows are sorted closest-first; each shows area, price/hours, and a "🚶 ~N min · … " hint.
- Typing in search filters live; tapping category chips filters; "Open now" / "Step-free" toggle.
- Switching the "From:" dropdown to "my Palazzo suite" re-sorts and updates the origin label.
- No console errors. (`openPlaceMap` is added in Task 10 — the "Map ›" button is wired but its handler lands next task; clicking it may log undefined until then.)

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat(food): Food & Shops tab — directory list, filters, origin selector"
```

---

### Task 10: Place map view — pin + route + Open in Maps

**Files:**
- Modify: `index.html` (add `openPlaceMap` + `placeMapHTML`; reuse `openMapModal`/`setupZoom` and the `.lvlmap` SVG shape used by `dayMapHTML`)

**Interfaces:**
- Consumes: `window.PLACES`, `PlacesEngine.{placeLoc,MAP_META,formatHint}`, `foodOrigin`, existing `openMapModal(lvlmapEl)` (line 644), `escapeHtml`.
- Produces: `openPlaceMap(id:string)` — builds a `.lvlmap` for the place's map with origin pin, place pin, dashed route, and an Open-in-Maps link, then opens it in the fullscreen modal.

- [ ] **Step 1: Add the map builder + opener**

Add near `dayMapHTML` (line 746):
```js
function placeMapHTML(place, origin){
  const loc = PlacesEngine.placeLoc(place);
  if(!loc) return null;
  const meta = PlacesEngine.MAP_META[loc.mapId]; if(!meta) return null;
  const sameMap = origin && origin.mapId===loc.mapId;
  // Match the existing dayMapHTML convention: 100x100 viewBox, image stretched, pins at x*100.
  const cx=(loc.x*100).toFixed(1), cy=(loc.y*100).toFixed(1);
  let route='', originPin='';
  if(sameMap){
    const ox=(origin.x*100).toFixed(1), oy=(origin.y*100).toFixed(1);
    route=`<line x1="${ox}" y1="${oy}" x2="${cx}" y2="${cy}" stroke="#7a5cff" stroke-width="1.3" stroke-dasharray="3 2"/>`;
    originPin=`<circle cx="${ox}" cy="${oy}" r="4.4" fill="#7a5cff" stroke="#fff" stroke-width="1.1"/>`+
      `<text x="${ox}" y="${(parseFloat(oy)+1.5).toFixed(1)}" text-anchor="middle" font-size="4" fill="#fff" font-weight="700">○</text>`;
  }
  const tag = place.placed ? '' : ' (approx. area)';
  const mapsUrl = 'https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(place.name+' Venetian Las Vegas');
  const hint = PlacesEngine.formatHint(PlacesEngine.walkBetween(origin||loc, loc), {stepFree:place.stepFree});
  return `<div class="lvlmap">
    <div class="lvlmap-h">${escapeHtml(place.name)} — ${escapeHtml(meta.label)}${tag} ⤢</div>
    <svg viewBox="0 0 100 100" width="100%">
      <image href="${meta.img}" x="0" y="0" width="100" height="100" preserveAspectRatio="none"/>
      ${route}${originPin}
      <circle cx="${cx}" cy="${cy}" r="5.2" fill="#e8463c" stroke="#fff" stroke-width="1.1"/>
      <text x="${cx}" y="${(parseFloat(cy)+1.7).toFixed(1)}" text-anchor="middle" font-size="5" fill="#fff" font-weight="700">●</text>
    </svg>
    <div class="lvlmap-key">🚶 ${escapeHtml(hint)} · <a href="${mapsUrl}" target="_blank" rel="noopener">Open in Maps ↗</a>${sameMap?' · ○ you · ● destination':''}</div>
  </div>`;
}
function openPlaceMap(id){
  const place=(window.PLACES||[]).find(p=>p.id===id); if(!place){ toast('Place not found'); return; }
  const html=placeMapHTML(place, foodOrigin());
  if(!html){ toast('No map for this spot'); return; }
  const wrap=document.createElement('div'); wrap.innerHTML=html;
  openMapModal(wrap.querySelector('.lvlmap'));
}
```

- [ ] **Step 2: Smoke-check the new symbols exist**

Run:
```bash
grep -q 'function openPlaceMap' index.html && grep -q 'function placeMapHTML' index.html && echo "place map fns present"
grep -q 'maps/search/?api=1' index.html && echo "open-in-maps wired"
```
Expected: both echo lines print.

- [ ] **Step 3: Manual verification**

Serve and open `http://localhost:8765/?plan=sarah` → **Food & Shops** → tap **Map ›** on a curated row (e.g. "Starbucks (Expo)").
Expected:
- The fullscreen zoom modal opens showing that map image with a red destination pin; for a same-map origin, a purple "you" pin + dashed route line appears.
- The key line shows "🚶 ~N min · … · Open in Maps ↗".
- Tapping **Open in Maps** opens Google Maps in a new tab searching the place at the Venetian. No personal data in the URL.
- Pinch/scroll zoom + drag pan + ✕/Esc close all work (reused `setupZoom`).
- Tapping **Map ›** on an unplaced long-tail row opens its area map with the pin near the area center and an "(approx. area)" tag.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat(food): place map view with route pin + Open in Maps"
```

---

### Task 11: Version bump, full test sweep, final verification

**Files:**
- Modify: `version.txt`; `index.html` (script `?v=` strings)

- [ ] **Step 1: Bump version + cache-bust**

Set `version.txt` to `2026-06-27.1`. Update every `?v=` query in `index.html` (data.js, details.js, places-engine.js, places.js) to `2026-06-27.1`:
```bash
sed -i '' 's/?v=2026-06-21.14/?v=2026-06-27.1/g' index.html
printf '2026-06-27.1\n' > version.txt
grep -c 'v=2026-06-27.1' index.html   # expect 4
```
Expected: prints `4`.

- [ ] **Step 2: Full automated test sweep**

Run:
```bash
node --test tests/ && python3 -m unittest discover -s tests -p 'test_*.py' -v
```
Expected: all Node tests pass and all Python tests pass (OK).

- [ ] **Step 3: Regenerate data + integrity check**

Run:
```bash
python3 scrape_places.py; python3 build_places.py
node -e "global.window={};require('./places-engine.js');require('./places.js');const P=window.PLACES;const bad=P.filter(p=>p.placed&&!window.PlacesEngine.MAP_META[p.map]);if(bad.length)throw new Error('placed w/ bad map: '+bad.map(b=>b.id));console.log('places ok:',P.length)"
```
Expected: `places ok: <n>` with no thrown error.

- [ ] **Step 4: Manual end-to-end**

Serve and walk the full flow on a phone-width viewport (`http://localhost:8765/?plan=sarah`):
- My Map renders (regression).
- Food & Shops: sort-by-distance, search, category chips, Open-now, Step-free, origin switch, place map with route + Open in Maps, long-tail approx pin.
- No console errors anywhere.

- [ ] **Step 5: Commit**

```bash
git add index.html version.txt places.js places_raw.json
git commit -m "chore: bump version 2026-06-27.1 for Food & Shops release"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** Data model → T4/T6; base maps + MAP_META → T1/T7/T8; walk engine (same-map reuse + zone graph) → T1; hints/open-now → T2; filter/sort + area anchors → T3; Food & Shops tab (origin, search, filters, list) → T9; map view (pin/route/Open in Maps) → T10; scrape→build pipeline → T5/T6; version bump → T11. All spec sections mapped.
- **Placeholder scan:** No TBD/TODO; every code step shows complete code; manual-verification steps list explicit expected outcomes.
- **Type consistency:** `walkBetween`→`{minutes,sameMap,zoneChange,far,from,to}` used consistently by `formatHint`/`sortByWalk`/`placeMapHTML`; `placeLoc`/`AREA_ANCHOR` names consistent T3→T10; `state.foodFilters` shape `{cats,openNow,stepFree,q}` consistent T9. `MAP_META` ids `expo2..5/gcs/palazzo` consistent throughout.
- **Testing reality:** automated where it pays (engine, Python, data schema); manual browser checks for DOM, matching repo convention (noted in Testing strategy).
