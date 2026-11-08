"""Offline contract tests; no adult book or cloud API required."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr, closing
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

import naughtyboddy as cli
import nb_novel as novel


class NovelTests(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.ctx.cleanup)
        self.root = Path(self.ctx.name)
        self.txt = self.root / "book.txt"
        self.txt.write_text("第1章 Opening\n\nAlice greets Bob.\n\nThey discuss a garden.\n\n第2章 Later\n\nBob thanks Alice.", encoding="utf-8")
        self.project = self.root / "project"

    def init(self, **kwargs):
        return novel.init_project(self.txt, self.project, **kwargs)

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(argv))
        data = json.loads(out.getvalue()) if out.getvalue().strip() else None
        return code, data, err.getvalue()

    def test_txt_chapters_segments_and_source_provenance(self):
        result = self.init()
        self.assertEqual(result["chapters"], 2)
        self.assertEqual(result["segments"], 5)
        self.assertEqual(result["source_sha256"], novel.digest(self.txt.read_bytes()))
        self.assertEqual((self.project / "source.txt").read_text(encoding="utf-8"), self.txt.read_text(encoding="utf-8"))
        self.assertEqual(novel.project_status(self.project)["pending"], 5)

    def test_split_chunks_exact_reconstruction(self):
        source = ("This is a longer sentence about music and stories. " * 80).strip()
        pieces = novel.split_segments(source, 350)
        self.assertTrue(all(0 < len(x) <= 350 for x in pieces))
        self.assertEqual("".join(pieces), source)
        self.assertGreater(len(pieces), 5)

    def test_mock_resume_and_export_demo_epub(self):
        self.init()
        code, first, error = self.call("novel", "translate", "--provider", "mock", "--project", str(self.project), "--max-segments", "2")
        self.assertEqual(code, 0, error)
        self.assertEqual(first["done"], 2)
        self.assertEqual(first["pending"], 3)
        code, final, error = self.call("novel", "translate", "--provider", "mock", "--project", str(self.project))
        self.assertEqual(code, 0, error)
        self.assertEqual(final["done"], 5)
        self.assertEqual(final["simulated"], 5)
        epub = self.root / "out.epub"
        code, _, error = self.call("novel", "export", "--project", str(self.project), "--output", str(epub))
        self.assertEqual(code, 1)
        self.assertIn("Demo segments", error)
        code, result, error = self.call("novel", "export", "--project", str(self.project), "--output", str(epub), "--allow-demo")
        self.assertEqual(code, 0, error)
        self.assertTrue(result["demo"])
        with ZipFile(epub) as z:
            self.assertEqual(z.namelist()[0], "mimetype")
            self.assertEqual(z.getinfo("mimetype").compress_type, 0)
            self.assertIn(b"DEMO", z.read("OEBPS/content.opf"))
        title, chapters = novel.read_epub(epub)
        self.assertIn("DEMO", title)
        self.assertEqual(len(chapters), 2)
        self.assertIn("NOT TRANSLATED", " ".join(chapters[0][1]))
        code, _, _ = self.call("novel", "export", "--project", str(self.project), "--output", str(epub), "--allow-demo")
        self.assertEqual(code, 1)

    def test_incomplete_export_blocked(self):
        self.init()
        with self.assertRaisesRegex(novel.ProviderError, "not translated"):
            novel.export_project(self.project, self.root / "bad.epub")

    def test_resume_after_inference_failure(self):
        self.init()
        calls = []
        def flaky(prompt):
            calls.append(prompt)
            if len(calls) == 2:
                raise RuntimeError("remote error contains a secret")
            return "译文" + str(len(calls))
        first = novel.run_translation(self.project, provider="compatible", model="fake", inference=flaky)
        self.assertEqual(first["done"], 1)
        self.assertEqual(first["pending"], 4)
        self.assertEqual(first["errors"][0]["error_type"], "RuntimeError")
        self.assertNotIn("secret", json.dumps(first))
        second = novel.run_translation(self.project, provider="compatible", model="fake", inference=lambda _: "译文完成")
        self.assertEqual(second["done"], 5)
        self.assertEqual(second["pending"], 0)
        with closing(sqlite3.connect(self.project / "work.sqlite3")) as db:
            first_target = db.execute("SELECT target FROM segments ORDER BY chapter_no, paragraph_no LIMIT 1").fetchone()[0]
        self.assertEqual(first_target, "译文1")
        out = self.root / "realish.txt"
        novel.export_project(self.project, out)
        self.assertIn("译文1", out.read_text(encoding="utf-8"))

    def test_remote_translation_is_opt_in(self):
        self.init()
        with patch.object(cli, "infer_text") as mock:
            code, data, err = self.call("novel", "translate", "--provider", "openrouter", "--model", "x/y", "--project", str(self.project))
        self.assertEqual(code, 1)
        mock.assert_not_called()
        self.assertIn("accept-remote", err)
        self.assertEqual(novel.project_status(self.project)["done"], 0)

    def test_local_endpoint_requires_no_cloud_opt_in(self):
        self.init()
        with patch.object(cli, "infer_text", return_value="你好") as mock:
            code, data, err = self.call("novel", "translate", "--provider", "compatible", "--model", "test", "--base-url", "http://127.0.0.1:8080/v1", "--project", str(self.project), "--max-segments", "1")
        self.assertEqual(code, 0, err)
        mock.assert_called_once()
        self.assertEqual(data["pending"], 4)

    def test_glossary_flags_need_manual_review(self):
        glossary_path = self.root / "glossary.json"
        glossary_path.write_text('{"Alice": "爱丽丝", "Bob": "鲍勃"}', encoding="utf-8")
        self.init(glossary_path=glossary_path)
        novel.run_translation(self.project, provider="compatible", model="test", inference=lambda _: "译文")
        audit = novel.audit_project(self.project)
        self.assertGreater(audit["flagged_total"], 0)
        self.assertTrue(any("missing_glossary:Alice" in r["flags"] for r in audit["flagged"]))
        self.assertEqual(audit["pending"], 0)

    def test_preexisting_project_refused(self):
        self.init()
        with self.assertRaisesRegex(novel.ProviderError, "already exists"):
            self.init()

    def test_invalid_glossary_refused_without_project(self):
        path = self.root / "glossary.json"
        path.write_text('["bad"]', encoding="utf-8")
        with self.assertRaisesRegex(novel.ProviderError, "Glossary"):
            self.init(glossary_path=path)
        self.assertFalse(self.project.exists())

    def test_import_existing_exported_epub(self):
        self.init()
        novel.run_translation(self.project, provider="mock", model="demo")
        ebook = self.root / "demo.epub"
        novel.export_project(self.project, ebook, allow_demo=True)
        new = self.root / "epub-project"
        info = novel.init_project(ebook, new)
        self.assertEqual(info["chapters"], 2)
        self.assertGreater(info["segments"], 0)

    def test_epub_rejects_traversal_zip_member(self):
        bad = self.root / "bad.epub"
        with ZipFile(bad, "w", ZIP_DEFLATED) as z:
            z.writestr("../something", "malicious")
            z.writestr("META-INF/container.xml", "<container/>")
        with self.assertRaisesRegex(novel.ProviderError, "Unsafe"):
            novel.read_epub(bad)

    def test_epub_rejects_external_spine_content(self):
        bad = self.root / "outside.epub"
        with ZipFile(bad, "w") as z:
            z.writestr("META-INF/container.xml", '<container><rootfile full-path="OEBPS/content.opf"/></container>')
            z.writestr("OEBPS/content.opf", '<package><manifest><item id="a" media-type="application/xhtml+xml" href="https://bad.example/chapter.xhtml"/></manifest><spine><itemref idref="a"/></spine></package>')
        with self.assertRaisesRegex(novel.ProviderError, "external"):
            novel.read_epub(bad)

    def test_source_text_does_not_execute_as_script(self):
        self.txt.write_text("Chapter 1\n\n<script>alert('x')</script> Literal text about a computer.", encoding="utf-8")
        self.init()
        novel.run_translation(self.project, provider="compatible", model="fake", inference=lambda _: '<script>alert("x")</script>')
        ebook = self.root / "escaped.epub"
        novel.export_project(self.project, ebook)
        with ZipFile(ebook) as z:
            content = z.read("OEBPS/chapter0001.xhtml").decode("utf-8")
        self.assertIn("&lt;script&gt;", content)
        self.assertNotIn("<script>", content)

    def test_no_accidental_model_calls_on_init_status_and_export(self):
        with patch.object(cli, "infer_text") as mock:
            self.init()
            code, status, _ = self.call("novel", "status", "--project", str(self.project))
            self.assertEqual(code, 0)
            self.assertEqual(status["pending"], 5)
            self.call("novel", "audit", "--project", str(self.project))
            self.call("novel", "export", "--project", str(self.project), "--output", str(self.root / "x.epub"))
            mock.assert_not_called()

    def test_lock_prevents_concurrent_translation(self):
        self.init()
        (self.project / ".translate.lock").write_text("held", encoding="utf-8")
        with self.assertRaisesRegex(novel.ProviderError, "already running"):
            novel.run_translation(self.project, provider="mock", model="demo")


if __name__ == "__main__":
    unittest.main()
