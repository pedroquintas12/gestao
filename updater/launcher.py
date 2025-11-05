import logging
from logging.handlers import RotatingFileHandler
import os, sys, subprocess, tempfile, json, urllib.request, hashlib, shutil, traceback, ctypes, time
from pathlib import Path
from datetime import datetime, timedelta

APP_NAME = "Gestao"

# ──────────────── Caminhos principais ─────────────────
APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
INSTALL_DIR = APP_DIR if os.path.basename(APP_DIR).lower() == APP_NAME.lower() else os.path.dirname(APP_DIR)

VENV_DIR     = os.path.join(INSTALL_DIR, "venv")
PYTHONW      = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")
PYTHON       = os.path.join(VENV_DIR, "Scripts", "python.exe")
MAIN         = os.path.join(INSTALL_DIR, "main.py")
REQUIREMENTS = os.path.join(INSTALL_DIR, "requirements.txt")

LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or ""
APPDATA_DIR  = Path(LOCALAPPDATA, APP_NAME) if LOCALAPPDATA else Path(INSTALL_DIR)

LOG_DIR      = APPDATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LAUNCHER_LOG = LOG_DIR / "launcher.log"
PIP_LOG      = LOG_DIR / "pip_install.log"

VERSION_FILE = Path(INSTALL_DIR) / "version.txt"
STATE_FILE   = APPDATA_DIR / "update_state.json"

LATEST_URL   = "https://raw.githubusercontent.com/pedroquintas12/gestao/refs/heads/main/latest.json"

OWNER = "pedroquintas12"
REPO  = "gestao"
GITHUB_LATEST_API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"

UPDATE_COOLDOWN_HOURS = int(os.environ.get("GESTAO_UPDATE_CHECK_INTERVAL_HOURS", "24"))

#──────────────────── Logging ────────────────────

def setup_logging(debug: bool = False):
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
        subprocess.Popen(["notepad.exe", str(LAUNCHER_LOG)])
    except:
        pass
    subprocess.Popen(["cmd.exe", "/c", "echo Falha ao iniciar. Veja o log & pause"])


#──────────────────── Util ──────────────────────

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, cwd=None, check=True):
    logging.debug(f"Run: {cmd} (cwd={cwd})")
    return subprocess.run(cmd, cwd=cwd, check=check)

def _msg_yes_no(title, text):
    IDYES = 6
    return ctypes.windll.user32.MessageBoxW(0, text, title, 0x4 | 0x40 | 0x40000) == IDYES

def _load_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except:
        pass
    return {}

def _save_state(d):
    try:
        STATE_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logging.exception("Falha ao salvar STATE_FILE")

def _parse_version(s):
    parts = []
    for tok in str(s).split("."):
        n = "".join(ch for ch in tok if ch.isdigit())
        if n == "": break
        parts.append(int(n))
    return tuple(parts) if parts else (0,)

def _get_current_version():
    try:
        if VERSION_FILE.exists():
            v = VERSION_FILE.read_text(encoding="utf-8").strip()
            if v: return v
    except:
        pass
    return ""

def _is_newer(remote, local):
    if not remote: return False
    if not local:  return True
    return _parse_version(remote) > _parse_version(local)

def _now_iso():
    return datetime.utcnow().isoformat() + "Z"

def _too_soon(last_iso, hours):
    try:
        last = datetime.fromisoformat(last_iso.replace("Z", ""))
        return datetime.utcnow() - last < timedelta(hours=hours)
    except:
        return False

#──────────────────── Update Check ──────────────────────

def _github_latest_asset_url(ext=".exe"):
    with urllib.request.urlopen(GITHUB_LATEST_API, timeout=15) as r:
        data = json.load(r)
    tag = data.get("tag_name") or ""
    assets = data.get("assets") or []
    url = None
    for a in assets:
        name = (a.get("name") or "").lower()
        if name.endswith(ext):
            url = a.get("browser_download_url")
            break
    notes = data.get("body") or ""
    return tag, url, notes

def _latest_from_fallback():
    with urllib.request.urlopen(LATEST_URL, timeout=10) as r:
        latest = json.load(r)
    tag = str(latest.get("version") or "")
    win = latest.get("windows", {}) or {}
    url = win.get("installer_url")
    sha = (win.get("sha256") or "").lower()
    mandatory = bool(latest.get("mandatory", False))
    notes = latest.get("notes") or ""
    return tag, url, sha, mandatory, notes

