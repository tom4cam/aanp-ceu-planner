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

  const API = { MAP_META, ZONES, ZONE_LABEL, zoneOf, walkBetween, formatHint, isOpenNow, AREA_ANCHOR, placeLoc, filterPlaces, sortByWalk };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.PlacesEngine = API;
})(typeof window !== 'undefined' ? window : globalThis);
