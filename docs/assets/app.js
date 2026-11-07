'use strict';
const $ = id => document.getElementById(id);
const formatNumber = n => new Intl.NumberFormat('ro-RO').format(n);
const bytes = n => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(1) + ' MB';
const first = (r, keys, fallback = '') => { for (const k of keys) { const v = r[k]; if (v !== undefined && v !== null && v !== '') return typeof v === 'object' ? JSON.stringify(v) : String(v); } return fallback; };
const safeURL = value => { try { const u = new URL(value, location.href); return ['http:', 'https:'].includes(u.protocol) ? u.href : ''; } catch { return ''; } };
const sourceURL = r => safeURL(first(r, ['source_url', 'document_url', 'url', 'source_page_url', 'source', 'official_url']));
const label = r => first(r, ['title', 'name', 'street', 'street_name', 'address', 'location', 'permit_number', 'number', 'id'], 'Înregistrare');
const geoLabel = r => first(r, ['coordinate_precision', 'geocoding_precision', 'geometry_precision', 'geo_precision', 'location_precision', 'geocode_precision', 'precision', 'geometry_type'], 'Vezi GeoJSON');
const element = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
let records = [], filtered = [], page = 0, selectedLanguage = 'curl', config;
const pageSize = 20;
const languages = {curl: ['download.sh', 'curl'], python: ['download.py', 'Python'], go: ['download.go', 'Go'], node: ['download.mjs', 'Node.js']};
const snippets = {};

