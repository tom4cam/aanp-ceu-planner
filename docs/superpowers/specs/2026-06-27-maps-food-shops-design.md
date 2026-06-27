# Maps + Food & Shops directory with proximity directions — design

**Date:** 2026-06-27
**App:** AANP 2026 CEU Planner (`index.html`, static, localStorage, GitHub Pages)
**Status:** Approved design — ready for implementation plan

## Goal

Give Sarah (AGACNP, foot injury) a way to find food, coffee, essentials, restrooms, and shops across
the **Venetian / Palazzo / Expo & Convention Center**, sorted by **walking distance from her next
session**, with maps and walk guidance. A *layered* experience: a browsable/searchable full
directory **plus** proximity ranking and route hints.

Chosen approach (from brainstorming): **A — extend the existing floor-plan system.** Reuse the
current `geoOf`/`roomDistance`/`homeLoc` proximity engine, the Level 2–5 Expo floor maps, and the
fullscreen pinch-zoom map modal. Add retail/dining base maps as new "maps," a places dataset, a
generalized walk engine, and a new tab.

## Decisions locked during brainstorming

- **Core intent:** Both, layered — browse/search the full directory AND proximity-rank by walk
  distance from her next live session, with route guidance.
- **Data sourcing:** Curated + scraped hybrid — scrape the full Grand Canal Shoppes / Venetian /
  Palazzo directory for browse/search completeness; hand-place + verify ~30–50 high-value spots with
  real pins/routes. Long tail shows info with coarse (area-level) location.
- **Directions:** Both — our own foot-injury-aware walk hint + drawn line, plus an "Open in Maps"
  handoff for live routing.

## Known approximations (accepted)

