# app/config.py (ou no topo do main.py)
import os
from pathlib import Path

def _str2bool(v: str, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def load_env_and_config():
    # 1) Local do .env em produção
    appdata = os.environ.get("LOCALAPPDATA")
    prod_env = Path(appdata) / "Gestao" / ".env" if appdata else None

    # 2) Local do .env em desenvolvimento (ajuste se seu main.py não está na raiz)
    repo_root = Path(__file__).resolve().parent
    # se este arquivo estiver em app/config.py, repo_root.parent.parent; ajuste conforme sua estrutura
    while repo_root.name not in {"gestao", "Gestao"} and repo_root.parent != repo_root:
        repo_root = repo_root.parent
    dev_env = repo_root / ".env"

    # 3) Carrega .env (ordem: override -> AppData -> raiz do repo)
    override = os.environ.get("GESTAO_ENV")
    candidates = [Path(override)] if override else []
    if prod_env:
        candidates.append(prod_env)
    candidates.append(dev_env)

    try:
        from dotenv import load_dotenv
        for p in candidates:
            if p and p.exists():
                load_dotenv(p, override=False)
                break
    except Exception:
        pass  # segue sem quebrar se faltar python-dotenv

    # 4) Monta config final
    cfg = {}
    cfg["TEMPLATE_FOLDER"] = os.getenv("TEMPLATE_FOLDER", "views")
    cfg["STATIC_FOLDER"]   = os.getenv("STATIC_FOLDER", "public")
    cfg["SECRET_KEY"]      = os.getenv("SECRET_KEY", "change-me")

    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///gestor.db")

    # Expande placeholder %LOCALAPPDATA% se for usado no .env
    if "%LOCALAPPDATA%" in uri and appdata:
        uri = uri.replace("%LOCALAPPDATA%", appdata.replace("\\", "/"))

    # Se for SQLite relativo (ex.: sqlite:///gestor.db), envia para %LocalAppData%\Gestao\gestor.db
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        # extrai nome do arquivo relativo
        rel = uri[len("sqlite:///"):]
        if not (":" in rel or rel.startswith("/")) and appdata:
            data_dir = Path(appdata) / "Gestao"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = (data_dir / rel).resolve()
            uri = f"sqlite:///{db_path.as_posix()}"

    cfg["SQLALCHEMY_DATABASE_URI"] = uri
    cfg["SQLALCHEMY_TRACK_MODIFICATIONS"] = _str2bool(os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "false"))
    cfg["SEED_ON_STARTUP"] = _str2bool(os.getenv("SEED_ON_STARTUP", "false"))

    # 5) Resolve caminhos absolutos das pastas de template/static com base no diretório de instalação
    install_dir = Path(__file__).resolve().parent  # ajuste se main.py estiver na raiz
    tpl = (install_dir / cfg["TEMPLATE_FOLDER"]).resolve()
    stc = (install_dir / cfg["STATIC_FOLDER"]).resolve()
    cfg["TEMPLATE_FOLDER_ABS"] = str(tpl)
    cfg["STATIC_FOLDER_ABS"]   = str(stc)

    return cfg
