"""P5.6: imported external directories remain unverified facts, not rankings."""
from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from nb_catalog import (
    ROOT, FACETS, CatalogError, catalogue, load_snapshots,
    safe_url, select,
)
from nb_studio import StudioHTTP, StudioService


class TagCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = catalogue()
        cls.items = cls.catalog["items"]

    def test_attributed_external_imports(self):
        sources = self.catalog["sources"]
        self.assertEqual(len(sources), 4)
        self.assertGreaterEqual(sum(s["count"] for s in sources), 90)
        self.assertGreaterEqual(len(self.items), 90)
        for source in sources:
            self.assertEqual(len(source["commit"]), 40)
            self.assertIn(source["license"], {"CC-BY-SA-4.0", "CC-BY-4.0"})
            self.assertTrue(source["url"].startswith("https://github.com/"))

    def test_not_all_imports_become_verification(self):
        imported = [x for x in self.items if x["evidence"] == "imported_unverified"]
        reviewed = [x for x in self.items if x["evidence"] == "documentation_reviewed"]
        self.assertGreaterEqual(len(imported), 60)
        self.assertGreaterEqual(len(reviewed), 10)
        self.assertTrue(all(x["adult_compatibility"] == "not_tested" for x in self.items))
        self.assertTrue(all(x["hardware_fit"] == "not_tested" for x in self.items))
        self.assertTrue(all(x["model_quality"] == "not_tested" for x in self.items))
        self.assertTrue(all(x["privacy_audit"] == "not_run" for x in self.items))

    def test_catalogue_has_no_duplicate_ids(self):
        ids = [x["id"] for x in self.items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_existing_curated_project_keeps_documentation_evidence(self):
        matches = [x for x in self.items if x["name"] == "SillyTavern"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["evidence"], "documentation_reviewed")
        self.assertGreaterEqual(len(matches[0]["sources"]), 2)

    def test_multi_modality_source_is_not_truncated(self):
        rows = [x for x in self.items if x["name"] == "思畅 AI"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]["modalities"]), {"text", "image", "video", "audio"})

    def test_facets_or_inside_and_across(self):
        found = select(self.items, {
            "modality": ["image", "video"],
            "deployment": ["local"],
            "type": ["model"],
        })
        self.assertGreater(len(found), 2)
        self.assertTrue(all(x["type"] == "model" and x["deployment"] == "local"
                            and bool({"image", "video"}.intersection(x["modalities"])) for x in found))

    def test_unknown_tags_are_rejected_not_parsed_by_llm(self):
        for bad in ({"prompt": ["hello"]}, {"task": ["invent_new_task"]},
                    {"deployment": "local"}):
            with self.assertRaises(CatalogError):
                select(self.items, bad)

    def test_every_visible_url_is_https(self):
        for x in self.items:
            self.assertTrue(safe_url(x["url"]), x["id"])
            self.assertTrue(x["sources"])
            self.assertTrue(all(safe_url(p["url"]) for p in x["sources"]))

    def test_import_rejects_unsafe_urls_and_false_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for src in ROOT.glob("*.json"):
                shutil.copy2(src, dest / src.name)
            first = sorted(dest.glob("*.json"))[0]
            data = json.loads(first.read_text(encoding="utf-8"))
            data["entries"][0]["url"] = "javascript:alert(1)"
            first.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CatalogError):
                load_snapshots(dest)

    def test_import_rejects_fake_model_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            for src in ROOT.glob("*.json"):
                shutil.copy2(src, dest / src.name)
            first = sorted(dest.glob("*.json"))[0]
            data = json.loads(first.read_text(encoding="utf-8"))
            data["entries"][0]["adult_compatibility"] = "verified_unrestricted"
            first.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(CatalogError):
                load_snapshots(dest)

    def test_no_external_request_during_catalogue_generation(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("called external network")):
            data = catalogue()
            self.assertEqual(data["model_invocations"], 0)
            self.assertEqual(data["network_requests"], 0)

    def test_filter_options_all_enumerated(self):
        self.assertEqual(set(FACETS), {"modality", "task", "deployment", "type", "evidence", "link_health"})
        self.assertTrue(all(FACETS[key] for key in FACETS))


class TagCatalogHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.svc = StudioService(Path(cls.tmp.name) / "workspace")
        cls.server = StudioHTTP(("127.0.0.1", 0), cls.svc)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.tmp.cleanup()

    def test_json_catalogue_read_only_and_sourced(self):
        with urlopen(self.base + "/api/catalog", timeout=5) as response:
            self.assertEqual(response.status, 200)
            result = json.load(response)
        self.assertGreaterEqual(len(result["items"]), 90)
        self.assertEqual(result["model_invocations"], 0)
        self.assertEqual(len(result["sources"]), 4)

    def test_tag_ui_replaces_four_step_questionnaire(self):
        with urlopen(self.base + "/discover", timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn('id="filters"', html)
        self.assertIn('id="cards"', html)
        self.assertIn('src="/chooser.js"', html)
        self.assertNotIn("<textarea", html)
        self.assertNotIn("<input", html)
        self.assertNotIn('id="next"', html)


if __name__ == "__main__":
    unittest.main()