function makeLink(url, text) { const a = element('a', text); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; }
function showTable() {
  $('table-head').replaceChildren();
  const trh = element('tr'); for (const title of ['Înregistrare', 'Tip / zonă', 'Detalii', 'Localizare', 'Sursa']) trh.append(element('th', title)); $('table-head').append(trh);
  $('table-body').replaceChildren();
  const rows = filtered.slice(page * pageSize, (page + 1) * pageSize);
  for (const r of rows) {
    const tr = element('tr');
    const main = element('td', label(r));
    if (r.id && label(r) !== String(r.id)) main.append(element('span', String(r.id), 'secondary'));
    tr.append(main);
    tr.append(element('td', first(r, ['category', 'categorie', 'zone', 'record_type', 'type', 'document_type', 'dataset'], '—')));
    const details = first(r, ['status', 'object', 'work_description', 'description', 'permit_object', 'purpose', 'capacity', 'spaces', 'number_of_spaces', 'issued_date', 'issue_date', 'date', 'submitted_at', 'created_at', 'created'], '—');
    const td = element('td', details.length > 220 ? details.slice(0, 217) + '…' : details); td.title = details;
    const address = first(r, ['address', 'street', 'street_name']); if (address && label(r) !== address) td.append(element('span', address, 'secondary'));
    tr.append(td);
    const lat = first(r, ['latitude', 'lat']); const lon = first(r, ['longitude', 'lon', 'lng', 'long']);
    const local = element('td', lat && lon ? `${lat}, ${lon}` : geoLabel(r));
    if (lat && lon) local.append(element('span', geoLabel(r), 'secondary')); tr.append(local);
    const source = element('td'); const url = sourceURL(r); if (url) source.append(makeLink(url, 'Original ↗')); else source.textContent = 'Vezi metadatele'; tr.append(source);
    $('table-body').append(tr);
  }
  if (!rows.length) { const tr = element('tr'); const td = element('td', records.length ? 'Nicio înregistrare pentru această căutare.' : 'Exportul nu conține înregistrări. Vezi starea sursei și metadatele.'); td.colSpan = 5; tr.append(td); $('table-body').append(tr); }
  $('table-count').textContent = `${formatNumber(filtered.length)} rezultate`;
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize)); $('page-info').textContent = `${page + 1} / ${pages}`;
  $('previous').disabled = page === 0; $('next').disabled = page + 1 >= pages;
}
function showMap(geo) {
  if (!window.L) { $('map').textContent = 'Biblioteca hărții nu s-a încărcat. GeoJSON rămâne disponibil pentru descărcare.'; return; }
  const map = L.map('map', {scrollWheelZoom: false}).setView([46.173, 21.315], 13);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
  const accent = getComputedStyle(document.body).getPropertyValue('--accent').trim();
  const layer = L.geoJSON(geo, {
    filter: f => !!f.geometry,
    style: f => ({color: accent, weight: 3, opacity: .8, fillOpacity: .12, dashArray: /street|reference|approx|centroid/i.test(geoLabel(f.properties || {})) ? '5 5' : null}),
    pointToLayer: (f, latlng) => L.circleMarker(latlng, {radius: 5, fillColor: /bbox_center|approx|centroid/i.test(geoLabel(f.properties || {})) ? '#b46b21' : accent, color: '#fff', weight: 1.5, fillOpacity: .9}),
    onEachFeature: (f, l) => { const p = f.properties || {}; const popup = element('div'); popup.append(element('div', label(p), 'popup-title'), element('div', 'Precizie: ' + geoLabel(p), 'popup-prop'));
      for (const [k, v] of Object.entries(p)) { if (v === null || v === undefined || typeof v === 'object' || /url|sha256|^id$/.test(k)) continue; const row = element('div', undefined, 'popup-prop'); row.append(element('b', k + ': '), document.createTextNode(String(v).slice(0, 250))); popup.append(row); if (popup.children.length > 9) break; }
      const url = sourceURL(p); if (url) popup.append(makeLink(url, 'Deschide sursa ↗')); l.bindPopup(popup, {maxWidth: 350}); }
  }).addTo(map);
  if (layer.getLayers().length) map.fitBounds(layer.getBounds(), {padding: [28, 28], maxZoom: 15});
  $('map-caption').textContent = `${formatNumber(config.geometry_count)} din ${formatNumber(config.count)} înregistrări au geometrie. Restul rămân în descărcări.`;
}
function textValues(value) {
  if (!value) return [];
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(textValues);
  return Object.entries(value).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`);
}
function showSources() {
  const meta = config.metadata;
  const limits = [...textValues(meta.scope), ...textValues(meta.coverage), ...textValues(meta.limitations), ...textValues(meta.quality_notes), ...textValues(meta.notes), ...textValues(meta.license || meta.licensing)];
  for (const value of limits.slice(0, 14)) $('limitations').append(element('p', value));
  if (!limits.length) $('limitations').append(element('p', 'Verifică README și metadatele înainte de reutilizare. Lipsa geometriei este păstrată explicit.'));
  const urls = new Set();
  const collect = obj => { if (typeof obj === 'string' && /^https?:\/\//.test(obj)) urls.add(obj); else if (Array.isArray(obj)) obj.forEach(collect); else if (obj && typeof obj === 'object') for (const [k, v] of Object.entries(obj)) if (/url|source/.test(k)) collect(v); };
  collect(meta); records.slice(0, 100).forEach(r => {const u = sourceURL(r); if (u) urls.add(u);});
  for (const url of [...urls].slice(0, 12)) { const li = element('li'); li.append(makeLink(safeURL(url), url)); $('source-list').append(li); }
}
async function showCode(language) {
  selectedLanguage = language;
  for (const tab of document.querySelectorAll('[data-language]')) tab.setAttribute('aria-selected', String(tab.dataset.language === language));
  const [file, name] = languages[language];
  if (!snippets[language]) { const response = await fetch('examples/' + file); if (!response.ok) throw new Error('Exemplul nu este disponibil'); snippets[language] = await response.text(); }
  $('code-content').textContent = snippets[language]; $('code-label').textContent = name; $('code-download').href = 'examples/' + file;
}
async function start() {
  const responses = await Promise.all(['portal.json', 'data/records.json', 'data/records.geojson'].map(async url => {const r = await fetch(url); if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json();}));
  [config, records] = responses; filtered = records;
  $('repo-link').href = 'downloads/source.zip';
  $('record-count').textContent = formatNumber(config.count); $('geo-count').textContent = formatNumber(config.geometry_count);
  const date = config.metadata.generated_at || config.metadata.extracted_at || config.metadata.retrieved_at || config.metadata.fetched_at || '';
  $('updated').textContent = date ? date.slice(0, 10).split('-').reverse().join('.') : 'Vezi metadate';
  let note = `${formatNumber(config.count)} înregistrări în export; ${formatNumber(config.geometry_count)} cu geometrie. Coordonatele necunoscute nu sunt înlocuite cu centrul orașului.`;
  if (config.dataset === 'parcari') note += ' Geometria unei străzi este un reper orientativ, nu conturul unei parcări sau poziția fiecărui loc.';
  if (config.dataset === 'sesizari') note += ' Instantaneu al fluxului public, fără nume, mesaje libere, fotografii sau răspunsuri personale; nu reprezintă istoricul complet.';
  if (config.dataset === 'urbanism') note += ' Documentațiile PUG sunt catalogate ca documente; nu sunt transformate în poligoane inventate.';
  $('quality-note').textContent = note;
  for (const file of config.files) { if (file.name.startsWith('records.')) { const type = file.name.split('.').pop(); if ($('size-' + type)) $('size-' + type).textContent = bytes(file.bytes) + ' · Descarcă ↓'; }
    const row = element('div', undefined, 'file-row'); const a = element('a', file.name); a.href = file.path; a.download = ''; row.append(a, element('span', bytes(file.bytes)), element('code', 'SHA-256 ' + file.sha256)); $('all-files').append(row); }
  const extraNames = config.dataset === 'urbanism' ? ['pug_documents.csv', 'pug_documents.json', 'pug_documents.geojson'] : config.dataset === 'parcari' ? ['tariffs.csv', 'tariffs.json', 'zones.csv', 'zones.json', 'rules.json'] : ['schema.json', 'metadata.json'];
  const extras = element('div', undefined, 'extra-downloads');
  extras.append(element('strong', config.dataset === 'urbanism' ? 'Separat: catalogul documentațiilor PUG' : config.dataset === 'parcari' ? 'Separat: tarife, zone și program' : 'Schema și proveniența'));
  for (const name of extraNames) {const file = config.files.find(f => f.name === name); if (file) {const a=element('a', name + ' ↓'); a.href=file.path; a.download=''; extras.append(a);}}
  $('quality-note').before(extras);
  showTable(); showMap(responses[2]); showSources(); await showCode('curl');
}
$('search').addEventListener('input', e => {const term = e.target.value.toLocaleLowerCase('ro'); filtered = records.filter(r => JSON.stringify(r).toLocaleLowerCase('ro').includes(term)); page = 0; showTable();});
$('previous').addEventListener('click', () => {page--; showTable();}); $('next').addEventListener('click', () => {page++; showTable();});
for (const tab of document.querySelectorAll('[data-language]')) tab.addEventListener('click', () => showCode(tab.dataset.language).catch(e => {$('code-content').textContent = e.message;}));
$('copy-code').addEventListener('click', async () => {try {await navigator.clipboard.writeText(snippets[selectedLanguage] || ''); $('copy-code').textContent = 'Copiat'; setTimeout(() => {$('copy-code').textContent = 'Copiază';}, 1500);} catch {$('copy-code').textContent = 'Selectează și copiază textul';}});
start().catch(error => { $('quality-note').textContent = `Previzualizarea nu s-a încărcat: ${error.message}. Deschide pagina printr-un server HTTP; descărcările de mai sus rămân disponibile.`; });
