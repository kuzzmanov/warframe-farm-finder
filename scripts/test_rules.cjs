const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const html = fs.readFileSync('index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'inline application script exists');
const element = () => ({ value: 'match', addEventListener() {}, classList: { add() {}, remove() {} }, querySelectorAll() { return []; } });
const context = {
  document: { querySelector: element, querySelectorAll: () => [] },
  fetch: async () => ({ ok: false }), URLSearchParams, console, Set, Map, Math, String, Number, Array, Object,
};
vm.createContext(context);
vm.runInContext(script + '\nglobalThis.rules = { cardKind, groupDropSources, fallbackImage, renderCard, renderSourceRows };', context);
const { cardKind, groupDropSources, fallbackImage, renderCard, renderSourceRows } = context.rules;

assert.equal(cardKind({ title: '2x Neurodes', category: 'DROP DATA' }), 'resource');
assert.equal(cardKind({ title: '(2x) Neurodes' }), 'resource');
assert.equal(cardKind({ title: 'Neurodes', category: 'RESOURCE' }), 'resource');
const grouped = groupDropSources([
  { title: 'Neurodes', detailItems: [{ label: 'Planet', value: 'Earth' }, { label: 'Node', value: 'Everest' }, { label: 'Rotation', value: 'A' }], chance: 10 },
  { title: 'Neurodes', detailItems: [{ label: 'Planet', value: 'Earth' }, { label: 'Node', value: 'Everest' }, { label: 'Rotation', value: 'A' }], chance: 10 },
  { title: 'Neurodes', detailItems: [{ label: 'Planet', value: 'Earth' }, { label: 'Node', value: 'Everest' }, { label: 'Rotation', value: 'B' }], chance: 10 },
]);
assert.equal(grouped.length, 1, 'same item becomes one card');
assert.equal(grouped[0].groupedSources.length, 1, 'same source across rotations is summarized in one row');
assert.equal([...grouped[0].groupedSources[0]._groupedRotations].sort().join(','), 'A,B', 'rotation labels are preserved in the summary');
assert.match(renderCard(grouped[0]), /Rot A\/B/);
const compactRows=renderSourceRows([
  {title:'Neurodes',chance:10,detailItems:[{label:'Planet',value:'Earth'},{label:'Node',value:'Everest'},{label:'Rotation',value:'A'},{label:'Stage',value:'1'}]},
  {title:'Neurodes',chance:20,detailItems:[{label:'Planet',value:'Earth'},{label:'Node',value:'Everest'},{label:'Rotation',value:'B'},{label:'Stage',value:'2'}]},
  {title:'Neurodes',chance:30,detailItems:[{label:'Planet',value:'Earth'},{label:'Node',value:'Everest'},{label:'Rotation',value:'C'},{label:'Stage',value:'3'}]},
]);
assert.equal((compactRows.match(/class="source-row"/g)||[]).length,4,'one farm location collapses to one summary row with expandable stage/rotation entries');
assert.match(compactRows,/Show 3 drop entries/);
assert.match(compactRows,/10%/);assert.match(compactRows,/20%/);assert.match(compactRows,/30%/);
assert.ok(fallbackImage('resource').startsWith('data:image/svg+xml,'), 'missing art receives a visible local fallback');
const card = renderCard({ title: 'Neurodes', category: 'RESOURCE' });
assert.match(card, /class="itemthumb thumb-resource"/);
assert.ok(card.indexOf('class="resultvisual"') < card.indexOf('class="result-heading"'), 'image precedes the title');
for (const result of [
  { title:'Redirection', category:'DROP DATA' },
  { title:'Paris Prime Blueprint', relic:'Lith P1' },
  { title:'Wiki test', source:'Warframe Wiki', tag:'WIKI RESULT', wikiQuery:'Wiki test' },
]) {
  const output=renderCard(result);
  assert.ok(output.indexOf('class="resultvisual"') < output.indexOf('class="result-heading"'), `${result.title} keeps its image above its title`);
}
assert.match(renderCard({title:'Redirection',detailItems:[{label:'Enemy',value:'Scavenger Drone'},{label:'Planet',value:'Earth'},{label:'Node',value:'Coba'}]}),/Scavenger Drone \/ Earth – Coba/);
const mappedEnemy=renderCard({title:'Redirection',detailItems:[{label:'Enemy',value:'Scavenger Drone'}],enemyLocations:{planets:['Earth','Deimos'],tileSets:['Plains of Eidolon']}});
assert.match(mappedEnemy,/Scavenger Drone \/ Earth, Deimos \+1 more/);
assert.match(mappedEnemy,/View all 3 enemy locations/);
assert.match(mappedEnemy,/Plains of Eidolon/);
assert.match(html, /\.resulthead\{width:max-content/);
assert.match(html, /\.resulthead \.result-heading\{text-align:center/);
const enemyRows = renderSourceRows([{ title:'Redirection', chance:2, detailItems:[{label:'Enemy',value:'Crewman'},{label:'Planet',value:'Earth'},{label:'Node',value:'Coba'}] }]);
assert.match(enemyRows, /Crewman \/ Earth – Coba/);
assert.match(renderSourceRows([{title:'Redirection',detailItems:[{label:'Enemy',value:'Crewman'}]}]), /Crewman \/ Location not listed/);
assert.match(html, /justify-content:center/);
console.log('Core rule checks passed: resource classification, rotation grouping, image fallback and top placement, enemy locations, and unresolved-location labeling.');
