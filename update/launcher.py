# updater/launcher.py
import os, sys, subprocess, tempfile, json, urllib.request, hashlib, shutil, logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

APP_NAME = "Gestao"
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
INSTALL_DIR = APP_DIR if os.path.basename(APP_DIR).lower() == APP_NAME.lower() else os.path.dirname(APP_DIR)

VENV_DIR = os.path.join(INSTALL_DIR, "venv")
PYTHONW = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")
PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
MAIN = os.path.join(INSTALL_DIR, "main.py")
REQUIREMENTS = os.path.join(INSTALL_DIR, "requirements.txt")

LATEST_URL = "https://pedroquintas12.github.io/gestao/latest.json"

# ============ LOG: configurar pasta e arquivos ============
LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or ""
LOG_DIR = os.path.join(LOCALAPPDATA, APP_NAME, "logs") if LOCALAPPDATA else os.path.join(INSTALL_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LAUNCHER_LOG = os.path.join(LOG_DIR, "launcher.log")

def setup_logging(debug: bool = False):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # arquivo rotativo 1MB x 5
    fh = RotatingFileHandler(LAUNCHER_LOG, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    # opcional: ecoar para console quando em debug
    if debug:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        sh.setLevel(logging.DEBUG)
        logger.addHandler(sh)

    # redirecionar stdout/stderr para o log (caso algo escape)
    class StreamToLogger:
        def __init__(self, level):
            self.level = level
        def write(self, buf):
            buf = buf.strip()
            if buf:
                for line in buf.splitlines():
                    logging.getLogger().log(self.level, line)
        def flush(self): pass

    sys.stdout = StreamToLogger(logging.INFO)
    sys.stderr = StreamToLogger(logging.ERROR)

def log_exc(e: Exception, note: str = ""):
    logging.exception(f"{note} {type(e).__name__}: {e}")

# =========================================================

def run(cmd, cwd=None, check=True):
    logging.debug(f"Run: {cmd} (cwd={cwd})")
    return subprocess.run(cmd, cwd=cwd, check=check)

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_env():
    if not os.path.exists(PYTHON):
        raise RuntimeError("Ambiente virtual ausente. Reinstale o aplicativo.")
    try:
        run([PYTHON, "-m", "pip", "install", "--upgrade", "pip"])
        if os.path.exists(REQUIREMENTS):
            run([PYTHON, "-m", "pip", "install", "-r", REQUIREMENTS])
    except Exception as e:
        log_exc(e, "Falha ao atualizar pip/requirements:")

def migrate_env_to_appdata():
    try:
        appdata = os.environ.get("LOCALAPPDATA")
        if not appdata:
            return
        dst_dir = os.path.join(appdata, APP_NAME)
        os.makedirs(dst_dir, exist_ok=True)
        old_env = os.path.join(INSTALL_DIR, ".env")
        new_env = os.path.join(dst_dir, ".env")
        if os.path.exists(old_env) and not os.path.exists(new_env):
            shutil.copy2(old_env, new_env)
            os.remove(old_env)
            logging.info(f"Migrado .env para {new_env}")
    except Exception as e:
        log_exc(e, "Falha ao migrar .env:")

def maybe_update():
    try:
        with urllib.request.urlopen(LATEST_URL, timeout=10) as r:
            latest = json.load(r)
        win = latest.get("windows", {})
        url = win.get("installer_url")
        sha = (win.get("sha256") or "").lower()
        if not url:
            logging.info("Sem URL de update.")
            return
        tmpdir = tempfile.mkdtemp()
        inst = os.path.join(tmpdir, "setup.exe")
        logging.info(f"Baixando update: {url}")
        with urllib.request.urlopen(url, timeout=60) as resp, open(inst, "wb") as f:
            f.write(resp.read())
        if sha:
            got = file_sha256(inst).lower()
            if got != sha:
                logging.error(f"SHA inválido. Esperado={sha} obtido={got}")
                return
        subprocess.Popen([inst, "/VERYSILENT", "/NORESTART"], close_fds=True)
        logging.info("Update silencioso disparado.")
    except Exception as e:
        log_exc(e, "Falha no update:")

def run_app(use_console: bool = False):
    exe = PYTHON if use_console else PYTHONW
    if not os.path.exists(exe):
        raise RuntimeError(f"Python do venv não encontrado: {exe}")
    os.chdir(INSTALL_DIR)
    logging.info(f"Iniciando app com {'console' if use_console else 'background'}: {exe} {MAIN}")
    subprocess.Popen([exe, MAIN], close_fds=True)

if __name__ == "__main__":
    # modos:
    #   --debug  -> ativa console + logs mais verbosos
    #   --nocheck -> não checa update
    debug = ("--debug" in sys.argv) or (os.environ.get("GESTAO_DEBUG") == "1")
    setup_logging(debug)
    logging.info(f"Launcher iniciado. INSTALL_DIR={INSTALL_DIR}")

    try:
        migrate_env_to_appdata()
        if "--nocheck" not in sys.argv:
            maybe_update()
        ensure_env()
        run_app(use_console=debug)  # em debug, abre com console (python.exe)
    except Exception as e:
        log_exc(e, "Falha crítica no launcher:")
        # em caso de crash, mostra o log rapidamente
        try:
            if os.path.exists(LAUNCHER_LOG):
                subprocess.Popen(["notepad.exe", LAUNCHER_LOG])
        except:
            pass
        # Fallback com console
        subprocess.Popen(["cmd.exe", "/c", f'echo {e} & echo Veja o log em "{LAUNCHER_LOG}" & pause'])
