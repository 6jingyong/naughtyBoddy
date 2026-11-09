import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from zipfile import ZipFile

import nb_evalkit as kit


class SyntheticEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.book = kit.read_json(kit.ROOT / 'book_case.json')
        self.comic = kit.read_json(kit.ROOT / 'comic_case.json')
        self.memory = kit.read_json(kit.ROOT / 'memory_case.json')
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def epub(self, variant):
        path = Path(self.tmp.name) / (variant + '.epub')
        kit.generate_epub(self.book, path, variant)
        return path

    def test_full_demo_has_expected_failures_and_no_real_model_claim(self):
        report = kit.run_demo()
        self.assertTrue(report['passed'])
        self.assertEqual(len(report['cases']), 8)
        self.assertEqual(report['real_model_tests'], 'not_run')
        self.assertTrue(all(v['scope'] == 'synthetic_contract_only' for v in report['cases'].values()))

    def test_epub_source_and_good_output_have_same_spine(self):
        spine_a, units_a = kit.epub_units(self.epub('source'))
        spine_b, units_b = kit.epub_units(self.epub('good'))
        self.assertEqual(spine_a, spine_b)
        self.assertEqual(len(units_a), len(units_b))
        with ZipFile(self.epub('good')) as z:
            self.assertEqual(z.namelist()[0], 'mimetype')
            self.assertEqual(z.getinfo('mimetype').compress_type, 0)
        self.assertTrue(kit.check_book(self.book, self.epub('good'))['passed'])

    def test_p_only_translation_catches_headings_and_divs(self):
        report = kit.check_book(self.book, self.epub('p_only_bad'))
        self.assertFalse(report['passed'])
        self.assertEqual(sum(x['code'] == 'unchanged_source' for x in report['errors']), 4)

    def test_missing_paragraph_detected(self):
        report = kit.check_book(self.book, self.epub('missing_bad'))
        self.assertIn('missing_segment', {x['code'] for x in report['errors']})

    def test_swapped_paragraphs_detected(self):
        report = kit.check_book(self.book, self.epub('swapped_bad'))
        self.assertEqual(sum(x['code'] == 'target_token_mismatch' for x in report['errors']), 2)

    def test_epub_missing_archive_part_is_rejected(self):
        path = Path(self.tmp.name) / 'invalid.epub'
        with ZipFile(path, 'w') as z:
            z.writestr('mimetype', 'application/epub+zip')
        with self.assertRaises(kit.KitError):
            kit.epub_units(path)

    def test_epub_duplicate_members_rejected(self):
        path = Path(self.tmp.name) / 'dup.epub'
        with ZipFile(path, 'w') as z:
            z.writestr('mimetype', 'application/epub+zip')
            with __import__('warnings').catch_warnings():
                __import__('warnings').simplefilter('ignore', UserWarning)
                z.writestr('mimetype', 'application/epub+zip')
        with self.assertRaisesRegex(kit.KitError, 'duplicate EPUB members'):
            kit.epub_units(path)

    def test_epub_path_traversal_rejected(self):
        path = Path(self.tmp.name) / 'unsafe.epub'
        with ZipFile(path, 'w') as z:
            z.writestr('mimetype', 'application/epub+zip')
            z.writestr('../escape', 'not safe')
        with self.assertRaisesRegex(kit.KitError, 'Unsafe ZIP member path'):
            kit.epub_units(path)

    def test_duplicate_source_segment_rejected(self):
        broken = copy.deepcopy(self.book)
        broken['chapters'][0]['segments'].append(broken['chapters'][0]['segments'][0])
        with self.assertRaisesRegex(kit.KitError, 'duplicate segment'):
            kit.generate_epub(broken, self.epub('good'))

    def test_comic_good_and_shifted_bubbles(self):
        self.assertTrue(kit.check_comic(self.comic, kit.read_json(kit.ROOT / 'comic_good.json'))['passed'])
        report = kit.check_comic(self.comic, kit.read_json(kit.ROOT / 'comic_bad_shifted.json'))
        self.assertEqual({x['code'] for x in report['errors']}, {'missing_bubble','shifted_target_token'})

    def test_comic_duplicate_and_extra_id(self):
        output = kit.read_json(kit.ROOT / 'comic_good.json')
        output['outputs'].append({'id': 'b01', 'text': 'TGT_B01'})
        output['outputs'].append({'id': 'b99', 'text': 'TGT_B99'})
        report = kit.check_comic(self.comic, output)
        self.assertEqual({x['code'] for x in report['errors']}, {'duplicate_bubble','extra_bubble'})

    def test_memory_good_and_cross_character_leak(self):
        self.assertTrue(kit.check_memory(self.memory, kit.read_json(kit.ROOT / 'memory_good.json'))['passed'])
        report = kit.check_memory(self.memory, kit.read_json(kit.ROOT / 'memory_bad_leak.json'))
        self.assertEqual(len([x for x in report['errors'] if x['code']=='private_fact_leak']), 2)
        self.assertEqual({x['channel'] for x in report['errors']}, {'history', 'lorebook'})

    def test_memory_unknown_fact_is_visible_error(self):
        output = kit.read_json(kit.ROOT / 'memory_good.json')
        output['snapshots']['Mira']['memory'].append('f-not-real')
        self.assertIn('unknown_fact', {x['code'] for x in kit.check_memory(self.memory, output)['errors']})

    def test_memory_cannot_omit_character_snapshot(self):
        output = kit.read_json(kit.ROOT / 'memory_good.json')
        output['snapshots'].pop('Jon')
        self.assertIn('missing_actor', {x['code'] for x in kit.check_memory(self.memory, output)['errors']})

    def test_cli_good_and_bad_return_codes(self):
        good = str(kit.ROOT / 'comic_good.json')
        bad = str(kit.ROOT / 'comic_bad_shifted.json')
        with redirect_stdout(io.StringIO()):
            self.assertEqual(kit.main(['check-comic','--candidate',good]), 0)
            self.assertEqual(kit.main(['check-comic','--candidate',bad]), 1)
            self.assertEqual(kit.main(['demo']), 0)

    def test_no_external_network_access_during_demo(self):
        from unittest.mock import patch
        with patch('urllib.request.urlopen', side_effect=AssertionError('network accessed')):
            self.assertTrue(kit.run_demo()['passed'])


if __name__ == '__main__':
    unittest.main()
