import argparse
import io
import json
import unittest
from contextlib import redirect_stdout
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

    def test_openrouter_requires_explicit_key(self):
        self.assertEqual(nb.hints_for("a heretic model"), ["heretic"])


if __name__ == "__main__":
    unittest.main()
