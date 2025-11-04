import logging
from logging.handlers import RotatingFileHandler
import os, sys, subprocess, tempfile, json, urllib.request, hashlib, shutil, traceback
from pathlib import Path

APP_NAME = "Gestao"

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
INSTALL_DIR = APP_DIR if os.path.basename(APP_DIR).lower() == APP_NAME.lower() else os.path.dirname(APP_DIR)

VENV_DIR     = os.path.join(INSTALL_DIR, "venv")
PYTHONW      = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")
PYTHON       = os.path.join(VENV_DIR, "Scripts", "python.exe")
MAIN         = os.path.join(INSTALL_DIR, "main.py")
REQUIREMENTS = os.path.join(INSTALL_DIR, "requirements.txt")  # <— use SEMPRE este

LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or ""
LOG_DIR      = os.path.join(LOCALAPPDATA, APP_NAME, "logs") if LOCALAPPDATA else os.path.join(INSTALL_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LAUNCHER_LOG = os.path.join(LOG_DIR, "launcher.log")
PIP_LOG      = os.path.join(LOG_DIR, "pip_install.log")

LATEST_URL   = "https://raw.githubusercontent.com/pedroquintas12/gestao/refs/tags/V0.1.2/latest.json"

def setup_logging(debug: bool = False):
    """Somente arquivo. Em binário --noconsole, stdout pode ser None."""
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = RotatingFileHandler(LAUNCHER_LOG, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG if debug else logging.INFO)
    root.addHandler(fh)

def log_fatal_and_show():
    try:
        with open(LAUNCHER_LOG, "a", encoding="utf-8") as f:
            f.write("\n=== FATAL ===\n")
            traceback.print_exc(file=f)
        if os.path.exists(LAUNCHER_LOG):
            subprocess.Popen(["notepad.exe", LAUNCHER_LOG])
    except:
        pass
    # fallback com console pausado
    try:
        subprocess.Popen(["cmd.exe", "/c", "echo Falha ao iniciar. Veja o log e pressione uma tecla... & pause"])
    except:
        pass

def run(cmd, cwd=None, check=True):
    logging.debug(f"Run: {cmd} (cwd={cwd})")
    return subprocess.run(cmd, cwd=cwd, check=check)

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def log(msg):
    try:
        with open(LAUNCHER_LOG, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except:
        pass

def ensure_env():
    """
    Garante o venv e instala requirements.
    Escreve toda a saída do pip em PIP_LOG.
    Abre o Notepad se o pip falhar.
    Se GESTAO_SKIP_PIP=1, só valida o venv.
    """
    if not os.path.exists(PYTHON):
        raise RuntimeError(f"venv ausente: {PYTHON}")

    if os.environ.get("GESTAO_SKIP_PIP") == "1":
        log("[pip] skip solicitado por GESTAO_SKIP_PIP=1")
        return

    # 1) upgrade do pip (não bloqueia se falhar)
    try:
        with open(PIP_LOG, "a", encoding="utf-8") as f:
            f.write("\n=== pip upgrade (pip -U pip) ===\n")
            p = subprocess.run(
                [PYTHON, "-m", "pip", "install", "-U", "pip",
                 "--disable-pip-version-check", "--no-input", "--no-color"],
                stdout=f, stderr=subprocess.STDOUT, text=True
            )
            f.write(f"\n[exitcode] {p.returncode}\n")
    except Exception:
        log("[pip] falha ao rodar upgrade:\n" + traceback.format_exc())

    # 2) instalar requirements.txt
    if os.path.exists(REQUIREMENTS):
        with open(PIP_LOG, "a", encoding="utf-8") as f:
            f.write("\n=== pip install -r requirements.txt ===\n")
            p = subprocess.run(
                [PYTHON, "-m", "pip", "install", "-r", REQUIREMENTS,
                 "--disable-pip-version-check", "--no-input", "--no-color",
                 f"--log={PIP_LOG}"],
                stdout=f, stderr=subprocess.STDOUT, text=True
            )
            f.write(f"\n[exitcode] {p.returncode}\n")

        if p.returncode != 0:
            log("[pip] install retornou erro; abrindo log…")
            try:
                subprocess.Popen(["notepad.exe", PIP_LOG])
            finally:
                raise RuntimeError("Falha ao instalar dependencias. Veja pip_install.log")
    else:
        log(f"[pip] {REQUIREMENTS} não encontrado; pulando.")


def migrate_env_to_appdata():
    try:
        if not LOCALAPPDATA:
            return
        dst_dir = os.path.join(LOCALAPPDATA, APP_NAME)
        os.makedirs(dst_dir, exist_ok=True)
        old_env = os.path.join(INSTALL_DIR, ".env")
        new_env = os.path.join(dst_dir, ".env")
        if os.path.exists(old_env) and not os.path.exists(new_env):
            shutil.copy2(old_env, new_env)
            os.remove(old_env)
            logging.info(f"Migrado .env para {new_env}")
    except Exception:
        logging.exception("Falha ao migrar .env:")

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
    except Exception:
        logging.exception("Falha no update:")

def run_app():
    exe = PYTHONW  # sem console
    if not os.path.exists(exe):
        raise RuntimeError(f"Python do venv não encontrado: {exe}")
    os.chdir(INSTALL_DIR)
    logging.info(f"Iniciando app: {exe} {MAIN}")
    subprocess.Popen([exe, MAIN], close_fds=True)

if __name__ == "__main__":
    try:
        # NÃO crie StreamHandler (sem console). Log só em arquivo.
        setup_logging(debug=False)
        logging.info(f"Launcher iniciado. INSTALL_DIR={INSTALL_DIR}")
        migrate_env_to_appdata()
        maybe_update()
        ensure_env()
        run_app()
    except Exception:
        log_fatal_and_show()
