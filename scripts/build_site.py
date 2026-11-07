#!/usr/bin/env python3
"""Build a dependency-free static download portal from the checked-in exports."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
KIND = ROOT.name
PROFILES = {
    'arad-urbanism-data': ('Urbanism Arad', 'Autorizații și documentații PUG', 'urbanism', '#006d5b'),
    'arad-parking-data': ('Parcări Arad', 'Inventarul public Recons, tarife și program', 'parcari', '#9b4c16'),
    'arad-complaints-data': ('Sesizări Arad', 'Sesizări din harta publică MyArad', 'sesizari', '#4256b5'),
}
TITLE, SUBTITLE, DATASET, ACCENT = PROFILES.get(KIND, (KIND, 'Date locale, surse și metodă', KIND, '#006d5b'))

def build():
    docs = ROOT / 'docs'
    docs.mkdir(exist_ok=True)
    for part in ('assets', 'data', 'examples'):
        source = ROOT / part
        target = docs / part
        if target.exists():
            shutil.rmtree(target)
        if source.exists():
            shutil.copytree(source, target)
    records = json.loads((ROOT / 'data/records.json').read_text())
    metadata = json.loads((ROOT / 'data/metadata.json').read_text())
    geo = json.loads((ROOT / 'data/records.geojson').read_text())
    geometries = sum(bool(f.get('geometry')) for f in geo.get('features', []))
    manifest = []
    for p in sorted((docs / 'data').rglob('*')):
        if p.is_file():
            manifest.append({'name': p.name, 'path': p.relative_to(docs).as_posix(), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    config = {'title': TITLE, 'subtitle': SUBTITLE, 'dataset': DATASET, 'repo': KIND, 'owner': 'baditaflorin', 'count': len(records), 'geometry_count': geometries, 'metadata': metadata, 'files': manifest}
    downloads=docs/'downloads'
    downloads.mkdir(exist_ok=True)
    with zipfile.ZipFile(downloads/'source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for folder in ['scripts','tests','examples','assets','data','raw','sources','.github']:
            for p in sorted((ROOT/folder).rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc':
                    archive.write(p, p.relative_to(ROOT).as_posix())
        for name in ['README.md','PAGES.md','LICENSE','DATA_LICENSE.md','LICENSE-DATA.md','requirements.txt','.gitignore']:
            if (ROOT/name).exists(): archive.write(ROOT/name,name)
    (docs / 'portal.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n')
    (docs / '.nojekyll').write_text('')
    html = (ROOT / 'assets/index.template.html').read_text().replace('{{TITLE}}', TITLE).replace('{{SUBTITLE}}', SUBTITLE).replace('{{ACCENT}}', ACCENT)
    (docs / 'index.html').write_text(html)
    print(json.dumps({'site': str(docs), 'records': len(records), 'with_geometry': geometries, 'files': len(manifest)}))

if __name__ == '__main__':
    build()
