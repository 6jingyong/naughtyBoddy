import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nb_registry as registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'registry'
        shutil.copytree(registry.DEFAULT_ROOT, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seed_registry_consistent(self):
        records, errors = registry.read_registry(self.root)
        self.assertEqual(errors, [])
        self.assertEqual([len(records[k]) for k in registry.KINDS], [3, 5, 2, 2])

    def test_cli_validate(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = registry.main(['--root', str(self.root), 'validate'])
        self.assertEqual(status, 0)
        self.assertTrue(json.loads(out.getvalue())['valid'])

    def test_candidate_matching_not_endorsement(self):
        records, errors = registry.read_registry(self.root)
        self.assertFalse(errors)
        result = registry.match_need(records, 'need-manga-localization')
        manga = next(x for x in result['candidates'] if x['solution_id'] == 'solution-libre-manga-translator')
        self.assertEqual(manga['fit'], 'unknown')
        self.assertEqual(manga['verification'], 'unreviewed')
        self.assertIn('not a quality', manga['caution'])

    def test_unknown_need_is_error(self):
        data, _ = registry.read_registry(self.root)
        with self.assertRaises(registry.RegistryError):
            registry.match_need(data, 'need-nonexistent')

    def test_bad_reference_rejected(self):
        file = self.root / 'gaps' / 'gap-cross-editor-manga.json'
        value = json.loads(file.read_text())
        value['need_id'] = 'need-does-not-exist'
        file.write_text(json.dumps(value))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any('unknown need_id' in e for e in errors))

    def test_false_fit_without_evidence_rejected(self):
        file = self.root / 'assessments' / 'assessment-manga-libre-pending.json'
        value = json.loads(file.read_text())
        value['fit'] = 'meets'
        file.write_text(json.dumps(value))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any('fit verdict needs reviewed evidence' in e for e in errors))

    def test_hands_on_without_real_checks_rejected(self):
        file = self.root / 'assessments' / 'assessment-manga-libre-pending.json'
        value = json.loads(file.read_text())
        value['evidence_status'] = 'hands_on_verified'
        value['fit'] = 'partial'
        value['observations'] = ['an unverified sentence']
        file.write_text(json.dumps(value))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any('needs environment and executed checks' in e for e in errors))

    def test_duplicate_ids_rejected(self):
        file = self.root / 'solutions' / 'solution-ollama.json'
        value = json.loads(file.read_text())
        value['id'] = 'solution-calibre'
        file.write_text(json.dumps(value))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any('duplicate id' in e for e in errors))

    def test_invalid_json_duplicate_keys_rejected(self):
        file = self.root / 'solutions' / 'solution-ollama.json'
        file.write_text('{"id":"solution-ollama","id":"solution-comfyui"}')
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any('duplicate JSON field' in e for e in errors))

    def test_no_network_while_matching(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('network touched')):
            data, errors = registry.read_registry(self.root)
            self.assertFalse(errors)
            self.assertTrue(registry.match_need(data, 'need-private-roleplay')['candidates'])

    def test_real_license_not_guessed(self):
        data, _ = registry.read_registry(self.root)
        self.assertTrue(all(s['license'] is None for s in data['solutions']))

    def test_wrong_schema_rejected(self):
        file = self.root / 'needs' / 'need-private-roleplay.json'
        value = json.loads(file.read_text())
        value['schema_version'] = 2
        file.write_text(json.dumps(value))
        _, errors = registry.read_registry(self.root)
        self.assertTrue(any('schema_version must be 1' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
