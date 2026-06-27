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

test('formatHint same map mentions the map label and step-free', () => {
  const r = E.walkBetween({mapId:'expo3',x:0.2,y:0.2},{mapId:'expo3',x:0.3,y:0.3});
  const s = E.formatHint(r, {stepFree:true});
  assert.match(s, /~\d+ min/);
  assert.match(s, /Expo Level 3/);
  assert.match(s, /step-free/);
});

test('formatHint across zones shows from -> to zone labels', () => {
  const r = E.walkBetween({mapId:'expo2',x:0.5,y:0.5},{mapId:'prop2',x:0.5,y:0.5});
  const s = E.formatHint(r, {});
  assert.match(s, /Expo/);
  assert.match(s, /Venetian\/Palazzo/);
  assert.match(s, /→/);
});

test('isOpenNow handles daily array, per-day object, and missing', () => {
  assert.equal(E.isOpenNow({open:[600, 1320]}, {day:3, minutes:700}), true);   // 10:00–22:00, now 11:40
  assert.equal(E.isOpenNow({open:[600, 1320]}, {day:3, minutes:1380}), false);  // 23:00
  assert.equal(E.isOpenNow({open:{'3':[600,1320],'0':[0,0]}}, {day:0, minutes:700}), false); // closed Sun
  assert.equal(E.isOpenNow({}, {day:3, minutes:700}), null);
});

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
