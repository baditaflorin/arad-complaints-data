"""Contract, privacy and geometry tests with intentionally synthetic test inputs."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("scrape", Path(__file__).parents[1] / "scripts" / "scrape.py")
scrape = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scrape)


def fixture(**overrides):
    entry = {"id": "TEST-1", "categorie": "Iluminat stradal", "status": "Preluata", "created": "06/07/2025", "position": "[46.1737, 21.3196]"}
    entry.update(overrides)
    return {"entries": [entry], "total": 1}


class ContractTests(unittest.TestCase):
    def normalize(self, payload):
        return scrape.normalize_payload(payload, "https://example.invalid/public-feed", "2026-11-07T10:00:00Z", "a" * 64)

    def test_source_day_first_date_not_us_date(self):
        rows, _ = self.normalize(fixture())
        self.assertEqual(rows[0]["submitted_at"], "2025-07-06")

    def test_original_coordinates_and_geojson_order(self):
        rows, details = self.normalize(fixture())
        self.assertEqual((rows[0]["latitude"], rows[0]["longitude"]), (46.1737, 21.3196))
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            scrape.export(rows, details, out, rows[0]["retrieved_at"], rows[0]["source_url"], rows[0]["source_sha256"])
            geometry = json.loads((out / "records.geojson").read_text())["features"][0]["geometry"]
            self.assertEqual(geometry["coordinates"], [21.3196, 46.1737])

    def test_missing_bad_and_nonfinite_coordinates_stay_null(self):
        for value in (None, "invalid", "[0, 0]", "[999, 21]", "[NaN, 21]", [True, 21], [46.1]):
            with self.subTest(value=value):
                rows, _ = self.normalize(fixture(position=value))
                self.assertIsNone(rows[0]["latitude"])
                self.assertIsNone(rows[0]["longitude"])
                self.assertEqual(rows[0]["geocode_method"], "missing")

    def test_all_free_text_and_unknown_fields_are_omitted(self):
        pii = "TEST-PERSON test@example.invalid +40700111222"
        payload = fixture(mesaj=pii, raspuns=pii, reporter=pii, email=pii, attachments=[pii])
        rows, details = self.normalize(payload)
        self.assertNotIn(pii, json.dumps(rows))
        self.assertNotIn("mesaj", rows[0])
        self.assertNotIn("raspuns", rows[0])
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            scrape.export(rows, details, out, rows[0]["retrieved_at"], rows[0]["source_url"], rows[0]["source_sha256"])
            for path in out.iterdir():
                self.assertNotIn(pii, path.read_text())

    def test_arbitrary_category_or_status_cannot_smuggle_free_text(self):
        rows, details = self.normalize(fixture(categorie="Person test@example.invalid", status="Contact +40700111222"))
        self.assertEqual(rows[0]["category"], "Categorie necunoscută")
        self.assertEqual(rows[0]["status"], "Stare necunoscută")
        self.assertNotIn("example.invalid", rows[0]["name"])
        self.assertEqual(details["unknown_categories_replaced"], 1)

    def test_duplicate_ids_fail_instead_of_silent_deduplication(self):
        payload = fixture()
        payload["entries"].append(dict(payload["entries"][0]))
        payload["total"] = 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.normalize(payload)

    def test_incomplete_total_is_explicit(self):
        payload = fixture()
        payload["total"] = 10
        rows, details = self.normalize(payload)
        self.assertFalse(details["snapshot_complete_relative_to_feed_total"])
        with tempfile.TemporaryDirectory() as directory:
            metadata = scrape.export(rows, details, Path(directory), rows[0]["retrieved_at"], rows[0]["source_url"], rows[0]["source_sha256"])
            self.assertEqual(metadata["status"], "partial")

    def test_saved_sanitized_snapshot_reproduces_primary_exports(self):
        rows, details = self.normalize(fixture())
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first", Path(directory) / "second"
            scrape.export(rows, details, first, rows[0]["retrieved_at"], rows[0]["source_url"], rows[0]["source_sha256"])
            self.assertEqual(scrape.main(["--input", str(first / "source-snapshot.sanitized.json"), "--output", str(second)]), 0)
            for filename in ("records.csv", "records.json", "records.geojson", "metadata.json"):
                self.assertEqual((first / filename).read_bytes(), (second / filename).read_bytes())

    def test_bad_input_does_not_overwrite_previous_good_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / "records.json").write_text('["PREVIOUS"]')
            invalid = out / "input.json"
            invalid.write_text('{"error":"not entries"}')
            self.assertEqual(scrape.main(["--input", str(invalid), "--output", str(out)]), 1)
            self.assertEqual((out / "records.json").read_text(), '["PREVIOUS"]')


if __name__ == "__main__":
    unittest.main()
