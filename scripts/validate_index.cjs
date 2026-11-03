const fs = require('node:fs');
const assert = require('node:assert/strict');
const index = JSON.parse(fs.readFileSync('data/search-index.json', 'utf8'));
assert.ok(Array.isArray(index.records) && index.records.length > 0, 'generated index contains records');
for (const [i, r] of index.records.entries()) {
  assert.equal(typeof r.title, 'string', `record ${i} has a title`);
  assert.ok(r.title.trim(), `record ${i} title is not empty`);
  assert.ok(Array.isArray(r.detailItems), `record ${i} has normalized detailItems`);
  assert.ok(r.detailItems.every(d => typeof d.label === 'string' && typeof d.value === 'string'), `record ${i} detailItems are normalized`);
  assert.ok(r.image == null || typeof r.image === 'string', `record ${i} image has a valid shape`);
  assert.ok(r.category == null || typeof r.category === 'string', `record ${i} category has a valid shape`);
  assert.ok(r.enemyLocations == null || (
    Array.isArray(r.enemyLocations.planets) && Array.isArray(r.enemyLocations.tileSets) &&
    [...r.enemyLocations.planets, ...r.enemyLocations.tileSets].every(x => typeof x === 'string')
  ), `record ${i} enemy locations have a valid structured shape`);
}
console.log(`Validated ${index.records.length} normalized drop records.`);
