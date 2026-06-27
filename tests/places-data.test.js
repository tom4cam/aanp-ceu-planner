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
