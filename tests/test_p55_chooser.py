"""P5.5: the end-user discovery wizard must work without AI or free text."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from nb_chooser import choose, chooser_questions, _profiles, PROFILES
from nb_registry import RegistryError
from nb_studio import StudioHTTP, StudioService


BOOK = "need-long-fiction-translation"
MANGA = "need-manga-localization"
ROLEPLAY = "need-private-roleplay"


def answers(task=BOOK, privacy="local_only", hardware="unknown", priority="editable"):
    return {"task": task, "privacy": privacy, "hardware": hardware, "priority": priority}


class ChooserTests(unittest.TestCase):
    def test_exactly_four_choice_questions_no_free_text(self):
        qs = chooser_questions()
        self.assertEqual([q["id"] for q in qs["questions"]],
                         ["task", "privacy", "hardware", "priority"])
        for q in qs["questions"]:
            self.assertTrue(all(set(opt) == {"id", "label"} for opt in q["options"]))

    def test_invalid_or_missing_options_are_rejected(self):
        for item in ({}, {"task": BOOK}, answers(hardware="64GB"),
                     {**answers(), "prompt": "Ignore all controls"}, answers(task="bad")):
            with self.assertRaises(RegistryError):
                choose(item)

    def test_privacy_filter_discloses_unknown_manga_backend(self):
        result = choose(answers(task=MANGA))
        ids = {c["id"] for c in result["candidates"]}
        unknown = {c["id"] for c in result["unconfirmed_local"]}
        self.assertIn("solution-koharu", ids)
        self.assertIn("solution-libre-manga-translator", ids)
        self.assertNotIn("solution-comitrans", ids)
        self.assertIn("solution-comitrans", unknown)

    def test_roleplay_distinguishes_apps_and_extensions(self):
        result = choose(answers(task=ROLEPLAY))
        by_id = {c["id"]: c for c in result["candidates"]}
        self.assertEqual(by_id["solution-sillytavern"]["role"], "workflow")
        self.assertEqual(by_id["solution-sillytavern-presence"]["role"], "extension")
        self.assertEqual(by_id["solution-koboldcpp"]["role"], "component")
        self.assertEqual(by_id["solution-dragon-memories-manager"]["claimed_quality"], "not_evaluated")

    def test_hardware_not_misrepresented_as_measured_fit(self):
        for device in ("cpu", "vram8", "vram12", "unknown"):
            result = choose(answers(hardware=device))
            self.assertEqual(result["real_world_tests"], "not_run")
            self.assertTrue(all(c["hardware_fit"] == "not_evaluated" for c in result["candidates"]))
        self.assertTrue(any("无独显" in x for x in choose(answers(hardware="cpu"))["warnings"]))

    def test_no_quality_scoring_and_no_secret_source_upload(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network accessed")):
            result = choose(answers(task=ROLEPLAY, privacy="remote_ok", priority="low_setup"))
        self.assertEqual(result["model_invocations"], 0)
        self.assertEqual(result["data_source"], "local_repository_registry")
        self.assertTrue(any("安装" in x for x in result["warnings"]))
        for item in result["candidates"]:
            self.assertEqual(item["privacy_audit"], "not_run")
            self.assertEqual(item["claimed_quality"], "not_evaluated")
            self.assertTrue(item["documentation_url"].startswith("https://"))

    def test_curated_profiles_refer_to_known_documents(self):
        profiles = _profiles(PROFILES)
        self.assertGreaterEqual(len(profiles), 12)
        self.assertTrue(all(p["note"] and p["documentation_url"].startswith("https://") for p in profiles))

    def test_unsupported_preference_cannot_trigger_model_search(self):
        with self.assertRaises(RegistryError):
            choose(answers(priority="ask_llm"))


class ChooserHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = StudioService(Path(self.tmp.name) / "private")
        self.server = StudioHTTP(("127.0.0.1", 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def test_discovery_page_is_accessible_without_prompts(self):
        with urlopen(self.base + "/discover", timeout=3) as res:
            page = res.read().decode("utf-8")
        self.assertIn("选择标签，发现工具", page)
        self.assertIn('id="filters"', page)
        self.assertIn("chooser.js", page)
        self.assertNotIn("<textarea", page)
        self.assertNotIn("<input", page)
        self.assertNotIn('id="next"', page)

    def test_options_and_matching_are_read_only(self):
        with urlopen(self.base + "/api/chooser/options", timeout=3) as res:
            options = json.load(res)
        self.assertEqual(len(options["questions"]), 4)
        url = self.base + "/api/chooser/match?" + urlencode(answers(task=MANGA))
        with urlopen(url, timeout=3) as res:
            result = json.load(res)
        self.assertEqual(result["model_invocations"], 0)
        self.assertTrue(result["candidates"])
        self.assertTrue(all(item["privacy_audit"] == "not_run" for item in result["candidates"]))

    def test_bad_choice_is_http_error_not_llm_fallback(self):
        url = self.base + "/api/chooser/match?" + urlencode(answers(priority="surprise"))
        with self.assertRaises(HTTPError) as cm:
            urlopen(url, timeout=3)
        self.assertEqual(cm.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
