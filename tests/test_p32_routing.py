"""Offline P3.2 tests: no network model inference, no GPU or cloud credentials."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from nb_common import ProviderError
from nb_routing import ModelProfileStore, route_models, normalize_review
from nb_studio import StudioHTTP, StudioService


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = ModelProfileStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_review_requires_confirmation_and_clean_fields(self):
        p = {"provider": "ollama", "model": "sample:q4", "task": "novel_translation",
             "adult_compatibility": "compatible", "task_quality": "good", "note": "I checked the sample."}
        with self.assertRaises(ProviderError): self.store.upsert(p)
        with self.assertRaises(ProviderError): self.store.upsert({**p, "confirm_review": True, "adult_compatibility": "perfect"})
        with self.assertRaises(ProviderError): self.store.upsert({**p, "confirm_review": True, "note": "x" * 1201})
        assert self.store.list() == []
        saved = self.store.upsert({**p, "confirm_review": True})
        self.assertEqual(saved["evidence_type"], "user_review")
        self.assertEqual(self.store.list()[0]["task_quality"], "good")
        if os.name != "nt": self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_upsert_replaces_task_only_and_not_other_reviews(self):
        base = {"provider": "ollama", "model": "m:q4", "confirm_review": True}
        self.store.upsert({**base, "task": "novel_translation", "task_quality": "good"})
        self.store.upsert({**base, "task": "roleplay", "task_quality": "mixed"})
        self.store.upsert({**base, "task": "novel_translation", "task_quality": "poor"})
        self.assertEqual(len(self.store.list()), 2)
        self.assertEqual(next(x for x in self.store.list() if x["task"] == "novel_translation")["task_quality"], "poor")

    def test_no_name_based_promotion_no_unverified_scores(self):
        candidates = [
            {"provider": "ollama", "model": "UNCENSORED-8B", "local": True, "available": True,
             "hints": ["uncensored"]},
            {"provider": "ollama", "model": "ordinary-model", "local": True, "available": True},
        ]
        x = route_models(candidates, [], [], task="novel_translation")
        self.assertEqual({c["adult_compatibility"] for c in x["candidates"]}, {"unknown"})
        self.assertTrue(all(c["evidence_type"] == "none" for c in x["candidates"]))
        self.assertIn("not a validated", x["note"])

    def test_reviewed_relevance_over_keyword_and_cloud_no_automatic_consent(self):
        candidates = [
            {"provider": "ollama", "model": "uncensored-8b", "local": True, "available": True, "hints": ["uncensored"]},
            {"provider": "openrouter", "model": "vendor/novel", "local": False, "available": True, "modalities": ["text"]},
        ]
        reviewed = [normalize_review({"provider": "openrouter", "model": "vendor/novel", "task": "novel_translation",
                                      "adult_compatibility": "compatible", "task_quality": "good", "confirm_review": True})]
        a = route_models(candidates, reviewed, [], task="novel_translation", allow_remote=False)
        self.assertEqual(len(a["candidates"]), 1)
        b = route_models(candidates, reviewed, [], task="novel_translation", allow_remote=True)
        self.assertEqual(b["recommendation"]["provider"], "openrouter")
        self.assertTrue(b["recommendation"]["remote_consent_required"])
        self.assertEqual(b["status"], "suggestions_only_no_auto_execution")

    def test_incompatible_excluded_and_task_specific(self):
        c = [{"provider": "ollama", "model": "test:q4", "local": True, "available": True}]
        reviewed = [normalize_review({"provider": "ollama", "model": "test:q4", "task": "novel_translation",
                                      "adult_compatibility": "incompatible", "confirm_review": True})]
        a = route_models(c, reviewed, [], task="novel_translation")
        self.assertIsNone(a["recommendation"])
        b = route_models(c, reviewed, [], task="roleplay")
        self.assertEqual(len(b["candidates"]), 1)
        self.assertEqual(b["recommendation"]["adult_compatibility"], "unknown")

    def test_vision_modality_not_assumed(self):
        candidates = [
            {"provider": "openrouter", "model": "x/text", "available": True, "local": False, "modalities": ["text"]},
            {"provider": "openrouter", "model": "x/vision", "available": True, "local": False, "modalities": ["text", "image"]}
        ]
        result = route_models(candidates, [], [], task="comic_translation", allow_remote=True)
        self.assertEqual([x["model"] for x in result["candidates"]], ["x/vision"])

    def test_profile_symlink_refused(self):
        real = self.root / "target.json"; real.write_text('{"profiles": []}')
        self.store.path.parent.mkdir(parents=True)
        try: self.store.path.symlink_to(real)
        except OSError: self.skipTest("Symlink not supported")
        with self.assertRaises(ProviderError): self.store.list()


class RoutingHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = StudioService(Path(self.temp.name) / "studio")
        self.server = StudioHTTP(("127.0.0.1", 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True);self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.token = self.get("/api/bootstrap")["csrf_token"]

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)
        self.service.models.stop();self.temp.cleanup()

    def get(self, p):
        with urlopen(self.base + p, timeout=3) as r:return json.loads(r.read())

    def post(self,p,data,token=None):
        req=Request(self.base+p, data=json.dumps(data).encode(), method="POST",
                    headers={"Content-Type":"application/json", "X-NB-Token": token or self.token})
        with urlopen(req, timeout=3) as r:return json.loads(r.read())

    def test_route_and_private_profile_api(self):
        with patch('naughtyboddy.discover_ollama', return_value=[{"id":"demo:q4","low_refusal_hints":["abliterated"]}]),\
             patch.object(self.service.models, 'reports', return_value=[]):
            self.assertEqual(self.get('/api/routing/suggest?task=novel_translation')["recommendation"]["adult_compatibility"], "unknown")
            review = self.post('/api/routing/profiles', {"provider":"ollama", "model":"demo:q4",
                "task":"novel_translation", "adult_compatibility":"compatible", "task_quality":"good",
                "note":"Reviewed offline", "confirm_review":True})
            self.assertEqual(review["evidence_type"], "user_review")
            self.assertEqual(self.get('/api/routing/suggest?task=novel_translation')["recommendation"]["task_quality"], "good")
            self.assertEqual(len(self.get('/api/routing/profiles')["profiles"]), 1)
        self.assertIn("routing-task", urlopen(self.base+'/').read().decode())

    def test_review_rejects_bad_csrf(self):
        with self.assertRaises(HTTPError) as e:
            self.post('/api/routing/profiles', {"task": "novel_translation"}, token="bad-token")
        self.assertEqual(e.exception.code, 403)


if __name__ == "__main__": unittest.main()
