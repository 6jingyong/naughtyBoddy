"""P5.4 contract tests: local, entirely synthetic, no project-specific runtime."""
import copy
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nb_comic_adapter as a
from nb_evalkit import read_json

ROOT = Path(__file__).resolve().parents[1] / 'benchmarks'
FIX = ROOT / 'p54'
CASE = ROOT / 'p53' / 'comic_case.json'


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.project = a.read_input(FIX / 'upstream-project-good.json')
        self.mapping = a.read_input(FIX / 'region-id-map.json')

    def convert(self, data=None, mapping=None):
        return a.from_manga_translator_ui(data or self.project, 'synthetic01',
                                         self.mapping if mapping is None else mapping)

    def test_documented_upstream_shape_and_mapping_pass_synthetic(self):
        contract = self.convert()
        self.assertEqual(contract['id_stability'], 'mapped_source_guard')
        self.assertEqual(contract['regions'][0]['bbox'], [0.016667, 0.025, 0.15, 0.075])
        self.assertTrue(a.audit(read_json(CASE), contract)['passed'])

    def test_deliberate_shift_rejected(self):
        bad = a.read_input(FIX / 'upstream-project-bad.json')
        result = a.audit(read_json(CASE), self.convert(data=bad))
        self.assertFalse(result['passed'])
        self.assertIn('shifted_target_token', [e['code'] for e in result['errors']])

    def test_positional_ids_cannot_pass_stable_id_audit(self):
        provisional = a.from_manga_translator_ui(self.project, 'synthetic01', None)
        self.assertEqual(provisional['id_stability'], 'positional_unstable')
        with self.assertRaisesRegex(a.AdapterError, 'stable IDs'):
            a.audit(read_json(CASE), provisional)
        with self.assertRaisesRegex(a.AdapterError, 'stable IDs'):
            a.audit(read_json(CASE), a.from_native(provisional))

    def test_upstream_document_is_read_only(self):
        before = json.dumps(self.project, sort_keys=True)
        contract = self.convert()
        self.assertEqual(json.dumps(self.project, sort_keys=True), before)
        self.assertNotIn('mask_raw', json.dumps(contract))
        self.assertNotIn('/synthetic/pages', json.dumps(contract))

    def test_source_edit_invalidates_mapping(self):
        data = copy.deepcopy(self.project)
        next(iter(data.values()))['regions'][2]['text'] = 'changed OCR'
        with self.assertRaisesRegex(a.AdapterError, 'OCR source mismatch'):
            self.convert(data=data)

    def test_reordered_regions_cannot_silently_pass(self):
        data = copy.deepcopy(self.project)
        rows = next(iter(data.values()))['regions']
        rows[1], rows[2] = rows[2], rows[1]
        with self.assertRaisesRegex(a.AdapterError, 'OCR source mismatch'):
            self.convert(data=data)

    def test_bbox_anchor_mismatch_detected(self):
        mapping = copy.deepcopy(self.mapping)
        mapping['regions'][0]['bbox'] = [0.1, 0.1, 0.2, 0.2]
        with self.assertRaisesRegex(a.AdapterError, 'Bounding box mismatch'):
            self.convert(mapping=mapping)

    def test_duplicate_region_mapping_rejected(self):
        mapping = copy.deepcopy(self.mapping)
        mapping['regions'][1]['index'] = 0
        with self.assertRaisesRegex(a.AdapterError, 'Duplicate or invalid region map index'):
            self.convert(mapping=mapping)

    def test_repeated_text_requires_bbox_guard(self):
        data = copy.deepcopy(self.project)
        rows = next(iter(data.values()))['regions']
        rows[1]['text'] = rows[0]['text']
        mapping = copy.deepcopy(self.mapping)
        mapping['regions'][1]['source'] = rows[0]['text']
        with self.assertRaisesRegex(a.AdapterError, 'Repeated source needs a bbox'):
            self.convert(data=data, mapping=mapping)

    def test_out_of_bounds_coordinates_rejected(self):
        data = copy.deepcopy(self.project)
        next(iter(data.values()))['regions'][0]['lines'][0][2][0] = 9000
        with self.assertRaisesRegex(a.AdapterError, 'outside page'):
            self.convert(data=data)

    def test_nonfinite_geometry_rejected(self):
        data = copy.deepcopy(self.project)
        next(iter(data.values()))['regions'][0]['lines'][0][2][0] = float('nan')
        with self.assertRaisesRegex(a.AdapterError, 'Bad OCR point'):
            self.convert(data=data)

    def test_ambiguous_multiple_image_input_rejected(self):
        data = copy.deepcopy(self.project)
        data['/other/sensitive/page.png'] = copy.deepcopy(next(iter(data.values())))
        with self.assertRaisesRegex(a.AdapterError, 'exactly one image'):
            self.convert(data=data)

    def test_native_contract_roundtrip(self):
        contract = self.convert()
        self.assertEqual(a.from_native(contract)['regions'], contract['regions'])
        self.assertEqual(a.from_native(contract)['id_stability'], 'mapped_source_guard')

    def test_native_duplicate_ids_rejected(self):
        contract = self.convert()
        contract['regions'][1]['id'] = 'b01'
        with self.assertRaisesRegex(a.AdapterError, 'duplicate'):
            a.from_native(contract)

    def test_json_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bad.json'
            path.write_text('{"x": 1, "x":2}', encoding='utf8')
            with self.assertRaisesRegex(a.AdapterError, 'Duplicate JSON'):
                a.read_input(path)

    def test_cli_conversion_no_content_to_stdout(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = a.main(['import', '--format', 'manga-translator-ui',
                           '--input', str(FIX/'upstream-project-good.json'),
                           '--mapping', str(FIX/'region-id-map.json')])
        self.assertEqual(code, 0)
        self.assertNotIn('SRC_B01', out.getvalue())
        self.assertNotIn('/synthetic/pages', out.getvalue())

    def test_cli_import_audit_output_private_file(self):
        with tempfile.TemporaryDirectory() as d:
            outpath = Path(d) / 'result.json'
            with contextlib.redirect_stdout(io.StringIO()):
                code = a.main(['import', '--format', 'manga-translator-ui',
                               '--input', str(FIX/'upstream-project-good.json'),
                               '--mapping', str(FIX/'region-id-map.json'),
                               '--output', str(outpath), '--audit-case', str(CASE)])
            self.assertEqual(code, 0)
            data = json.loads(outpath.read_text(encoding='utf8'))
            self.assertEqual(data['regions'][5]['id'], 'b06')
            self.assertTrue(a.audit(read_json(CASE), data)['passed'])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(a.main(['import', '--format', 'manga-translator-ui',
                                         '--input', str(FIX/'upstream-project-good.json'),
                                         '--mapping', str(FIX/'region-id-map.json'),
                                         '--output', str(outpath)]), 2)

    def test_malicious_unrelated_fields_not_carried(self):
        data = copy.deepcopy(self.project)
        next(iter(data.values()))['API_SECRET'] = 'SHOULD_NOT_COPY'
        c = self.convert(data=data)
        self.assertNotIn('API_SECRET', json.dumps(c))
        self.assertNotIn('SHOULD_NOT_COPY', json.dumps(c))

    def test_real_language_translation_not_falsely_scored(self):
        contract = self.convert()
        contract['regions'][1]['translation'] = '你好，朋友'
        outcome = a.audit(read_json(CASE), contract)
        self.assertFalse(outcome['passed'])
        self.assertIn('wrong_target_token', [e['code'] for e in outcome['errors']])

    def test_no_network_during_adapter(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            self.assertTrue(a.audit(read_json(CASE), self.convert())['passed'])


if __name__ == '__main__':
    unittest.main()
