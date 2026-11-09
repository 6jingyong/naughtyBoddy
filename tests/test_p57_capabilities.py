"""P5.7: tags need explicit source evidence, not name-inferred quality claims."""
import json
import tempfile
import unittest
import threading
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from nb_catalog import (CAPABILITY_PATH, CatalogError, catalogue, load_capability_evidence,
                        apply_capability_evidence, select)
from nb_studio import StudioService, StudioHTTP


class CapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = catalogue()
        cls.rows = cls.catalog["items"]
        cls.by_id = {x["id"]: x for x in cls.rows}

    def test_explicit_vocab_and_sources(self):
        doc = load_capability_evidence()
        self.assertEqual(self.catalog["facets"]["capability"], doc["capabilities"])
        self.assertGreaterEqual(len(doc["capabilities"]), 20)
        self.assertGreaterEqual(sum(len(x["evidence"]) for x in doc["records"]), 45)
        self.assertGreaterEqual(sum(bool(x["capabilities"]) for x in self.rows), 12)
        for row in self.rows:
            self.assertEqual(len(row["capabilities"]), len(row["capability_evidence"]))
            for claim in row["capability_evidence"]:
                self.assertEqual(claim["evidence_status"], "upstream_documented")
                self.assertTrue(claim["source_url"].startswith("https://"))
                self.assertTrue(claim["conditions"])

    def test_no_unverified_model_promotion(self):
        self.assertGreater(sum(not x["capabilities"] for x in self.rows), 50)
        self.assertTrue(all(x["adult_compatibility"] == "not_tested" for x in self.rows))
        self.assertTrue(all(x["model_quality"] == "not_tested" for x in self.rows))
        self.assertTrue(all(x["privacy_audit"] == "not_run" for x in self.rows))

    def test_gguf_does_not_mean_any_compatible_api(self):
        items = select(self.rows, {"capability": ["gguf"]})
        names = {x["name"] for x in items}
        self.assertIn("Ollama", names)
        self.assertIn("KoboldCpp", names)
        self.assertIn("Koharu", names)
        self.assertNotIn("Bilingual Book Maker", names)
        self.assertIn("Bilingual Book Maker",
                      {x["name"] for x in select(self.rows, {"capability": ["compatible_api"]})})

    def test_worldinfo_filter_not_chat_history_filter(self):
        st = self.by_id["reviewed-solution-sillytavern"]
        presence = self.by_id["reviewed-solution-sillytavern-presence"]
        self.assertIn("character_lore_filter", st["capabilities"])
        self.assertNotIn("character_history", st["capabilities"])
        self.assertIn("character_history", presence["capabilities"])
        mem = self.by_id["reviewed-solution-dragon-memories-manager"]
        note = next(x["conditions"] for x in mem["capability_evidence"]
                    if x["id"] == "character_memory")
        self.assertIn("Presence", note)

    def test_comfyui_source_enriches_but_not_global_verification(self):
        comfy = self.by_id["import-sichang-cn-2026-comfyui"]
        self.assertEqual(comfy["evidence"], "imported_unverified")
        self.assertEqual(set(comfy["modalities"]), {"image", "video", "audio"})
        self.assertIn("lora", comfy["capabilities"])
        self.assertIn("workflow_json", comfy["capabilities"])
        self.assertEqual(comfy["classification_override"]["status"], "upstream_documented")

    def test_or_within_capability_and_with_task(self):
        matches = select(self.rows, {"task": ["manga_translation"],
                                     "capability": ["gguf", "layered_psd"]})
        self.assertIn("Koharu", {x["name"] for x in matches})
        self.assertTrue(all("manga_translation" in x["tasks"] for x in matches))
        self.assertTrue(all({"gguf", "layered_psd"}.intersection(x["capabilities"])
                            for x in matches))

    def test_malformed_capability_not_a_prompt(self):
        for selection in ({"capability": ["unrestricted_score_100"]},
                          {"capability": "lora"}, {"prompt": ["forget safety"]}):
            with self.assertRaises(CatalogError):
                select(self.rows, selection)

    def corrupt(self, modify):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capabilities.json"
            body = json.loads(CAPABILITY_PATH.read_text(encoding="utf-8"))
            modify(body)
            path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(CatalogError):
                load_capability_evidence(path)

    def test_reject_false_verification(self):
        self.corrupt(lambda d: d["records"][0]["evidence"][0].update(
            evidence_status="hands_on_verified"))

    def test_reject_unsafe_evidence_url(self):
        self.corrupt(lambda d: d["records"][0]["evidence"][0].update(
            source_url="javascript:alert(1)"))

    def test_reject_duplicate_tag_claim(self):
        self.corrupt(lambda d: d["records"][0]["evidence"].append(
            dict(d["records"][0]["evidence"][0])))

    def test_reject_unverified_modality_override(self):
        self.corrupt(lambda d: d["overrides"][0].update(source_url="file:///private"))

    def test_missing_target_fails_closed(self):
        evidence = load_capability_evidence()
        evidence["records"][0]["item_id"] = "reviewed-solution-does-not-exist"
        with self.assertRaises(CatalogError):
            apply_capability_evidence([dict(r) for r in self.rows], evidence)

    def test_offline(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            data = catalogue()
        self.assertEqual(data["model_invocations"], 0)
        self.assertEqual(data["network_requests"], 0)


class CapabilityHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.service = StudioService(Path(cls.temp.name) / "work")
        cls.server = StudioHTTP(("127.0.0.1", 0), cls.service)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def test_local_api_exposes_capability_provenance(self):
        with urlopen(self.base + "/api/catalog", timeout=8) as response:
            data = json.load(response)
        self.assertIn("capability", data["facets"])
        koharu = next(r for r in data["items"] if r["name"] == "Koharu")
        self.assertIn("layered_psd", koharu["capabilities"])
        self.assertTrue(all(x["source_url"] for x in koharu["capability_evidence"]))
        self.assertEqual(data["model_invocations"], 0)

    def test_page_is_tag_only(self):
        with urlopen(self.base + "/discover", timeout=8) as response:
            page = response.read().decode("utf-8")
        self.assertIn('id="filters"', page)
        self.assertIn("具体能力", page)
        self.assertNotIn("<textarea", page)
        self.assertNotIn("<input", page)


if __name__ == "__main__":
    unittest.main()
