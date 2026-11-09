"""P5.10: named client/backend/format edges and no fabricated model compatibility."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

from nb_text_catalog import text_catalogue
from nb_text_compat import DATA_PATH, CompatibilityError, load_graph, annotate_connections
from nb_studio import StudioHTTP, StudioService


class TextCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = text_catalogue()
        cls.by_id = {row["id"]: row for row in cls.index["items"]}
        cls.graph = load_graph(item_ids=set(cls.by_id))
        cls.edges = {row["id"]: row for row in cls.graph["edges"]}

    def test_graph_has_precise_documentation_vs_unverified_protocol_candidate(self):
        summary = self.index["compatibility_summary"]
        self.assertEqual(summary["edge_count"], 10)
        self.assertEqual(summary["documented_edges"], 9)
        self.assertEqual(summary["protocol_candidates"], 1)
        self.assertEqual(summary["named_model_backend_compatibility_tests"], 0)
        self.assertEqual(summary["actual_connection_tests"], 0)

    def test_sillytavern_has_two_documented_connection_routes(self):
        st = self.by_id["reviewed-solution-sillytavern"]
        outgoing = [x for x in st["connections"]
                    if x["direction"] == "outgoing" and x["relation"] == "client_backend"]
        self.assertEqual({x["other_id"] for x in outgoing},
                         {"reviewed-solution-ollama", "reviewed-solution-koboldcpp"})
        self.assertTrue(all(x["evidence_status"] == "documented" for x in outgoing))
        kobold = next(x for x in outgoing if x["other_id"].endswith("koboldcpp"))
        self.assertEqual(kobold["api_profile"], "koboldcpp_native")
        self.assertEqual(kobold["endpoint_hint"], "http://127.0.0.1:5001")

    def test_book_translation_backends_have_explicit_documented_paths(self):
        bbm = self.by_id["reviewed-solution-bilingual-book-maker"]
        tolmach = self.by_id["reviewed-solution-book-translator"]
        bbm_doc = [x for x in bbm["connections"] if x["relation"] == "client_backend"]
        self.assertEqual(len(bbm_doc), 1)
        self.assertEqual(bbm_doc[0]["other_id"], "reviewed-solution-ollama")
        self.assertEqual(bbm_doc[0]["api_profile"], "openai_subset")
        self.assertEqual(bbm_doc[0]["endpoint_hint"], "http://127.0.0.1:11434/v1")
        self.assertTrue(any(x["api_profile"] == "ollama_native" for x in tolmach["connections"]))

    def test_shared_openai_schema_is_not_a_verified_integration(self):
        candidate = self.edges["bbm-kcpp-openai-candidate"]
        self.assertEqual(candidate["relation"], "protocol_candidate")
        self.assertEqual(candidate["evidence_status"], "protocol_inferred_not_tested")
        self.assertEqual(candidate["actual_connection_test"], "not_run")
        bbm = self.by_id["reviewed-solution-bilingual-book-maker"]
        paired = next(x for x in bbm["connections"] if x["id"] == candidate["id"])
        self.assertEqual(paired["evidence_status"], "protocol_inferred_not_tested")
        self.assertTrue(paired["verification_plan"])

    def test_gguf_is_a_file_format_not_named_model_compatibility(self):
        for backend in ("reviewed-solution-koboldcpp", "reviewed-solution-ollama"):
            row = self.by_id[backend]
            edges = [e for e in row["connections"] if e["relation"] == "runtime_format"]
            self.assertEqual(len(edges), 1)
            self.assertEqual(edges[0]["other_id"], "format:gguf")
            self.assertEqual(edges[0]["actual_connection_test"], "not_run")
        self.assertNotIn("format:gguf", self.by_id)

    def test_imported_named_models_do_not_inherit_runtime_support(self):
        models = [row for row in self.index["items"]
                  if row["id"].startswith("import-uncensored-llms-")]
        self.assertGreaterEqual(len(models), 20)
        self.assertTrue(all(not row["connections"] for row in models))
        self.assertTrue(all(row["hardware_fit"] == "not_tested" for row in models))

    def test_presence_and_memory_dependency_kept_distinct(self):
        dmm = self.by_id["reviewed-solution-dragon-memories-manager"]
        presence = next(e for e in dmm["connections"]
                        if e["relation"] == "needs_extension_for_isolation")
        self.assertEqual(presence["other_id"], "reviewed-solution-sillytavern-presence")
        self.assertIn("strongly recommended", presence["limitations"])
        self.assertIn("extension_host", dmm["integration_tags"])
        self.assertIn("presence_metadata", dmm["integration_tags"])

    def test_integration_tags_are_only_from_documented_edges(self):
        for row in self.index["items"]:
            documented = {r["api_profile"] for r in row["connections"]
                          if r["evidence_status"] == "documented"
                          and r["relation"] in ("client_backend", "extension_for",
                                                "needs_extension_for_isolation")}
            self.assertEqual(set(row["integration_tags"]), documented)

    def test_public_scope_still_only_text(self):
        self.assertEqual(len(self.index["items"]), 52)
        self.assertTrue(all(row["modalities"] == ["text"] for row in self.index["items"]))
        self.assertTrue(all("image_generation" not in row["tasks"] for row in self.index["items"]))
        self.assertIn("integration", self.index["facets"])
        self.assertTrue(all(option["id"] != "gguf_model_file"
                            for option in self.index["facets"]["integration"]))

    def edit_graph(self, fn):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "compatibility.json"
            payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
            fn(payload)
            file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(CompatibilityError):
                load_graph(file, item_ids=set(self.by_id))

    def test_cannot_mark_protocol_guess_documented(self):
        self.edit_graph(lambda x: next(r for r in x["edges"] if r["relation"] == "protocol_candidate").update(
            evidence_status="documented"))

    def test_cannot_forge_hands_on_test_result(self):
        self.edit_graph(lambda x: x["edges"][0].update(actual_connection_test="pass"))

    def test_unknown_target_fails_closed(self):
        self.edit_graph(lambda x: x["edges"][0].update(to_id="reviewed-solution-does-not-exist"))

    def test_legacy_multimedia_target_fails_closed(self):
        self.edit_graph(lambda x: x["edges"][0].update(to_id="reviewed-solution-koharu"))

    def test_duplicate_edge_ids_are_rejected(self):
        self.edit_graph(lambda x: x["edges"].append(dict(x["edges"][0])))

    def test_source_urls_must_be_public_https(self):
        self.edit_graph(lambda x: x["edges"][0].update(source_urls=["http://localhost/secret"]))

    def test_endpoint_hint_rejects_external_host(self):
        self.edit_graph(lambda x: x["edges"][0].update(endpoint_hint="https://cloud.example.com/v1"))

    def test_graph_and_catalogue_read_without_external_requests(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
            data = text_catalogue()
        self.assertEqual(data["network_requests"], 0)
        self.assertEqual(data["model_invocations"], 0)


class TextCompatibilityHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.service = StudioService(Path(cls.tmp.name) / "work")
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

    def test_catalogue_api_contains_bounded_connections(self):
        with urlopen(self.base + "/api/catalog/text", timeout=8) as res:
            content = json.load(res)
        self.assertEqual(content["compatibility_summary"]["edge_count"], 10)
        st = next(r for r in content["items"] if r["name"] == "SillyTavern")
        self.assertTrue(st["connections"])
        self.assertEqual(content["model_invocations"], 0)

    def test_page_and_js_do_not_request_free_text(self):
        with urlopen(self.base + "/discover", timeout=8) as res:
            page = res.read().decode("utf-8")
        with urlopen(self.base + "/chooser.js", timeout=8) as res:
            script = res.read().decode("utf-8")
        self.assertIn('id="filters"', page)
        self.assertIn("连接方式", page)
        self.assertIn('facet==="integration"', script)
        self.assertIn("compatibility-details", script)
        self.assertNotIn("<textarea", page)
        self.assertNotIn('type="text"', page)


if __name__ == "__main__":
    unittest.main()
