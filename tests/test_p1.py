import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch, MagicMock

import naughtyboddy as nb
import nb_hardware as hw
import nb_local as loc
import nb_evaluation as ev


class HardwareTests(unittest.TestCase):
    @patch.object(hw.subprocess, "check_output", return_value="RTX Test, 12288, 9020\nBad, unknown, 1\n")
    def test_nvidia_parse(self, _):
        self.assertEqual(hw.nvidia_gpus(), [{"name": "RTX Test", "vram_total_mib": 12288,
                                              "vram_free_mib": 9020, "backend": "nvidia-smi"}])

    def test_fit_does_not_claim_guarantee(self):
        device = {"gpus": [{"vram_free_mib": 12000}], "system_ram_bytes": 32 * hw.GIB}
        fit = hw.gguf_fit(6 * hw.GIB, device)
        self.assertEqual(fit["assessment"], "gpu_plausible")
        self.assertIn("rough estimate", fit["warning"])
        self.assertEqual(hw.gguf_fit(40 * hw.GIB, device)["assessment"], "unknown_or_insufficient")

    @patch.object(hw, "hardware_inventory", return_value={"system_ram_bytes": 123, "gpus": []})
    def test_hardware_cli(self, _):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = nb.main(["hardware"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue())["system_ram_bytes"], 123)


class LocalModelTests(unittest.TestCase):
    def test_repo_and_path_validation(self):
        self.assertTrue(loc.valid_gguf_name("Q4/model.gguf"))
        for filename in ["../../escape.gguf", "../escape.gguf", "C:\\escape.gguf", "../a.gguf", "demo.bin", "/root.gguf"]:
            self.assertFalse(loc.valid_gguf_name(filename), filename)
        self.assertTrue(loc.is_loopback("http://127.0.0.1:11434"))
        self.assertFalse(loc.is_loopback("https://example.com:11434"))
        self.assertFalse(loc.is_loopback("http://user:pass@127.0.0.1:11434"))

    @patch.object(loc, "request_json")
    def test_catalog_provenance_and_files(self, mocked):
        mocked.return_value = {"id": "owner/repo", "sha": "f"*40, "gated": False,
                               "cardData": {"license": "mit"},
                               "siblings": [{"rfilename": "model-q4.gguf", "size": 123},
                                            {"rfilename": "model.safetensors", "size": 456}]}
        result = loc.gguf_catalog("owner/repo")
        self.assertEqual(result["files"], [{"filename": "model-q4.gguf", "size_bytes": 123}])
        self.assertEqual(result["license"], "mit")
        self.assertEqual(result["revision"], "f"*40)

    @patch.object(loc, "request_json")
    def test_ollama_install_requires_local_endpoint(self, mocked):
        with self.assertRaises(nb.ProviderError):
            loc.ollama_pull("model", "https://public.example")
        mocked.assert_not_called()

    @patch.object(loc, "request_json", return_value={"status": "success"})
    def test_ollama_pull(self, mocked):
        result = loc.ollama_pull("demo")
        self.assertEqual(result["status"], "installed")
        self.assertEqual(mocked.call_args.kwargs["payload"], {"model": "demo", "stream": False})

    @patch.object(loc, "ollama_pull")
    def test_pull_opt_in(self, mocked):
        with redirect_stderr(io.StringIO()):
            rc = nb.main(["local", "ollama-pull", "--model", "demo"])
        self.assertEqual(rc, 1)
        mocked.assert_not_called()

    @patch.object(loc, "gguf_catalog", return_value={"repo": "owner/repo", "revision": "a"*40,
                                                      "gated": False, "private": False,
                                                      "files": [{"filename": "q4.gguf"}]})
    @patch.object(loc, "urlopen")
    def test_small_gguf_download(self, open_mock, _catalog):
        class Stub:
            status = 200
            headers = {"Content-Length": "5"}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, size):
                if not hasattr(self, "read_once"):
                    self.read_once = True
                    return b"small"
                return b""
        open_mock.return_value = Stub()
        with tempfile.TemporaryDirectory() as td:
            result = loc.download_gguf("owner/repo", "q4.gguf", Path(td), max_bytes=100)
            self.assertEqual(Path(result["path"]).read_bytes(), b"small")
            self.assertNotIn(".part", result["path"])
        self.assertIn("/resolve/", open_mock.call_args.args[0].full_url)

    @patch.object(loc, "gguf_catalog", return_value={"repo": "owner/repo", "revision": "a"*40,
                                                      "gated": True, "private": False,
                                                      "files": [{"filename": "q4.gguf"}]})
    @patch.object(loc, "urlopen")
    def test_gated_download_blocked(self, open_mock, _catalog):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(nb.ProviderError):
                loc.download_gguf("owner/repo", "q4.gguf", Path(td))
        open_mock.assert_not_called()

    @patch.object(loc.subprocess, "call", return_value=0)
    def test_llama_serve_localhost_and_no_shell(self, mock_call):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "model.gguf"
            f.write_bytes(b"gguf")
            rc = loc.serve_llama_cpp(f, port=8081)
        self.assertEqual(rc, 0)
        args = mock_call.call_args.args[0]
        self.assertEqual(args[args.index("--host") + 1], "127.0.0.1")
        self.assertNotIn("--shell", args)


class EvaluationTests(unittest.TestCase):
    def test_case_validation(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "eval.json"
            file.write_text(json.dumps({"cases": [{"id": "a", "prompt": "Hello"},
                                                   {"id": "a", "prompt": "Again"}]}))
            with self.assertRaises(ValueError):
                ev.read_cases(file)
            file.write_text(json.dumps({"cases": [{"id": "a", "prompt": "Hello", "expected_terms": ["one"]}]}))
            self.assertEqual(ev.read_cases(file)[0]["expected_terms"], ["one"])

    def test_evaluation_does_not_infer_success_from_non_refusal(self):
        cases = [{"id": "a", "prompt": "Hello", "expected_terms": ["yes"]}]
        result = ev.run_evaluation(cases, lambda _: "no", provider="ollama", model="demo")
        self.assertEqual(result["summary"]["suspected_refusals"], 0)
        self.assertEqual(result["summary"]["term_check_passes"], 0)
        self.assertNotIn("response", result["cases"][0])
        self.assertTrue(result["cases"][0]["manual_review_needed"])

    def test_report_is_private_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reports" / "result.json"
            ev.write_private_report(path, {"ok": True})
            self.assertTrue(path.exists())
            self.assertTrue(path.stat().st_mode & 0o600)
            with self.assertRaises(FileExistsError):
                ev.write_private_report(path, {"ok": False})

    @patch.object(nb, "infer_text")
    def test_cloud_eval_requires_explicit_consent(self, mocked):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "eval.json"
            path.write_text(json.dumps({"cases": [{"id": "a", "prompt": "Hello"}]}))
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "example"}):
                with redirect_stderr(io.StringIO()):
                    rc = nb.main(["evaluate", "--provider", "openrouter", "--model", "test",
                                  "--cases", str(path)])
        self.assertEqual(rc, 1)
        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
