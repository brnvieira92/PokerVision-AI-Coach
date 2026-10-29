"""Servidor HTTP de teste local: valida protocolo real sem instalar ou chamar um LLM."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
import pytest
from pokervision.ollama import OllamaProvider, OllamaError, MAIN_MODEL
from pokervision.resources import CancelToken, Cancelled


@pytest.fixture
def server():
    state={'requests':[], 'mode':'ok', 'started':threading.Event()}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_GET(self):
            self.reply(None)
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            self.reply(payload)
        def reply(self,payload):
            state['requests'].append((self.path,payload))
            self.send_response(200)
            self.send_header('Content-Type','application/x-ndjson')
            if self.path=='/api/chat' and state['mode']=='chunked':
                self.send_header('Transfer-Encoding','chunked')
            self.send_header('Connection','close')
            self.end_headers()
            self.close_connection=True
            try:
                if self.path=='/api/tags':
                    self.wfile.write(json.dumps({'models':[{'name':MAIN_MODEL},
                        {'name':'huge:cloud','remote_host':'cloud.example'}]}).encode())
                elif self.path=='/api/pull':
                    self.wfile.write(b'{"status":"pulling","completed":5,"total":10}\n{"status":"success"}\n')
                elif self.path=='/api/generate':
                    self.wfile.write(b'{"done":true}')
                else:
                    if state['mode']=='chunked':
                        for part in (b'{"message":{"content":"hello"},"done":false}\n',
                                     b'{"message":{"content":" world"},"done":true}\n'):
                            self.wfile.write(f'{len(part):x}\r\n'.encode()+part+b'\r\n')
                        self.wfile.write(b'0\r\n\r\n')
                        return
                    if state['mode']=='bad-json':
                        self.wfile.write(b'not json\n')
                        return
                    self.wfile.write(b'{"message":{"content":"hello"},"done":false}\n')
                    self.wfile.flush()
                    state['started'].set()
                    if state['mode']=='slow':
                        time.sleep(1)
                    if state['mode']!='truncated':
                        self.wfile.write(b'{"message":{"content":" world"},"done":true}\n')
            except (OSError, ConnectionError):
                pass
    httpd=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=lambda:httpd.serve_forever(poll_interval=.02),daemon=True)
    thread.start()
    provider=OllamaProvider(f'http://127.0.0.1:{httpd.server_port}',timeout=3)
    yield provider,state
    httpd.shutdown()
    httpd.server_close()
    thread.join(1)


def test_http_streaming_options_models_pull_and_unload(server):
    p,state=server
    assert p.models()==[MAIN_MODEL]
    chunks=[]
    assert p.chat(MAIN_MODEL,[],{},CancelToken(),chunks.append,cpu=True)=='hello world'
    payload=state['requests'][-1][1]
    assert payload['think'] is False and payload['keep_alive']=='2m'
    assert payload['options']==dict(num_gpu=0,num_ctx=2048,num_predict=384,temperature=.2)
    assert chunks==['hello',' world']
    events=[]
    p.pull(MAIN_MODEL,authorized=True,progress=events.append)
    assert events[-1]['status']=='success'
    p.unload(MAIN_MODEL)
    assert state['requests'][-1][1]['keep_alive']==0


@pytest.mark.parametrize('mode',['bad-json','truncated'])
def test_http_invalid_or_incomplete_stream(server,mode):
    p,state=server
    state['mode']=mode
    with pytest.raises(OllamaError):
        p.chat(MAIN_MODEL,[],{},CancelToken())


def test_http_cancellation_interrupts_waiting_socket(server):
    p,state=server
    state['mode']='slow'
    token,errors=CancelToken(),[]
    def run():
        try:
            p.chat(MAIN_MODEL,[],{},token)
        except Exception as exc:
            errors.append(exc)
    thread=threading.Thread(target=run)
    thread.start()
    assert state['started'].wait(1)
    token.cancel()
    thread.join(.7)
    assert not thread.is_alive()
    assert len(errors)==1 and isinstance(errors[0],Cancelled)


def test_http_overall_timeout(server):
    p,state=server
    state['mode']='slow'
    p.timeout=.15
    with pytest.raises(OllamaError,match='tempo'):
        p.chat(MAIN_MODEL,[],{},CancelToken())



def test_http_chunked_stream(server):
    p,state=server
    state['mode']='chunked'
    assert p.chat(MAIN_MODEL,[],{},CancelToken())=='hello world'
