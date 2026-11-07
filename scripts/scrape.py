#!/usr/bin/env python3
"""Fetch the public MyArad map feed and export a strict, privacy-safe projection.

Standard-library only. No account, browser session, Google Maps key or CAPTCHA is
needed for the read-only endpoint used by the public map's own Angular client.
Raw complaint messages/replies are never written by this program.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PORTAL_URL = "https://myarad.primariaarad.ro/dm_arad/servicii.nsf/pagini/sesizari%2Bonline%2Bpe%2Bharta"
FEED_URL = "https://myarad.primariaarad.ro/dm_arad/ext_services.nsf/xsp/.jaxrs/myCity/getAll"
CLIENT_URL = "https://myarad.primariaarad.ro/dm_arad/servicii.nsf/sobis.mycity.js?Open"
UTILITY_URL = "https://myarad.primariaarad.ro/dm_arad/servicii.nsf/sobis.utils.js?Open"
HISTORICAL_POLICY_URL = "https://www.primariaarad.ro/dm_arad/portal.nsf/9886ED9671CAD1B5C2258805003EF921/%24FILE/5.%20SIDU%20Arad%202021-2027.%20Martie%202022.pdf?Open="
CODE_LICENSE = "MIT"
DATA_LICENSE = "Upstream reuse licence not identified; MIT applies to code only."
FIELDS = [
    "id", "source_id", "record_type", "name", "category", "status",
    "submitted_at", "latitude", "longitude", "coordinate_source",
    "coordinate_precision", "geocode_method", "source_url", "source_page",
    "source_sha256", "retrieved_at",
]
KNOWN_STATUSES = {
    "Preluata", "Preluată", "Solutionata", "Soluționată", "In asteptare",
    "În așteptare", "Respinsa", "Respinsă", "In lucru", "În lucru",
}
KNOWN_CATEGORIES = {
    "Altele", "Caini comunitari", "Canalizare pluviala", "Deszapezire",
    "Iluminat stradal", "Locuri de joaca", "Lucrari edilitare in desfasurare",
    "Masini abandonate sau parcate neregulamentar", "Ordine publica",
    "Parcari publice", "Parcari rezidentiale", "Probleme carosabil/trotuare/asfaltare",
    "Probleme de mediu", "Salubrizare menajera", "Salubrizare stradala",
    "Semnalizare rutiera", "Spatii verzi/parcuri",
    "Toaletare copaci, intretinere gard viu", "Transport public",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def safe_source_id(value) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Complaint lacks a stable public id; refusing to invent an id from free text")
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", text):
        return text
    # Arbitrary identifiers may themselves contain names or contact information.
    return "hashed-" + hashlib.sha256(text.encode()).hexdigest()[:24]


def parse_date(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # The live field is DD/MM/YYYY: source createdText confirms e.g.
    # 06/07/2025 = 6 iulie 2025. It is a date, not a UTC timestamp.
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T[^\s]+", text):
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
        except ValueError:
            pass
    raise ValueError("Unsupported submitted date format; schema may have changed")


def parse_position(value) -> tuple[float | None, float | None]:
    """The source stores Google marker position as a JSON string [lat, lon]."""
    if value in (None, "", []):
        return None, None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None, None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None, None
    if any(isinstance(v, bool) for v in value):
        return None, None
    try:
        lat, lon = map(float, value)
    except (ValueError, TypeError):
        return None, None
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None, None
    if lat == 0 and lon == 0:
        return None, None
    # Do not silently swap coordinates: that would conceal upstream errors.
    return lat, lon


def normalize_payload(payload, source_url: str, retrieved_at: str, source_sha256: str) -> tuple[list[dict], dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError("Expected the MyArad JSON object with an entries array; HTML/auth errors are not empty data")
    entries = payload["entries"]
    total = payload.get("total", len(entries))
    if isinstance(total, bool) or not isinstance(total, int) or total < len(entries):
        raise ValueError("Inconsistent source total")
    config = payload.get("config") or {}
    categories = set(KNOWN_CATEGORIES)
    if isinstance(config, dict):
        for item in config.get("category", []):
            # Categories are server-controlled configuration, not complaint text.
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                name = item["name"].strip()
                if 0 < len(name) <= 120 and not re.search(r"[@<>\d]", name):
                    categories.add(name)
    records = []
    seen = set()
    omitted_unknown_category = 0
    omitted_unknown_status = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Non-object complaint entry")
        sid = safe_source_id(entry.get("id"))
        key = sid.lower()
        if key in seen:
            raise ValueError("Duplicate source complaint id: " + sid)
        seen.add(key)
        category = entry.get("categorie", "")
        if category not in categories:
            category = "Categorie necunoscută"
            omitted_unknown_category += 1
        status = entry.get("status", "")
        if status not in KNOWN_STATUSES:
            status = "Stare necunoscută"
            omitted_unknown_status += 1
        lat, lon = parse_position(entry.get("position"))
        records.append({
            "id": "myarad-" + key,
            "source_id": sid,
            "record_type": "public_complaint",
            "name": "Sesizare: " + category,
            "category": category,
            "status": status,
            "submitted_at": parse_date(entry.get("created")),
            "latitude": lat,
            "longitude": lon,
            "coordinate_source": source_url if lat is not None else "",
            "coordinate_precision": "reported map marker; accuracy not independently verified" if lat is not None else "unknown",
            "geocode_method": "source_original" if lat is not None else "missing",
            "source_url": source_url,
            "source_page": PORTAL_URL,
            "source_sha256": source_sha256,
            "retrieved_at": retrieved_at,
        })
    records.sort(key=lambda r: (r["submitted_at"], r["source_id"]), reverse=True)
    details = {
        "source_total": total,
        "snapshot_complete_relative_to_feed_total": total == len(entries),
        "unknown_categories_replaced": omitted_unknown_category,
        "unknown_statuses_replaced": omitted_unknown_status,
        "category_count": len(categories),
        "categories": sorted(categories),
    }
    return records, details


def fetch_payload(endpoint: str, timeout: int) -> tuple[bytes, str]:
    # These are the public client's headers and cache-busting convention. Some
    # source/proxy caches return 406 when the JSON Accept header is absent.
    url = endpoint + ("&" if "?" in endpoint else "?") + "_dc=" + str(time.time())
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; AradPublicData/1.0)",
        "Accept": "application/json, text/plain, */*",
        "Referer": PORTAL_URL,
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("Unexpected HTTP status " + str(response.status))
        raw = response.read(20_000_001)
        if len(raw) > 20_000_000:
            raise ValueError("Feed exceeds the 20 MB safety bound; review source pagination")
        return raw, response.geturl()


def export(records: list[dict], details: dict, out: Path, retrieved_at: str, source_url: str, source_sha256: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "records.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    write_json(out / "records.json", records)
    write_json(out / "records.geojson", {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "id": row["id"],
            "geometry": {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]} if row["latitude"] is not None else None,
            "properties": dict(row),
        } for row in records],
    })
    valid = sum(row["latitude"] is not None for row in records)
    dates = [row["submitted_at"] for row in records if row["submitted_at"]]
    bounds = None
    if valid:
        pts = [(row["longitude"], row["latitude"]) for row in records if row["latitude"] is not None]
        bounds = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
    metadata = {
        "dataset": "arad-complaints", "title": "Sesizări publice MyArad — proiecție fără text liber",
        "description": "Instantaneu al sesizărilor afișate de API-ul hărții publice MyArad, cu câmpuri strict selectate și coordonatele originale.",
        "generated_at": retrieved_at, "record_count": len(records),
        "geocoded_count": valid, "source_coordinate_count": valid,
        "externally_geocoded_count": 0, "missing_coordinate_count": len(records) - valid,
        "status": "ok" if details["snapshot_complete_relative_to_feed_total"] else "partial",
        "license": DATA_LICENSE, "code_license": CODE_LICENSE,
        "source_urls": [PORTAL_URL, FEED_URL, CLIENT_URL, UTILITY_URL],
        "source_url": source_url, "source_sha256": source_sha256,
        "scope": "Public GET myCity/getAll snapshot only; not an archive of all submitted complaints.",
        "coverage_start": min(dates) if dates else None,
        "coverage_end": max(dates) if dates else None,
        "bbox": bounds, "crs": "EPSG:4326", "geojson_coordinate_order": "longitude, latitude",
        "categories": dict(sorted(Counter(row["category"] for row in records).items())),
        "statuses": dict(sorted(Counter(row["status"] for row in records).items())),
        "privacy": {
            "strategy": "Allowlist structured fields; omit all message/reply text and all attachments.",
            "excluded_fields": ["mesaj", "raspuns", "createdText", "marker", "culoare", "reporter names", "email", "phone", "attachments"],
            "name_field": "Generated solely from the controlled category, not the original complaint text.",
        },
        "limitations": [
            "Records present in the public map feed only; no completeness claim about historical submissions.",
            "Original map positions are unverified reported locations, not surveyed coordinates.",
            "Missing or malformed positions remain null. No city centroid or guessed address is substituted.",
            "An older official strategy described 30-day unresolved and 5-day resolved display windows; this snapshot contains older dates, so those windows are not assumed to be currently enforced.",
            "No freely reusable upstream data licence was identified. Public accessibility alone does not establish redistribution rights.",
        ],
        "source_details": details,
    }
    write_json(out / "metadata.json", metadata)
    # Reproducible public input with only the same safe fields as the exports.
    # Original raw message/reply data never touches a tracked snapshot.
    sanitized = {
        "format": "myarad-safe-snapshot-v1", "retrieved_at": retrieved_at,
        "original_source_url": source_url, "original_source_sha256": source_sha256,
        "total": details["source_total"],
        "entries": [{
            "id": row["source_id"], "categorie": row["category"],
            "status": row["status"], "created": row["submitted_at"],
            "position": [row["latitude"], row["longitude"]] if row["latitude"] is not None else None,
        } for row in records],
        "config": {"category": [{"name": value} for value in details["categories"]]},
    }
    write_json(out / "source-snapshot.sanitized.json", sanitized)
    write_json(out / "schema.json", {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MyArad privacy-safe records", "type": "array",
        "items": {"type": "object", "required": FIELDS, "additionalProperties": False,
                  "properties": {field: {"type": ["number", "null"]} if field in ("latitude", "longitude") else {"type": "string"} for field in FIELDS}},
    })
    return metadata


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", "--out", type=Path, default=Path("data"))
    parser.add_argument("--input", type=Path, help="Process a saved original API JSON or the safe snapshot, without a network request")
    parser.add_argument("--endpoint", default=FEED_URL, help="Override after verifying a public MyArad API relocation")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retrieved-at", help="Known UTC retrieval time for an imported original API snapshot")
    args = parser.parse_args(argv)
    now = utc_now()
    try:
        if args.input:
            raw = args.input.read_bytes()
            source_url = args.endpoint
            now = args.retrieved_at or datetime.fromtimestamp(args.input.stat().st_mtime, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        else:
            raw, source_url = fetch_payload(args.endpoint, args.timeout)
            now = utc_now()
        payload = json.loads(raw)
        sha = hashlib.sha256(raw).hexdigest()
        if args.input and isinstance(payload, dict) and payload.get("format") == "myarad-safe-snapshot-v1":
            now = payload["retrieved_at"]
            source_url = payload["original_source_url"]
            sha = payload["original_source_sha256"]
        records, details = normalize_payload(payload, source_url, now, sha)
        metadata = export(records, details, args.output, now, source_url, sha)
    except (OSError, ValueError, TypeError, urllib.error.URLError) as exc:
        # Do not replace a previous good dataset with an empty result on failure.
        print("Extraction failed; existing exports preserved: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"record_count": metadata["record_count"], "geocoded_count": metadata["geocoded_count"], "status": metadata["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
