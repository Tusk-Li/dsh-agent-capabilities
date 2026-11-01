import base64
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills'
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

image = module('images', ROOT / 'dsh-image-service/scripts/image_service.py')
chart = module('chart', ROOT / 'dsh-visualize/scripts/chart.py')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        self.server.requests.append((self.path, dict(self.headers), self.rfile.read(int(self.headers['Content-Length']))))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(self.server.reply).encode())

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = Path(self.temp.name)
        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.server.requests = []
        self.server.reply = {'data': [{'b64_json': base64.b64encode(PNG).decode()}]}
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.config = self.root / 'config.json'
        url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.config.write_text(json.dumps({'generationUrl': url+'/generate', 'editUrl': url+'/edit', 'model':'test', 'apiKeyEnv':'DSH_TEST_IMAGE_KEY'}))
        os.environ['DSH_TEST_IMAGE_KEY'] = 'test-only'
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()
        os.environ.pop('DSH_TEST_IMAGE_KEY', None)
    def args(self, **kw):
        values = dict(command='generate', config=self.config, allow_local=True, prompt='test', count=1, size=None, output_dir=self.root/'out')
        values.update(kw)
        return SimpleNamespace(**values)
    def test_generate_and_unique_paths(self):
        a, b = image.run(self.args()), image.run(self.args())
        self.assertNotEqual(a['files'], b['files'])
        self.assertEqual(Path(a['files'][0]).read_bytes(), PNG)
        _, headers, body = self.server.requests[0]
        self.assertEqual(headers['Authorization'], 'Bearer test-only')
        self.assertEqual(json.loads(body)['model'], 'test')
    def test_edit_multipart(self):
        p = self.root/'input.png'; p.write_bytes(PNG)
        image.run(self.args(command='edit', image=p, mask=None))
        path, headers, body = self.server.requests[0]
        self.assertEqual(path, '/edit')
        self.assertIn('multipart/form-data', headers['Content-Type'])
        self.assertIn(b'name="image"', body)
        self.assertIn(PNG, body)
    def test_status_no_network_or_secret(self):
        result=image.run(self.args(command='status'))
        self.assertTrue(result['credentialAvailable'])
        self.assertNotIn('test-only', json.dumps(result))
        self.assertEqual(self.server.requests, [])
    def test_invalid_response_writes_nothing(self):
        self.server.reply={'data':[{'b64_json':base64.b64encode(b'not an image').decode()}]}
        with self.assertRaises(ValueError): image.run(self.args())
        self.assertFalse((self.root/'out').exists())
    def test_https_required(self):
        with self.assertRaises(ValueError): image.run(self.args(allow_local=False))
    def test_missing_credential_no_request(self):
        os.environ.pop('DSH_TEST_IMAGE_KEY')
        with self.assertRaises(ValueError): image.run(self.args())
        self.assertEqual(self.server.requests, [])
    def test_chart_escaping_and_numbers(self):
        out=chart.render({'title':'<b>X</b>', 'labels':['</script><script>alert(1)</script>'], 'values':[-2]})
        self.assertNotIn('</script><script>alert',out)
        self.assertIn('&lt;b&gt;X&lt;/b&gt;',out)
        for values in ([float('nan')], [True], [float('inf')]):
            with self.assertRaises(ValueError): chart.render({'labels':['x'],'values':values})

if __name__ == '__main__': unittest.main(verbosity=2)
