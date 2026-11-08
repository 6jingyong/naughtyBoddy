"""P3.1 tests run offline; no model download, GPU, or paid API required."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch, MagicMock

from nb_common import ProviderError
from nb_model_manager import ModelManager, managed_models
from nb_studio import StudioHTTP, StudioService

FAKE_HW={"platform":"Linux","machine":"x86_64","cpu_cores_logical":4,
         "system_ram_bytes":16*1024**3,"gpus":[],"notes":[]}

class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.manager=ModelManager(self.root)

    def tearDown(self):
        self.manager.stop()
        self.tmp.cleanup()

    def test_status_ollama_offline_still_returns_hardware(self):
        with patch('nb_model_manager.hardware_inventory', return_value=FAKE_HW),\
             patch('naughtyboddy.discover_ollama', side_effect=ProviderError('offline')):
            data=self.manager.status()
        self.assertFalse(data['ollama']['available'])
        self.assertEqual(data['hardware']['platform'],'Linux')
        self.assertEqual(data['gguf'],[])

    def test_catalog_hardware_fit_and_unknown_size(self):
        cat={"repo":"user/model", "license":"mit", "gated":False, "private":False,
             "revision":"a"*40,"files":[{"filename":"q4.gguf","size_bytes":1_000_000},
                                            {"filename":"q5.gguf","size_bytes":None}]}
        with patch('nb_model_manager.gguf_catalog',return_value=cat),\
             patch('nb_model_manager.hardware_inventory',return_value=FAKE_HW):
            data=self.manager.catalog('user/model')
        self.assertTrue(data['files'][0]['fit'])
        self.assertIsNone(data['files'][1]['fit'])
        with self.assertRaises(ProviderError):
            self.manager.catalog('https://not-a-repo')

    def test_gguf_requires_explicit_consent_and_license_review(self):
        with self.assertRaises(ProviderError):
            self.manager.install({'kind':'gguf','repo':'user/model','filename':'file.gguf'})
        with self.assertRaises(ProviderError):
            self.manager.install({'kind':'gguf','repo':'user/model','filename':'file.gguf','confirm_download':True})
        with self.assertRaises(ProviderError):
            self.manager.install({'kind':'gguf','repo':'user/model','filename':'../file.gguf','confirm_download':True,'license_reviewed':True})
        with self.assertRaises(ProviderError):
            self.manager.install({'kind':'gguf','repo':'user/model','filename':'file.gguf','confirm_download':True,'license_reviewed':True,'max_gb':100})

    def test_confirmed_gguf_download_goes_into_managed_dir(self):
        def fake(repo, filename, root, **kwargs):
            self.assertEqual(root,self.manager.root)
            kwargs['on_progress'](1048576)
            return {'status':'downloaded','filename':filename,'size_bytes':1048576}
        with patch('nb_model_manager.download_gguf', side_effect=fake):
            job=self.manager.install({'kind':'gguf','repo':'user/model','filename':'q4.gguf',
                                      'confirm_download':True,'license_reviewed':True})
            for _ in range(100):
                s=self.manager.job(job['job_id'])
                if s['state'] in ('done','failed'):break
                time.sleep(.01)
        self.assertEqual(s['state'],'done',s)
        self.assertEqual(s['progress_bytes'],1048576)

    def test_ollama_install_stays_local_and_serialized(self):
        started=threading.Event();finish=threading.Event()
        def slow(model):
            started.set();finish.wait(timeout=3)
            return {'status':'installed','model':model}
        with patch('nb_model_manager.ollama_pull',side_effect=slow):
            job=self.manager.install({'kind':'ollama','model':'local:latest','confirm_download':True})
            self.assertTrue(started.wait(timeout=2))
            with self.assertRaises(ProviderError):
                self.manager.install({'kind':'ollama','model':'second','confirm_download':True})
            finish.set()
            for _ in range(100):
                s=self.manager.job(job['job_id'])
                if s['state']=='done':break
                time.sleep(.01)
        self.assertEqual(s['state'],'done',s)

    def test_managed_models_ignores_external_symlinks(self):
        d=self.manager.root/'author--model';d.mkdir()
        (d/'valid.gguf').write_bytes(b'GGUF'+b'\0'*16)
        other=self.root/'other.gguf';other.write_bytes(b'GGUF')
        (d/'external.gguf').symlink_to(other)
        rows=managed_models(self.manager.root,FAKE_HW)
        self.assertEqual([x['name'] for x in rows],['author--model/valid.gguf'])
        with self.assertRaises(ProviderError):
            self.manager._managed_path('../other.gguf')

    def test_launch_requires_consent_and_executable(self):
        folder=self.manager.root/'author--model';folder.mkdir()
        (folder/'q4.gguf').write_bytes(b'GGUF'+b'\0'*8)
        with self.assertRaises(ProviderError):
            self.manager.launch({'name':'author--model/q4.gguf'})
        with patch('nb_model_manager.shutil.which',return_value=None):
            with self.assertRaises(ProviderError):
                self.manager.launch({'name':'author--model/q4.gguf','confirm_launch':True})
        proc=MagicMock();proc.poll.return_value=None
        proc.wait.return_value=0
        with patch('nb_model_manager.shutil.which',return_value='/bin/llama-server'),\
             patch('nb_model_manager.subprocess.Popen',return_value=proc) as mock:
            status=self.manager.launch({'name':'author--model/q4.gguf','confirm_launch':True,'port':18080})
            self.assertIn(status['state'],('starting','ready'))
            self.assertEqual(mock.call_args.args[0][3:5],['--host','127.0.0.1'])
            self.assertEqual(self.manager.stop()['state'],'stopped')
            proc.terminate.assert_called_once()

    def test_evaluation_is_explicit_and_keeps_private_reports(self):
        with self.assertRaises(ProviderError):
            self.manager.evaluate({'provider':'compatible','model':'demo','base_url':'https://example.com/v1'})
        with patch('naughtyboddy.infer_text',return_value='Avery Jordan 信任'):
            started=self.manager.evaluate({'provider':'ollama','model':'demo'})
            for _ in range(100):
                job=self.manager.job(started['job_id'])
                if job['state'] in ('done','failed'):break
                time.sleep(.01)
        self.assertEqual(job['state'],'done',job)
        report=self.manager.reports()[0]
        self.assertEqual(report['summary']['total'],3)
        self.assertEqual(report['assessment'],'heuristic_only_manual_review_pending')
        raw=json.loads((self.manager.evaluations/report['id']).read_text())
        self.assertTrue(all('response' not in c for c in raw['cases']))


class ModelHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.service=StudioService(Path(self.tmp.name)/'workspace')
        self.server=StudioHTTP(('127.0.0.1',0),self.service)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_address[1]}'
        self.token=json.loads(urlopen(self.base+'/api/bootstrap').read())['csrf_token']

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
        self.service.models.stop();self.tmp.cleanup()

    def request(self,path,method='GET',body=None,token=None):
        headers={}
        if method!='GET': headers={'X-NB-Token':self.token if token is None else token,
                                   'Content-Type':'application/json'}
        req=Request(self.base+path,data=None if body is None else json.dumps(body).encode(),
                    method=method,headers=headers)
        with urlopen(req,timeout=3) as r: return json.loads(r.read())

    def test_hardware_and_engine_http(self):
        with patch('nb_model_manager.hardware_inventory',return_value=FAKE_HW),\
             patch('naughtyboddy.discover_ollama',return_value=[]):
            self.assertEqual(self.request('/api/local/status')['hardware']['platform'],'Linux')
        self.assertEqual(self.request('/api/local/engine')['state'],'stopped')

    def test_model_download_requires_server_side_approval(self):
        body={'kind':'ollama','model':'demo'}
        with self.assertRaises(HTTPError) as e: self.request('/api/local/install','POST',body)
        self.assertEqual(e.exception.code,400)
        with self.assertRaises(HTTPError) as e:
            self.request('/api/local/install','POST',{'kind':'ollama','model':'demo','confirm_download':True},token='bad')
        self.assertEqual(e.exception.code,403)

    def test_catalog_and_studio_static_widgets(self):
        cat={'repo':'abc/q4','files':[],'revision':'a'*40,'license':'other','gated':False,'private':False}
        with patch('nb_model_manager.gguf_catalog',return_value=cat),\
             patch('nb_model_manager.hardware_inventory',return_value=FAKE_HW):
            self.assertEqual(self.request('/api/local/catalog?repo=abc%2Fq4')['repo'],'abc/q4')
        with urlopen(self.base+'/') as r: html=r.read().decode()
        self.assertIn('gguf-download',html)
        self.assertIn('local-manager',html)
        with urlopen(self.base+'/app.js') as r: js=r.read().decode()
        self.assertIn('pollModelJob',js)

if __name__=='__main__': unittest.main()