def maybe_prompt_update():
    auto = os.environ.get("GESTAO_AUTO_UPDATE", "").strip() in {"1", "true", "on", "yes"}
    state = _load_state()
    last_tag = state.get("last_seen_tag", "")
    last_check = state.get("last_check_iso", "")
    current = _get_current_version()

    if last_check and _too_soon(last_check, UPDATE_COOLDOWN_HOURS):
        logging.info("Update: cooldown ativo, ignorando.")
        return

    tag, url, notes, sha_expected, mandatory = None, None, "", "", False
    try:
        tag, url, notes = _github_latest_asset_url(".exe")
        if not url:
            logging.info("Update: nenhum .exe no release, tentando latest.json")
            tag, url, sha_expected, mandatory, notes = _latest_from_fallback()
    except Exception:
        logging.exception("Update: falha ao consultar releases")
        state.update({"last_check_iso": _now_iso()})
        _save_state(state)
        return

    if not url:
        logging.info("Update: nenhuma URL encontrada.")
        state.update({"last_check_iso": _now_iso()})
        _save_state(state)
        return

    if tag == last_tag and _too_soon(last_check, UPDATE_COOLDOWN_HOURS):
        logging.info("Update: já notificado sobre este tag recentemente.")
        return

    if tag and current and not _is_newer(tag.lstrip("vV"), current):
        logging.info("Update: remoto não é maior que local.")
        state.update({"last_check_iso": _now_iso(), "last_seen_tag": tag})
        _save_state(state)
        return

    # Popup
    msg = f"Uma atualização do {APP_NAME} está disponível.\n\n"
    if current: msg += f"Sua versão: {current}\n"
    if tag:     msg += f"Nova versão: {tag}\n"
    if notes:
        msg += "\nNovidades:\n" + "\n".join(notes.splitlines()[:8]) + "\n"
    msg += "\nDeseja baixar e instalar agora?"

    if auto:
        agreed = True
        logging.info("Update: AUTO=1, atualizando sem perguntar.")
    else:
        agreed = _msg_yes_no(f"{APP_NAME} – Atualização disponível", msg)

    state.update({"last_check_iso": _now_iso(), "last_seen_tag": tag})
    _save_state(state)

    if not agreed:
        logging.info("Update: usuário recusou.")
        return

    try:
        tmpdir = tempfile.mkdtemp()
        inst = os.path.join(tmpdir, "setup.exe")
        logging.info(f"Baixando update: {url}")
        with urllib.request.urlopen(url, timeout=60) as resp, open(inst, "wb") as f:
            shutil.copyfileobj(resp, f)

        if sha_expected:
            got = file_sha256(inst).lower()
            if got != sha_expected:
                logging.error(f"SHA inválido. Esperado={sha_expected}, obtido={got}")
                _msg_yes_no(f"{APP_NAME} – Erro de integridade",
                            "Falha ao validar o instalador baixado.\nAtualização cancelada.")
                return

        subprocess.Popen([inst, "/VERYSILENT", "/NORESTART"], close_fds=True)
        logging.info("Update disparado.")
    except Exception:
        logging.exception("Erro no update")


#──────────────────── Venv + pip ──────────────────────

def ensure_env():
    if not os.path.exists(PYTHON):
        run([sys.executable, "-m", "venv", VENV_DIR], check=True)

    if os.environ.get("GESTAO_SKIP_PIP") == "1":
        logging.info("PIP ignorado por GESTAO_SKIP_PIP=1")
        return

    try:
        with open(PIP_LOG, "a", encoding="utf-8") as f:
            f.write("\n=== pip upgrade ===\n")
            p = subprocess.run([PYTHON, "-m", "pip", "install", "-U", "pip",
                                "--disable-pip-version-check", "--no-input", "--no-color"],
                               stdout=f, stderr=subprocess.STDOUT, text=True)
            f.write(f"\n[exit] {p.returncode}\n")
    except Exception:
        logging.exception("Falha upgrade pip")

    if os.path.exists(REQUIREMENTS):
        with open(PIP_LOG, "a", encoding="utf-8") as f:
            f.write("\n=== pip install -r requirements ===\n")
            p = subprocess.run([PYTHON, "-m", "pip", "install", "-r", REQUIREMENTS,
                                "--disable-pip-version-check", "--no-input", "--no-color",
                                f"--log={PIP_LOG}"],
                               stdout=f, stderr=subprocess.STDOUT, text=True)
            f.write(f"\n[exit] {p.returncode}\n")

        if p.returncode != 0:
            subprocess.Popen(["notepad.exe", str(PIP_LOG)])
            raise RuntimeError("Falha ao instalar dependências. Veja pip_install.log")


#──────────────────── Execução do App ──────────────────────

def run_app():
    exe = PYTHONW
    if not os.path.exists(exe):
        raise RuntimeError(f"Python do venv não encontrado: {exe}")
    os.chdir(INSTALL_DIR)
    logging.info(f"Iniciando app: {exe} {MAIN}")
    subprocess.Popen([exe, MAIN], close_fds=True)


#──────────────────── MAIN ──────────────────────

if __name__ == "__main__":
    try:
        setup_logging(debug=False)
        logging.info(f"Launcher iniciado. INSTALL_DIR={INSTALL_DIR}")
        maybe_prompt_update()
        ensure_env()
        run_app()
    except Exception:
        log_fatal_and_show()
