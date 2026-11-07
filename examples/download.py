#!/usr/bin/env python3
"""python examples/download.py [JSON_URL] [OUTPUT_PATH] -- Python 3, stdlib only."""
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

url = sys.argv[1] if len(sys.argv) > 1 else 'https://baditaflorin.github.io/arad-complaints-data/data/records.json'
output = Path(sys.argv[2] if len(sys.argv) > 2 else 'records.json')
with urlopen(Request(url, headers={'User-Agent': 'AradDataExample/1.0'}), timeout=60) as response:
    records = json.load(response)
if not isinstance(records, list):
    raise SystemExit('Expected a JSON array')
output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(records)} records saved to {output}')
