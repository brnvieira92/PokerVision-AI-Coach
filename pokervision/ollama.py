"""Cliente HTTP exclusivo de loopback; sem SDK, downloads implícitos ou credenciais."""
import http.client
import json
import io
import socket
import threading
from urllib.parse import urlsplit
from .resources import CancelToken, Cancelled

MAIN_MODEL = 'qwen3:1.7b-q4_K_M'
ECONOMY_MODEL = 'qwen3:0.6b-q4_K_M'


class OllamaError(Exception):
    pass


class _PollingReader(io.RawIOBase):
    """Socket com leituras curtas retomáveis, inclusive durante carregamento do modelo."""
    def __init__(self, sock, token, expired):
        super().__init__()
        self.sock = sock.dup()
        self.sock.settimeout(0.2)
        self.token, self.expired = token, expired

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            self.token.check()
            if self.expired.is_set():
                raise OllamaError('O Ollama excedeu o tempo de resposta.')
            try:
                return self.sock.recv_into(buffer)
            except socket.timeout:
                continue

    def close(self):
        self.sock.close()
        super().close()


class _ResponseSocket:
    def __init__(self, sock, token, expired):
        self.sock, self.token, self.expired = sock, token, expired

    def makefile(self, mode):
        return io.BufferedReader(_PollingReader(self.sock, self.token, self.expired))


class OllamaProvider:
    def __init__(self, base_url='http://127.0.0.1:11434', timeout=90):
        url = urlsplit(base_url)
        if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1') or
                url.username or url.password or url.path not in ('', '/') or url.query or url.fragment):
            raise ValueError('Use um servidor Ollama HTTP local, sem credenciais ou caminhos.')
        self.host, self.port, self.timeout = url.hostname, url.port or 11434, timeout

    def _request(self, path, payload=None, token=None, progress=None, timeout=None):
        token = token or CancelToken()
        token.check()
        deadline = timeout or self.timeout
        connection = http.client.HTTPConnection(self.host, self.port, timeout=min(5, deadline))
        expired = threading.Event()
        connection.response_class = lambda sock, **kwargs: http.client.HTTPResponse(
            _ResponseSocket(sock, token, expired), **kwargs)
        response = None

        def abort():
            sock = connection.sock
            if sock:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            connection.close()

        def expire():
            expired.set()
            abort()

        token.bind(abort)
        timer = threading.Timer(deadline, expire)
        timer.daemon = True
        timer.start()
        try:
            connection.connect()
            token.check()
            if expired.is_set():
                raise OllamaError('O Ollama excedeu o tempo de resposta.')
            connection.sock.settimeout(deadline)
            connection.request('GET' if payload is None else 'POST', path,
                               body=None if payload is None else json.dumps(payload).encode('utf-8'),
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            if response.status != 200:
                raise OllamaError(f'Ollama HTTP {response.status}: ' + response.read(2048).decode('utf-8', errors='replace'))
            if payload and payload.get('stream'):
                chunks, size, final = [], 0, False
                while True:
                    token.check()
                    line = response.readline(65537)
                    if not line:
                        break
                    if len(line) > 65536:
                        raise OllamaError('Resposta do Ollama acima do limite.')
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        raise OllamaError('Evento inválido do Ollama.')
                    if item.get('error'):
                        raise OllamaError(str(item['error']))
                    chunk = item.get('message', {}).get('content', '')
                    if not isinstance(chunk, str):
                        raise OllamaError('Conteúdo inválido do Ollama.')
                    size += len(chunk)
                    if size > 16384:
                        raise OllamaError('Explicação acima do limite.')
                    chunks.append(chunk)
                    if progress:
                        progress(item if path == '/api/pull' else chunk)
                    final = bool(item.get('done')) or (path == '/api/pull' and item.get('status') == 'success')
                    if final:
                        if item.get('done_reason') == 'length':
                            raise OllamaError('Resposta interrompida pelo limite de tokens.')
                        break
                if not final:
                    raise OllamaError('Resposta interrompida antes de terminar.')
                result = ''.join(chunks)
            else:
                data = response.read(1048577)
                if len(data) > 1048576:
                    raise OllamaError('Resposta acima do limite.')
                result = json.loads(data)
            token.check()
            if expired.is_set():
                raise OllamaError('O Ollama excedeu o tempo de resposta.')
            return result
        except Exception as exc:
            if token.event.is_set():
                raise Cancelled('Solicitação cancelada.') from exc
            if expired.is_set() or isinstance(exc, (TimeoutError, socket.timeout)):
                raise OllamaError('O Ollama excedeu o tempo de resposta.') from exc
            if isinstance(exc, OllamaError):
                raise
            if isinstance(exc, (OSError, ValueError, http.client.HTTPException, AttributeError)):
                raise OllamaError('Não foi possível conversar com o Ollama local: ' + str(exc)) from exc
            raise
        finally:
            timer.cancel()
            token.bind(None)
            connection.close()
            if response is not None:
                response.close()

    def models(self, token=None):
        data = self._request('/api/tags', token=token, timeout=5)
        if not isinstance(data, dict) or not isinstance(data.get('models'), list):
            raise OllamaError('Listagem de modelos inválida.')
        return [m['name'] for m in data['models'] if isinstance(m, dict) and isinstance(m.get('name'), str)
                and not m.get('remote_host') and 'cloud' not in m['name'].lower()]

    @staticmethod
    def choose_model(installed, mode):
        preferred = [ECONOMY_MODEL, 'qwen3:0.6b'] if mode == 'economy' else [MAIN_MODEL, 'qwen3:1.7b', ECONOMY_MODEL, 'qwen3:0.6b']
        lookup = {m.lower(): m for m in installed}
        return next((lookup[m.lower()] for m in preferred if m.lower() in lookup), None)

    def chat(self, model, messages, schema, token, progress=None, cpu=False):
        payload = dict(model=model, messages=messages, format=schema, stream=True,
                       think=False, keep_alive='2m',
                       options=dict(num_ctx=2048, num_predict=384, temperature=0.2))
        if cpu:
            payload['options']['num_gpu'] = 0
        return self._request('/api/chat', payload, token, progress)

    def pull(self, model, *, authorized=False, token=None, progress=None):
        if not authorized:
            raise PermissionError('O download exige autorização explícita.')
        return self._request('/api/pull', dict(model=model, stream=True), token, progress, timeout=1800)

    def unload(self, model, token=None):
        return self._request('/api/generate', dict(model=model, keep_alive=0, stream=False), token, timeout=15)
