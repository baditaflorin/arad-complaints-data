// node examples/download.mjs [JSON_URL] [OUTPUT_PATH] -- Node.js 18+
import { writeFile } from 'node:fs/promises';

const url = process.argv[2] || 'https://baditaflorin.github.io/arad-complaints-data/data/records.json';
const output = process.argv[3] || 'records.json';
const response = await fetch(url, { headers: { accept: 'application/json' }, signal: AbortSignal.timeout(60000) });
if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
const records = await response.json();
if (!Array.isArray(records)) throw new Error('Expected a JSON array');
await writeFile(output, JSON.stringify(records, null, 2) + '\n', 'utf8');
console.log(`${records.length} records saved to ${output}`);
