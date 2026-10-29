"""Recursos locais: medição sem exigir GPU e uma operação de IA por vez."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import csv
import io
import platform
import subprocess
import threading
import psutil


class Cancelled(Exception):
    pass


class CancelToken:
    def __init__(self):
        self.event = threading.Event()
        self._lock = threading.Lock()
        self._abort = None

    def check(self):
        if self.event.is_set():
            raise Cancelled('Solicitação cancelada.')

    def bind(self, callback):
        with self._lock:
            self._abort = callback
            cancelled = self.event.is_set()
        if cancelled and callback:
            callback()

    def cancel(self):
        self.event.set()
        with self._lock:
            callback = self._abort
        if callback:
            callback()


@dataclass
class HardwareProfile:
    system: str
    processor: str
    cpu_count: int
    ram_total_gb: float
    ram_available_gb: float
    cpu_percent: float
    app_ram_mb: float
    gpus: list
    gpu_note: str

    def to_dict(self):
        return asdict(self)


class HardwareProfiler:
    def profile(self):
        memory = psutil.virtual_memory()
        gpus, note = [], 'GPU não detectada; CPU continua disponível.'
        try:
            kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if platform.system() == 'Windows' else {}
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free,driver_version',
                                     '--format=csv,noheader,nounits'], capture_output=True,
                                    text=True, timeout=3, check=True, **kwargs)
            for row in csv.reader(io.StringIO(result.stdout)):
                if len(row) == 4:
                    name, total, free, driver = [v.strip() for v in row]
                    gpus.append(dict(name=name, vram_total_mb=float(total),
                                     vram_free_mb=float(free), driver=driver))
            if gpus:
                note = 'Leitura NVIDIA; alocação real do modelo é decidida pelo Ollama.'
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        return HardwareProfile(platform.platform(), platform.processor() or 'Não identificado',
                               psutil.cpu_count() or 1, memory.total/2**30, memory.available/2**30,
                               psutil.cpu_percent(interval=None), psutil.Process().memory_info().rss/2**20,
                               gpus, note)


class ResourceManager:
    def __init__(self, available=None):
        self.lock = threading.Lock()
        self.available = available or (lambda: psutil.virtual_memory().available/2**30)

    def mode_for_memory(self, requested):
        free = self.available()
        if requested == 'off' or free < 1.5:
            return 'off'
        return 'economy' if requested == 'balanced' and free < 3 else requested

    @contextmanager
    def inference(self, token):
        while not self.lock.acquire(timeout=0.05):
            token.check()
        try:
            token.check()
            yield
        finally:
            self.lock.release()


RESOURCES = ResourceManager()
