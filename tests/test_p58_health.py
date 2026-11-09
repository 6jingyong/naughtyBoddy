"""P5.8: link and identity quality checks never turn uncertainty into deletion."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from nb_catalog import catalogue, select
from nb_catalog_health import (
    ROOT, HealthError, annotate_health, identity_review,
    load_link_health, name_key, url_key,
)
from nb_studio import StudioHTTP, StudioService


class DirectoryHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue()
        cls.items = cls.data["items"]
        cls.ids = {x["id"]: x for x in cls.items}

    def test_catalog_after_migration_has_no_double_comfyui(self):
        matches = [x for x in self.items if x["name"] == "ComfyUI"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(self.items), 106)
        row = matches[0]
        self.assertEqual(row["id"], "reviewed-solution-comfyui")
        self.assertEqual(row["url"], "https://github.com/Comfy-Org/ComfyUI")
        self.assertGreaterEqual(len(row["sources"]), 2)
        self.assertIn("workflow_json", row["capabilities"])
        self.assertEqual(row["evidence"], "imported_unverified")

    def test_audit_is_partial_and_date_scoped(self):
        summary = self.data["health_summary"]
        counts = summary["counts"]
        self.assertEqual(counts["repository_metadata_found"], 18)
        self.assertEqual(counts["conflicting_evidence"], 1)
        self.assertEqual(sum(counts.values()), len(self.items))
        self.assertGreater(counts["not_checked"], 70)
        self.assertEqual(summary["checked_on"], "2026-11-09")

    def test_404_conflict_is_not_deletion(self):
        row = self.ids["reviewed-solution-libre-manga-translator"]
        self.assertEqual(row["link_health"], "conflicting_evidence")
        self.assertIn("待", row["link_check"]["note"])
        self.assertTrue(row["url"].startswith("https://github.com/"))
        self.assertEqual(row["adult_compatibility"], "not_tested")

    def test_old_code_push_does_not_mean_abandoned(self):
        risu = self.ids["reviewed-solution-risuai"]
        self.assertEqual(risu["link_health"], "repository_metadata_found")
        self.assertTrue(risu["link_check"]["last_code_push"].startswith("2025"))
        self.assertFalse(risu["link_check"]["repo_archived"])
        self.assertNotIn("abandoned", risu["link_check"])

    def test_shared_destinations_do_not_merge_model_variants(self):
        groups = self.data["identity_review"]["shared_destinations"]
        self.assertGreaterEqual(len(groups), 5)
        qwen = next(g for g in groups if "muapi.ai/qwen-abliterated-api" in g["destination_key"])
        self.assertGreaterEqual(len(qwen["items"]), 4)
        self.assertEqual(qwen["interpretation"], "shared_destination_not_proof_of_duplicate")
        self.assertTrue(all(x["id"] in self.ids for x in qwen["items"]))

    def test_same_model_name_different_hosting_not_auto_merged(self):
        groups = self.data["identity_review"]["same_name_different_destinations"]
        self.assertTrue(any(g["name_key"] == "wan22" for g in groups))
        self.assertIn("No automatic merge", self.data["identity_review"]["policy"])

    def test_verified_old_repository_migration_is_explicit(self):
        migrations = self.data["health_summary"]["migrations"]
        self.assertEqual(len(migrations), 1)
        self.assertEqual(migrations[0]["former_url"], "https://github.com/comfyanonymous/ComfyUI")
        self.assertEqual(migrations[0]["canonical_url"], "https://github.com/Comfy-Org/ComfyUI")
        self.assertEqual(migrations[0]["observed_response"], "Moved Permanently")

    def test_selection_can_filter_only_checked_repositories(self):
        matches = select(self.items, {"link_health": ["repository_metadata_found"],
                                      "type": ["tool"]})
        self.assertTrue(matches)
        self.assertTrue(all(x["link_health"] == "repository_metadata_found" for x in matches))
        self.assertTrue(all(x["type"] == "tool" for x in matches))

    def test_unknown_status_cannot_be_used_as_open_query(self):
        from nb_catalog import CatalogError
        with self.assertRaises(CatalogError):
            select(self.items, {"link_health": ["repository_deleted_verified"]})

    def mutate(self, changer):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "link-health.json"
            doc = json.loads(ROOT.read_text(encoding="utf-8"))
            changer(doc)
            path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(HealthError):
                load_link_health(path)

    def test_forged_200_without_evidence_fails(self):
        self.mutate(lambda d: d["observations"][0].update(evidence_url="file:///private"))

    def test_duplicate_observation_ids_fail(self):
        self.mutate(lambda d: d["observations"].append(dict(d["observations"][0])))

    def test_link_change_invalidates_previous_audit(self):
        doc = load_link_health()
        clone = [dict(x) for x in self.items]
        first = next(x for x in clone if x["id"] == doc["observations"][0]["item_id"])
        first["url"] = "https://github.com/some/other-repo"
        with self.assertRaises(HealthError):
            annotate_health(clone, doc)

    def test_unknown_audit_target_fails_loudly(self):
        doc = load_link_health()
        doc["observations"][0]["item_id"] = "no-such-tool"
        with self.assertRaises(HealthError):
            annotate_health([dict(x) for x in self.items], doc)

    def test_health_report_does_not_require_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("External URL touched")):
            snapshot = catalogue()
        self.assertEqual(snapshot["network_requests"], 0)
        self.assertEqual(snapshot["model_invocations"], 0)

    def test_url_and_name_keys_only_detect_candidates(self):
        self.assertEqual(url_key("https://muapi.ai/GLM-API/"),
                         url_key("https://www.muapi.ai/glm-api"))
        self.assertEqual(name_key("Wan 2.2"), name_key("Wan2.2"))


class HealthHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.service = StudioService(Path(cls.tmp.name) / "workspace")
        cls.server = StudioHTTP(("127.0.0.1", 0), cls.service)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=3)
        cls.tmp.cleanup()

    def test_catalog_includes_link_provenance(self):
        with urlopen(self.base + "/api/catalog", timeout=10) as res:
            result = json.load(res)
        self.assertIn("link_health", result["facets"])
        self.assertIn("identity_review", result)
        self.assertEqual(result["health_summary"]["counts"]["conflicting_evidence"], 1)
        self.assertEqual(result["model_invocations"], 0)

    def test_page_only_offers_tags(self):
        with urlopen(self.base + "/discover", timeout=8) as res:
            html = res.read().decode("utf-8")
        self.assertIn('id="health-count"', html)
        self.assertIn('id="identity-list"', html)
        self.assertNotIn("<textarea", html)
        self.assertNotIn("<input", html)


if __name__ == "__main__":
    unittest.main()
