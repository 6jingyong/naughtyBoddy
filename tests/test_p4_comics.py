"""P4 tests use synthetic images and stub language models, no explicit material."""
import base64
import json
import struct
import tempfile
import threading
import time
import unittest
import zlib
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from nb_common import ProviderError
from nb_comics import ComicLibrary, image_size
from nb_studio import StudioHTTP, StudioService


def fake_png(width=64, height=48):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data)&0xffffffff)
    data = b''.join(b'\x00' + b'\xff\xff\xff' * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(data)) + chunk(b'IEND', b'')


class ComicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.library = ComicLibrary(Path(self.tmp.name))
        self.picture = fake_png()

    def tearDown(self):
        self.tmp.cleanup()

    def make_one(self):
        return self.library.create(filename='story.png', image=self.picture, rights_confirmed=True)['id']

    def test_dimensions_and_bad_image(self):
        self.assertEqual(image_size(self.picture), ('png',64,48))
        with self.assertRaises(ProviderError): image_size(b'not a valid image')
        with self.assertRaises(ProviderError): image_size(fake_png(15000, 15000))

    def test_create_rights_and_safe_filename(self):
        with self.assertRaises(ProviderError):
            self.library.create(filename='story.png', image=self.picture, rights_confirmed=False)
        with self.assertRaises(ProviderError):
            self.library.create(filename='../story.png', image=self.picture, rights_confirmed=True)
        with self.assertRaises(ProviderError):
            self.library.create(filename='story.jpg', image=self.picture, rights_confirmed=True)
        id=self.make_one()
        self.assertEqual(len(self.library.list()),1)
        with self.assertRaises(ProviderError): self.library.get('../secrets')
        meta=self.library.get(id)
        self.assertEqual(meta['title'],'story')
        self.assertEqual(self.library.page_bytes(id,meta['pages'][0]['id'])[0],self.picture)

    def test_regions_edit_version_and_reopen(self):
        id=self.make_one();page=self.library.get(id)['pages'][0]['id']
        region=self.library.add_region(id,page_id=page,box=[.1,.2,.4,.3],source='Hello')
        self.assertEqual(region['revision'],1)
        edited=self.library.edit_region(id,region['id'],target='你好',expected_revision=1)
        self.assertEqual(edited['revision'],2)
        self.assertEqual(ComicLibrary(Path(self.tmp.name)).get(id)['regions'][0]['target'],'你好')
        with self.assertRaises(ProviderError): self.library.edit_region(id,region['id'],target='Oops',expected_revision=1)
        for box in ([0,0,-1,1],[.9,.9,.2,.2],[0,0,0,1],[True,0,.5,.5]):
            with self.assertRaises(ProviderError): self.library.add_region(id,page_id=page,box=box)

    def test_model_is_just_a_function_and_user_edits_win(self):
        id=self.make_one();page=self.library.get(id)['pages'][0]['id']
        region=self.library.add_region(id,page_id=page,box=[.2,.2,.5,.5],source='Good morning')
        result=self.library.translate_region(id,region['id'],lambda x:'早上好',provider='ollama',model='local')
        self.assertEqual(result['target'],'早上好')
        self.assertEqual(result['method'],'ollama/local')
        with self.assertRaises(ProviderError):
            def racing(prompt):
                self.library.edit_region(id,region['id'],target='人工修改')
                return '机器结果'
            self.library.translate_region(id,region['id'],racing,provider='ollama',model='local')
        self.assertEqual(self.library.get(id)['regions'][0]['target'],'人工修改')

    def test_export_svg_and_demo_protection(self):
        id=self.library.create(filename='large.png',image=fake_png(640,480),rights_confirmed=True)['id'];page=self.library.get(id)['pages'][0]['id']
        region=self.library.add_region(id,page_id=page,box=[.1,.1,.8,.8],source='Hello')
        with self.assertRaises(ProviderError): self.library.export_svg(id,page)
        self.library.edit_region(id,region['id'],target='<script>alert(1)</script>')
        svg=self.library.export_svg(id,page)
        self.assertIn(b'<svg ',svg)
        self.assertNotIn(b'<script>',svg)
        self.assertIn(b'&lt;script&gt;',svg)
        self.library.translate_region(id,region['id'],lambda _: '[DEMO] Hi',provider='mock',model='demo')
        with self.assertRaises(ProviderError): self.library.export_svg(id,page)
        self.assertIn(b'[DEMO]',self.library.export_svg(id,page,allow_demo=True))

    def test_multi_page_and_no_symlink_project(self):
        id=self.make_one()
        page=self.library.add_page(id,filename='next.png',image=self.picture)
        self.assertEqual(len(self.library.get(id)['pages']),2)
        self.assertEqual(page['width'],64)
        with tempfile.TemporaryDirectory() as other:
            try:
                (self.library.root/('c'*32)).symlink_to(Path(other),target_is_directory=True)
            except (OSError,NotImplementedError): return
            self.assertEqual(len(self.library.list()),1)


class ComicHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.service=StudioService(Path(self.tmp.name)/'workspace')
        self.server=StudioHTTP(('127.0.0.1',0),self.service)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_address[1]}'
        self.token=json.loads(urlopen(self.base+'/api/bootstrap').read())['csrf_token']

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(3);self.tmp.cleanup()

    def request(self,path, method='GET', body=None, binary=False, token=None):
        headers={}
        if method != 'GET':headers={'Content-Type':'application/json','X-NB-Token':token if token is not None else self.token}
        req=Request(self.base+path,headers=headers,method=method,
                    data=json.dumps(body).encode() if body is not None else None)
        with urlopen(req,timeout=10) as response:
            data=response.read()
            return data if binary else json.loads(data)

    def test_comic_http_roundtrip(self):
        payload={'filename':'test.png','base64':base64.b64encode(fake_png()).decode(), 'rights_confirmed':True}
        with self.assertRaises(HTTPError) as fail:
            self.request('/api/comics','POST',payload,token='wrong')
        self.assertEqual(fail.exception.code,403)
        created=self.request('/api/comics','POST',payload)
        id=created['id'];page=created['pages'][0]['id']
        self.assertEqual(self.request(f'/api/comics/{id}/pages/{page}/image',binary=True),fake_png())
        region=self.request(f'/api/comics/{id}/regions','POST',{'page_id':page,'box':[0.1,0.1,0.8,0.8],'source':'Hello'})
        self.request(f'/api/comics/{id}/regions/{region["id"]}','PATCH',{'target':'你好','expected_revision':1})
        data=self.request(f'/api/comics/{id}/pages/{page}/export.svg',binary=True)
        self.assertIn('你好'.encode(),data)
        self.assertEqual(len(self.request('/api/comics')['comics']),1)

    def test_explicit_remote_approval_and_mock_job(self):
        payload={'filename':'page.png','base64':base64.b64encode(fake_png()).decode(),'rights_confirmed':True}
        created=self.request('/api/comics','POST',payload)
        id=created['id'];page=created['pages'][0]['id']
        region=self.request(f'/api/comics/{id}/regions','POST',{'page_id':page,'box':[.1,.1,.8,.8],'source':'Hello'})
        url=f'/api/comics/{id}/regions/{region["id"]}/translate'
        with self.assertRaises(HTTPError): self.request(url,'POST',{'provider':'openrouter','model':'vendor/model'})
        job=self.request(url,'POST',{'provider':'mock'})
        for _ in range(100):
            status=self.request(f'/api/jobs/{job["job_id"]}')
            if status['state'] in ('done','failed'):break
            time.sleep(.02)
        self.assertEqual(status['state'],'done',status)
        with self.assertRaises(HTTPError):self.request(f'/api/comics/{id}/pages/{page}/export.svg',binary=True)
        self.assertIn(b'[DEMO]',self.request(f'/api/comics/{id}/pages/{page}/export.svg?allow_demo=1',binary=True))

if __name__=='__main__':unittest.main()
