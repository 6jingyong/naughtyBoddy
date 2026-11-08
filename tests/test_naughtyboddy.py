import argparse
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

import naughtyboddy as nb


class DiscoveryTests(unittest.TestCase):
    @patch.object(nb, "request_json")
    def test_ollama_local_inventory_is_not_a_verdict(self, mock_request):
        mock_request.return_value = {"models": [{"name": "demo-abliterated:q4", "size": 999,
                                                 "details": {"parameter_size": "8B", "quantization_level": "Q4"}}]}
        models = nb.discover_ollama()
        self.assertEqual(models[0]["id"], "demo-abliterated:q4")
        self.assertEqual(models[0]["adult_compatibility"], "untested")
        self.assertEqual(models[0]["low_refusal_hints"], ["abliterated"])
        self.assertTrue(models[0]["local"])

    @patch.object(nb, "request_json")
    def test_openrouter_metadata_not_a_verdict(self, mock_request):
        mock_request.return_value = {"data": [{"id": "org/uncensored", "pricing": {"prompt": "0.0001", "completion": "0.0002"},
                                                "architecture": {"input_modalities": ["text"]}}]}
        model = nb.discover_openrouter()[0]
        self.assertEqual(model["low_refusal_hints"], ["uncensored"])
        self.assertEqual(model["adult_compatibility"], "untested")
        self.assertEqual(model["pricing_usd_per_token"]["prompt"], "0.0001")

    @patch.object(nb, "request_json", side_effect=nb.ProviderError("offline"))
    def test_discovery_returns_errors_without_crashing(self, _mock_request):
        args = argparse.Namespace(source="ollama", ollama_url=nb.OLLAMA, query="", limit=5)
        out = io.StringIO()
        with redirect_stdout(out):
            code = nb.discover(args)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["errors"]["ollama"], "offline")

    @patch.object(nb, "request_json")
    def test_openrouter_requires_explicit_key(self, mock_request):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.txt"
            path.write_text("Hello", encoding="utf-8")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
                with redirect_stderr(io.StringIO()):
                    status = nb.main(["probe", "--provider", "openrouter", "--model", "demo", "--prompt-file", str(path)])
        self.assertEqual(status, 1)
        mock_request.assert_not_called()

    @patch.object(nb, "request_json", return_value={"message": {"content": "你好"}})
    def test_ollama_probe_is_explicit_and_unrated(self, mock_request):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prompt.txt"
            path.write_text("Test sentence", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                status = nb.main(["probe", "--provider", "ollama", "--model", "demo", "--prompt-file", str(path)])
        self.assertEqual(status, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data["response"], "你好")
        self.assertEqual(data["adult_compatibility"], "needs_human_review")
        self.assertEqual(mock_request.call_args.kwargs["payload"]["messages"][0]["content"], "Test sentence")


if __name__ == "__main__":
    unittest.main()
