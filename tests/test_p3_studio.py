import base64
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from nb_common import ProviderError
from nb_studio import StudioService, StudioHTTP


class StudioServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.svc = StudioService(Path(self.tmp.name) / 'work')
        self.text = 'Chapter 1\n\nThis is the first paragraph about two adults.\n\nAnother ordinary paragraph.\n'

    def tearDown(self):
        self.tmp.cleanup()

    def import_one(self):
        return self.svc.import_book({'filename': 'Book.txt', 'base64': base64.b64encode(self.text.encode()).decode(),
                                     'target_language': 'zh-CN', 'rights_confirmed': True})['id']

    def test_import_summary_segments_and_original_filename(self):
        pid = self.import_one()
        s = self.svc.summary(pid)
        self.assertGreater(s['segments'], 1)
        self.assertEqual(s['chapter_list'][0]['chapter_no'], 1)
        self.assertEqual(self.svc.segments(pid, 1)['rows'][0]['paragraph_no'], 0)
        meta = json.loads((self.svc.path(pid) / 'manifest.json').read_text())
        self.assertEqual(meta['source_filename'], 'Book.txt')

    def test_require_rights_and_reject_filename_traversal(self):
        good = base64.b64encode(self.text.encode()).decode()
        for bad in ({'filename': 'Book.txt', 'base64': good},
                    {'filename': '../Book.txt', 'base64': good, 'rights_confirmed': True},
                    {'filename': 'Book.jpg', 'base64': good, 'rights_confirmed': True}):
            with self.assertRaises(ProviderError):
                self.svc.import_book(bad)

    def test_manual_edits_title_and_version_history(self):
        pid = self.import_one()
        row = self.svc.segments(pid, 1)['rows'][0]
        changed = self.svc.edit_segment(pid, row['id'], '第一章')
        self.assertTrue(changed['changed'])
        self.assertEqual(self.svc.summary(pid)['chapter_list'][0]['translated_title'], '第一章')
        self.assertFalse(self.svc.edit_segment(pid, row['id'], '第一章')['changed'])
        with __import__('sqlite3').connect(self.svc.path(pid) / 'work.sqlite3') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM studio_edits').fetchone()[0], 1)
        self.svc.edit_segment(pid, row['id'], '')
        self.assertEqual(self.svc.summary(pid)['chapter_list'][0]['translated_title'], None)

    def test_mock_job_is_opt_in_and_demo_export_is_marked(self):
        pid = self.import_one()
        status = self.svc.start_translation(pid, {'provider':'mock','max_segments':20})
        for _ in range(100):
            job = self.svc.job_status(status['job_id'])
            if job['state'] in ('done','failed'):
                break
            time.sleep(0.02)
        self.assertEqual(job['state'], 'done', job)
        self.assertEqual(self.svc.summary(pid)['pending'], 0)
        with self.assertRaises(ProviderError):
            self.svc.export(pid, 'epub')
        exp = self.svc.export(pid, 'epub', allow_demo=True)
        self.assertTrue((self.svc.path(pid)/'exports'/exp['filename']).exists())
        self.assertTrue(exp['demo'])

    def test_glossary_roundtrip_and_validation(self):
        pid=self.import_one()
        self.assertEqual(self.svc.get_glossary(pid)['terms'],{})
        saved=self.svc.save_glossary(pid,{'Alice':'爱丽丝','Bob':'鲍勃'})
        self.assertEqual(saved['count'],2)
        self.assertEqual(self.svc.get_glossary(pid)['terms']['Alice'],'爱丽丝')
        with self.assertRaises(ProviderError):
            self.svc.save_glossary(pid,{'': 'bad'})

    def test_remote_consent(self):
        pid=self.import_one()
        with self.assertRaises(ProviderError):
            self.svc.start_translation(pid, {'provider':'openrouter', 'model':'sample/test'})
        with self.assertRaises(ProviderError):
            self.svc.start_translation(pid, {'provider':'compatible','model':'sample',
                                               'base_url':'https://somewhere.example/v1'})

    def test_project_id_validation(self):
        for name in ('../etc','not-valid','A'*32):
            with self.assertRaises(ProviderError):
                self.svc.path(name)

    def test_no_lan_binding(self):
        with self.assertRaises(ValueError):
            StudioHTTP(('0.0.0.0',0),self.svc)


class StudioHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.svc=StudioService(Path(self.tmp.name)/'work')
        self.server=StudioHTTP(('127.0.0.1',0),self.svc)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_address[1]}'
        self.token=self.fetch('/api/bootstrap')['csrf_token']

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3);self.tmp.cleanup()

    def fetch(self,path,method='GET',body=None,token=None,headers=None):
        hdr=headers or {}
        if method != 'GET':
            hdr.update({'Content-Type':'application/json','X-NB-Token':self.token if token is None else token})
        req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
                    headers=hdr,method=method)
        with urlopen(req,timeout=5) as r:
            return json.loads(r.read())

    def test_bootstrap_and_xss_safe_static_delivery(self):
        self.assertTrue(self.token)
        req=Request(self.base+'/')
        with urlopen(req) as r:
            self.assertIn(b'Creative Studio',r.read())
            self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff')
            self.assertIn('frame-ancestors',r.headers['Content-Security-Policy'])

    def test_mutations_require_csrf(self):
        with self.assertRaises(HTTPError) as e:
            self.fetch('/api/projects','POST',{'foo':'bar'},token='bad')
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(HTTPError) as e:
            self.fetch('/api/projects','POST',{'foo':'bar'},headers={'Origin':'http://evil.example'})
        self.assertEqual(e.exception.code,403)

    def test_http_import_edit_audit(self):
        raw=b'Chapter 1\n\nThe first paragraph.\n\nThe second paragraph.'
        imported=self.fetch('/api/projects','POST',{'filename':'book.txt','base64':base64.b64encode(raw).decode(),
                                                    'rights_confirmed':True})
        pid=imported['id']
        rows=self.fetch(f'/api/projects/{pid}/segments?chapter=1')['rows']
        self.assertTrue(rows)
        edited=self.fetch(f'/api/projects/{pid}/segments/{rows[0]["id"]}', 'PATCH', {'target':'第一章'})
        self.assertTrue(edited['changed'])
        self.assertGreater(self.fetch(f'/api/projects/{pid}/audit')['pending'],0)
        saved=self.fetch(f'/api/projects/{pid}/glossary','PATCH',{'terms':{'Alice':'爱丽丝'}})
        self.assertEqual(saved['count'],1)
        self.assertEqual(self.fetch(f'/api/projects/{pid}/glossary')['terms']['Alice'],'爱丽丝')
        with self.assertRaises(HTTPError) as e:
            self.fetch(f'/api/projects/{pid}/export','POST',{'format':'epub'})
        self.assertEqual(e.exception.code,400)

if __name__ == '__main__':
    unittest.main()
