"""P5.9 text-first scope: public Discovery cannot expose media workflows."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from nb_catalog import catalogue
from nb_text_catalog import TEXT_CAPABILITIES, TEXT_TASKS, is_text_first, text_catalogue
from nb_studio import StudioHTTP, StudioService


class TextFirstScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = catalogue()
        cls.focused = text_catalogue()
        cls.rows = cls.focused["items"]

    def test_public_scope_is_strictly_text(self):
        self.assertEqual(self.focused["scope"], "text_first")
        self.assertGreater(len(self.rows), 15)
        self.assertLess(len(self.rows), len(self.full["items"]))
        for row in self.rows:
            self.assertEqual(row["modalities"], ["text"])
            self.assertTrue(set(row["tasks"]).issubset(TEXT_TASKS))

    def test_core_text_projects_remain_discoverable(self):
        names = {r["name"] for r in self.rows}
        self.assertIn("SillyTavern", names)
        self.assertIn("Bilingual Book Maker", names)
        self.assertIn("KoboldCpp", names)
        self.assertIn("Ollama", names)
        self.assertIn("Dragon Memories Manager", names)

    def test_media_projects_and_models_are_not_in_public_search(self):
        ids = {r["id"] for r in self.rows}
        for excluded in ("reviewed-solution-koharu", "reviewed-solution-comfyui",
                         "reviewed-solution-comitrans", "reviewed-solution-manga-translator-ui"):
            self.assertNotIn(excluded, ids)
        self.assertTrue(all("manga_translation" not in r["tasks"] for r in self.rows))
        self.assertTrue(all("video_generation" not in r["tasks"] for r in self.rows))
        self.assertTrue(all("image_generation" not in r["tasks"] for r in self.rows))
        self.assertTrue(all("audio_generation" not in r["tasks"] for r in self.rows))

    def test_multimodal_services_are_excluded_even_if_text_label_is_present(self):
        mixed = {"modalities": ["text", "image"], "tasks": ["text_generation"]}
        self.assertFalse(is_text_first(mixed))
        mixed["modalities"] = ["text"]
        mixed["tasks"] = ["text_generation", "image_generation"]
        self.assertFalse(is_text_first(mixed))

    def test_capabilities_only_show_text_features(self):
        self.assertNotIn("modality", self.focused["facets"])
        caps = {row["id"] for row in self.focused["facets"]["capability"]}
        self.assertTrue(caps.issubset(TEXT_CAPABILITIES))
        self.assertNotIn("inpainting", caps)
        self.assertNotIn("layered_psd", caps)
        self.assertNotIn("lora", caps)
        self.assertIn("gguf", caps)
        self.assertIn("character_memory", caps)

    def test_external_directory_imports_are_not_destroyed(self):
        self.assertEqual(len(self.full["items"]), 106)
        summary = self.focused["archive_summary"]
        self.assertEqual(summary["full_catalogue_items"], len(self.full["items"]))
        self.assertEqual(summary["text_first_items"], len(self.rows))
        self.assertEqual(summary["media_or_mixed_items_archived"], len(self.full["items"])-len(self.rows))
        self.assertTrue(summary["media_sources_preserved_in_repo"])
        self.assertTrue(any(x["id"] == "reviewed-solution-koharu" for x in self.full["items"]))

    def test_facets_do_not_contain_media_tasks(self):
        allowed = {row["id"] for row in self.focused["facets"]["task"]}
        self.assertTrue(allowed.issubset(TEXT_TASKS))
        self.assertNotIn("manga_translation", allowed)
        self.assertNotIn("audio_generation", allowed)
        self.assertTrue(self.focused["facets"]["task"])

    def test_source_list_only_covers_visible_text_records(self):
        included = {s["name"] for x in self.rows for s in x["sources"] if s.get("readme_sha")}
        self.assertTrue(self.focused["sources"])
        self.assertTrue(all(s["name"] in included for s in self.focused["sources"]))
        for s in self.focused["sources"]:
            count = sum(any(x["name"] == s["name"] for x in r["sources"]) for r in self.rows)
            self.assertEqual(s["count"], count)

    def test_link_health_counts_are_recomputed_for_text(self):
        counts = self.focused["health_summary"]["counts"]
        self.assertEqual(sum(counts.values()), len(self.rows))
        self.assertEqual(self.focused["health_summary"]["migrations"], [])
        self.assertNotIn("comfyanonymous", json.dumps(self.focused["health_summary"]))

    def test_original_catalogue_not_mutated_by_projection(self):
        ids = {x["id"] for x in self.full["items"]}
        self.assertIn("reviewed-solution-comfyui", ids)
        self.assertTrue(any("image" in x["modalities"] for x in self.full["items"]))
        self.assertTrue(all("link_check" in x for x in self.rows))

    def test_no_remote_inference_or_network_calls(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            result = text_catalogue()
        self.assertEqual(result["model_invocations"], 0)
        self.assertEqual(result["network_requests"], 0)


class TextFirstHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.service = StudioService(Path(cls.temp.name) / "workspace")
        cls.server = StudioHTTP(("127.0.0.1", 0), cls.service)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=3)
        cls.temp.cleanup()

    def test_local_text_api_has_strict_scope(self):
        with urlopen(self.base + "/api/catalog/text", timeout=7) as res:
            data = json.load(res)
        self.assertEqual(data["scope"], "text_first")
        self.assertTrue(all(x["modalities"] == ["text"] for x in data["items"]))
        self.assertEqual(data["model_invocations"], 0)

    def test_legacy_research_api_remains_available(self):
        with urlopen(self.base + "/api/catalog", timeout=7) as res:
            data = json.load(res)
        self.assertEqual(len(data["items"]), 106)
        self.assertTrue(any("image" in x["modalities"] for x in data["items"]))

    def test_public_discovery_html_is_text_first(self):
        with urlopen(self.base + "/discover", timeout=7) as res:
            page = res.read().decode("utf-8")
        self.assertIn("从文字创作开始", page)
        self.assertIn("图像、漫画、语音与视频资料暂时归档", page)
        self.assertNotIn("<textarea", page)

    def test_discovery_js_uses_text_endpoint_not_legacy_archive(self):
        with urlopen(self.base + "/chooser.js", timeout=7) as res:
            body = res.read().decode("utf-8")
        self.assertIn('fetch("/api/catalog/text"', body)
        self.assertNotIn('fetch("/api/catalog",{', body)


if __name__ == "__main__":
    unittest.main()
