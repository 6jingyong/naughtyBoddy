"""P5.2: evidence records are searchable, sourced and never mistaken for live tests."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nb_registry as registry


class FrictionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "registry"
        shutil.copytree(registry.DEFAULT_ROOT, self.root)

    def tearDown(self):
        self.temp.cleanup()

    def rewrite(self, name, change):
        path = self.root / name
        record = json.loads(path.read_text(encoding="utf-8"))
        change(record)
        path.write_text(json.dumps(record), encoding="utf-8")

    def test_seed_is_sourced_and_unverified(self):
        data, errors = registry.read_registry(self.root)
        self.assertEqual(errors, [])
        self.assertEqual(len(data["frictions"]), 10)
        self.assertGreaterEqual(len(data["solutions"]), 15)
        self.assertTrue(all(f["sources"] for f in data["frictions"]))
        self.assertTrue(all(f["evidence_status"] != "hands_on_verified" for f in data["frictions"]))
        self.assertTrue(all(f["status"] != "reproduced_locally" for f in data["frictions"]))

    def test_match_surfaces_existing_mitigations_not_a_ranking(self):
        data, errors = registry.read_registry(self.root)
        self.assertEqual(errors, [])
        result = registry.match_need(data, "need-private-roleplay")
        self.assertEqual(len(result["frictions"]), 3)
        presence = next(c for c in result["candidates"] if c["solution_id"] == "solution-sillytavern-presence")
        self.assertTrue(presence["related_friction_ids"])
        self.assertEqual(presence["fit"], "unknown")
        self.assertIn("not a quality", presence["caution"])

    def test_cli_can_filter_friction_by_need(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = registry.main(["--root", str(self.root), "frictions", "--need", "need-manga-localization"])
        self.assertEqual(code, 0)
        rows = json.loads(out.getvalue())
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(x["need_id"] == "need-manga-localization" for x in rows))

    def test_cli_unknown_need_reports_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(registry.main(["--root", str(self.root), "frictions", "--need", "does-not-exist"]), 2)

    def test_unknown_solution_and_gap_rejected(self):
        def corrupt(v):
            v["solution_ids"].append("solution-not-here")
            v["gap_ids"].append("gap-not-here")
        self.rewrite("frictions/friction-manga-segment-shift.json", corrupt)
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any("unknown solution_id" in e for e in errors))
        self.assertTrue(any("unknown gap_id" in e for e in errors))

    def test_issue_cannot_claim_hands_on_verification(self):
        self.rewrite("frictions/friction-manga-segment-shift.json",
                     lambda v: v.update(evidence_status="hands_on_verified"))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any("not hands-on verification" in e for e in errors))

    def test_documented_mitigation_must_have_sources(self):
        def corrupt(v):
            v["existing_mitigation"]["sources"] = []
        self.rewrite("frictions/friction-fiction-default-html-tags.json", corrupt)
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any("documented mitigation requires steps and sources" in e for e in errors))

    def test_every_friction_has_public_primary_source(self):
        self.rewrite("frictions/friction-fiction-default-html-tags.json",
                     lambda v: v.update(sources=["file:///private/book.epub"]))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any("friction requires HTTPS evidence URLs" in e for e in errors))

    def test_isolated_local_search_never_fetches_sources(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network call")):
            data, errors = registry.read_registry(self.root)
            self.assertEqual(errors, [])
            rows = registry.friction_for_need(data, "need-long-fiction-translation")
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
