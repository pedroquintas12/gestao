# config/logger.py
from datetime import datetime
import os, sys, logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os, sys, subprocess, tempfile, json, urllib.request, hashlib, shutil, traceback, ctypes, time
from pathlib import Path
from datetime import datetime, timedelta


APP_NAME = "Gestao"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / APP_NAME / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
APP_LOG = LOG_DIR / "app.log"

root = logging.getLogger()
if not root.handlers:  # evita duplicar
    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

    fh = RotatingFileHandler(APP_LOG, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)
    root.addHandler(fh)

    # só adiciona console se existir (ex.: rodando pelo .bat)
    stream = getattr(sys, "__stdout__", None) or getattr(sys, "__stderr__", None)
    if os.environ.get("GESTAO_DEBUG") == "1" and stream:
        sh = logging.StreamHandler(stream=stream)
        sh.setFormatter(fmt)
        sh.setLevel(logging.DEBUG)
        root.addHandler(sh)

logging.info("logger do app configurado; arquivo: %s", APP_LOG)


# Configurando o log
log_directory = os.path.join(os.getcwd(), 'logs')

# Cria o diretório se não existir
if not os.path.exists(log_directory):
    os.makedirs(log_directory)


current_date = datetime.now().strftime('%y-%m-%d')
log_name = f'log-envio-{current_date}.log'

log_file_path = os.path.join(log_directory,log_name)

logger = logging.getLogger('Log')
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_file_path)
console_handler = logging.StreamHandler()

formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)