1. **Hand-placed retail pins.** The Grand Canal Shoppes / Palazzo maps are NOT in the AANP/Floq
   bundle. Base images are sourced externally; curated pins are placed by hand (visually accurate,
   approximate — same model as today's Palazzo home pin). Long-tail items get an area-centroid pin
   tagged "approx. area," not a precise spot.
2. **Estimated cross-building walk times.** No indoor routing API exists for this complex.
   Cross-area times come from a small hand-tuned zone graph, surfaced honestly in the hint text.
3. **Static hours snapshot.** Scraped hours are a point-in-time snapshot and may go stale; no
   real-time hours API.

## 1. Data model — `places.js`

Loads as a global, like `data.js` / `details.js`:

```js
window.PLACES = [{
  id,          // stable slug
  name,
  cat,         // 'coffee' | 'food' | 'sitdown' | 'essentials' | 'restroom' | 'shop' | 'landmark'
  sub,         // free text: 'Italian', 'Pharmacy', 'Apparel'…
  area,        // 'Expo' | 'Grand Canal Shoppes' | 'Venetian Casino' | 'Palazzo' | 'Waterfall Atrium'
  map, lvl, x, y,  // map id + normalized 0–1 coords IF hand-placed; else null
  placed,      // true = real pin (curated) · false = long-tail (area-level only)
  price,       // '$'..'$$$$' or null
  hours,       // display string, e.g. "10a–11p"
  open,        // optional {d:[{o,c}…]} structured hours for "Open now"; omitted → no badge
  stepFree,    // true if reachable without stairs (foot-injury aid)
  note         // short curated tip, optional
}]
```

- Curated ~30–50 entries: `placed:true`, real `map/lvl/x/y`, `stepFree`, optional `note`.
- Scraped long tail: `placed:false`, `area` only (no precise coords).

## 2. Base maps + coordinate system

- Reuse existing Expo Level 2–5 JPGs (`floorplans/level{2,3,4,5}.jpg`).
- Add two new base images sourced from the Venetian's published property maps, resized to ~150 KB
  JPGs to match existing floorplans: `maps/gcs.jpg` (Grand Canal Shoppes retail level),
  `maps/palazzo.jpg` (Palazzo / Waterfall Atrium dining area).
- Generalize the current `LVL_IMG = {2..5: …}` into a `MAPS` registry keyed by map id:
  `expo2, expo3, expo4, expo5, gcs, palazzo`. Each map has its own normalized 0–1 coordinate space.
- Keep a numeric `lvl` on each map for the vertical-distance penalty in the walk engine; retail
  maps get a representative `lvl` for that penalty.

## 3. Walk engine — generalize the existing proximity math

Today `roomDistance(a,b)` handles same-building level math only (Euclidean + `0.6*Δlevel` penalty,
`far` threshold 0.34). Add:

```
walkBetween(origin, place) -> { minutes, legs:[...], stepFree, far, hint }
```

- **Same map:** reuse existing Euclidean+level math; scale the normalized distance to minutes.
- **Across areas:** a small hand-tuned **zone graph** with anchor points and approximate
  walk-minutes between zones (Expo ⇄ Palazzo walkway ⇄ Grand Canal Shoppes ⇄ Venetian casino),
  plus the intra-map leg on each end.
- `origin` can be: her next live session's room, the Palazzo home base (`homeLoc`), or a
  user-picked room. Reuse `geoOf`, `homeLoc`, `levelOf`.
- Hint text is explicit and foot-injury-aware, e.g.
  `~6 min · Expo L2 → Palazzo walkway → Grand Canal level · step-free`.

"Next session" origin = from her live picks, the next one by start time during conference hours;
otherwise fall back to the first live session of the next conference day, then to home base.

## 4. UI — new **🍽️ Food & Shops** tab (inserted after **My Map**)

Tab order becomes: Browse · My Plan · My Map · **Food & Shops** · My Notes · CEUs · Watch Later · Help.
The new tab uses `data-tab="food"` (handled in `show()` alongside the existing tab ids
`browse/plan/live/notes/dash/rec/help`).

- **Origin selector** (top): default **"From my next session"** (auto-detected); options
  "From my Palazzo suite" and "Pick a room." Last choice may persist in `state.placeOrigin`.
- **Search box** + **filter chips:** Coffee · Food · Sit-down · Essentials · Restrooms · Shops ·
  Open now · Step-free. (Category + area + price + open-now + step-free filters.)
- **List** sorted by walk-minutes from origin. Each row: category icon, name, area, price,
  hours / open-now badge, and the walk hint. Curated `placed:true` rows show a precise pin on tap;
  long-tail `placed:false` rows show an area pin tagged "approx. area."
- **Map view on tap:** reuse the existing fullscreen pinch-zoom map modal (`#mapModal` / `setupZoom`)
  showing the place pin, a dashed route line from origin, and an **"Open in Maps"** button:
  `https://www.google.com/maps/search/?api=1&query=<name>%20Venetian%20Las%20Vegas`
  (place name + venue only; no personal data in the URL).

## 5. Build pipeline (mirrors `build_data.py`)

- `scrape_places.py` — fetch the Grand Canal Shoppes directory + Venetian/Palazzo dining pages,
  parse name/category/hours/area → `places_raw.json`.
- `places_curated.json` — hand-authored ~30–50 entries with `map/lvl/x/y`, `stepFree`, `note`.
- `build_places.py` — merge `places_raw.json` + `places_curated.json` → `places.js`
  (curated overrides/augments scraped entries by name match). Re-runnable, like the rooms pipeline.

## 6. Scope guards (YAGNI)

**In:** everything above. **Out (explicitly):** live GPS/geolocation; real-time hours API;
reservations/ordering; individually-pinned long tail; turn-by-turn navigation. These keep the
feature offline-capable and honest about precision.

## Files

- **New:** `places.js`, `build_places.py`, `scrape_places.py`, `places_curated.json`,
  `maps/gcs.jpg`, `maps/palazzo.jpg`.
- **Edit `index.html`:** `MAPS` registry (generalize `LVL_IMG`); `walkBetween` + zone graph;
  new **🍽️ Food & Shops** tab markup, render, filters, and origin selector; load `places.js`.
- **Bump** `version.txt` (format `YYYY-MM-DD.N`) to trigger the client auto-updater.

## Privacy / repo notes

- No new credentials or personal data. "Open in Maps" URLs carry only a place name + "Venetian Las
  Vegas." Consistent with the repo being public and state staying in localStorage.

## Success criteria

- A browsable, searchable directory of Venetian/Palazzo/Expo shops & restaurants renders in the new
  tab.
- Results sort by estimated walk-minutes from her next session, with a clear, step-free-aware hint.
- Curated high-value spots show precise pins + a drawn route on the real maps; long-tail shows
  area-level location.
- "Open in Maps" hands off correctly; everything works offline except that handoff.
