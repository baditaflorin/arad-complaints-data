#!/usr/bin/env python3
"""Check dataset consistency, geo ranges, provenance, uniqueness and published copies."""
from pathlib import Path
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
def check_coordinates(value):
    if not isinstance(value, (list, tuple)):
        raise AssertionError('Invalid coordinates container')
    if value and isinstance(value[0], (int, float)):
        assert len(value) >= 2 and all(isinstance(x, (int,float)) and math.isfinite(x) for x in value), value
        assert -180 <= value[0] <= 180 and -90 <= value[1] <= 90, value
    else:
        for item in value: check_coordinates(item)

def validate():
    data = ROOT/'data'
    records = json.loads((data/'records.json').read_text())
    assert isinstance(records, list)
    with (data/'records.csv').open(newline='', encoding='utf-8-sig') as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == len(records), 'CSV and JSON counts differ'
    ids = [str(r.get('id', r.get('record_id', ''))) for r in records]
    assert all(ids) and len(set(ids)) == len(ids), 'Missing or duplicate identifiers'
    geo = json.loads((data/'records.geojson').read_text())
    assert geo['type'] == 'FeatureCollection'
    seen = set()
    mapped = 0
    for f in geo['features']:
        assert f['type'] == 'Feature' and isinstance(f['properties'], dict)
        fid = str(f.get('id', f['properties'].get('id', f['properties'].get('record_id', ''))))
        if fid:
            assert fid in set(ids), 'GeoJSON references unknown record'
            assert fid not in seen, 'Duplicate GeoJSON identifier'
            seen.add(fid)
        g = f.get('geometry')
        if g:
            assert g['type'] in ['Point','LineString','MultiLineString','Polygon','MultiPolygon','MultiPoint','GeometryCollection']
            if g['type'] != 'GeometryCollection': check_coordinates(g['coordinates'])
            else:
                for item in g['geometries']: check_coordinates(item['coordinates'])
            mapped += 1
    forbidden = {'reporter_name', 'reporter_email', 'reporter_phone', 'cnp', 'email', 'phone', 'beneficiary', 'beneficiar', 'petent'}
    for r in records:
        assert not forbidden.intersection(r), f'Personal data field in {r.get("id")}'
        assert any(r.get(k) for k in ['source_url','source_page_url','document_url','url','source']), f'Missing provenance for {r.get("id")}'
    meta = json.loads((data/'metadata.json').read_text())
    assert meta, 'Missing metadata'
    docs = ROOT/'docs'
    if (docs/'portal.json').exists():
        portal = json.loads((docs/'portal.json').read_text())
        assert portal['count'] == len(records) and portal['geometry_count'] == mapped
        for f in portal['files']:
            p=docs/f['path']
            assert p.stat().st_size == f['bytes']
            assert hashlib.sha256(p.read_bytes()).hexdigest() == f['sha256']
        for name in ['records.csv','records.json','records.geojson','metadata.json']:
            assert (docs/'data'/name).read_bytes() == (data/name).read_bytes()
    print(json.dumps({'records': len(records), 'csv_rows': len(csv_rows), 'geojson_features':len(geo['features']), 'with_geometry': mapped, 'validation':'passed'}))

if __name__ == '__main__': validate()
