# config/__init__.py
import os
from pathlib import Path

def _str2bool(v: str, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def _find_install_root(anchor_name: str = "config", max_hops: int = 6) -> Path:
    """
    Sobe diretórios a partir deste arquivo até achar a pasta 'config'
    e retorna o PAI dela (a raiz onde ficam views/ e public/).
    """
    here = Path(__file__).resolve()
    p = here.parent
    hops = 0
    while p.parent != p and hops <= max_hops:
        if p.name.lower() == anchor_name.lower():
            return p.parent
        p = p.parent
        hops += 1
    # fallback seguro: um nível acima de config/__init__.py
    return Path(__file__).resolve().parent.parent

def _load_first_env(candidates):
    """Carrega o primeiro arquivo .env existente dentre os candidatos (sem quebrar se faltar python-dotenv)."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for p in candidates:
        try:
            if p and Path(p).exists():
                load_dotenv(p, override=False)
                return
        except Exception:
            # segue tentando os demais
            pass

def load_env_and_config():
    # ===== 1) Carregar .env (ordem: override -> AppData -> raiz) =====
    appdata = os.environ.get("LOCALAPPDATA")
    install_root = _find_install_root(anchor_name="config")

    # Candidatos produção (AppData\Gestao)
    prod_candidates = []
    if appdata:
        prod_dir = Path(appdata) / "Gestao"
        prod_candidates = [
            prod_dir / ".env",          # alvo final
            prod_dir / "env.example",   # fallback
            prod_dir / "env.exemple",   # fallback (grafia alternativa)
        ]

    # Candidatos desenvolvimento (raiz do app)
    dev_candidates = [
        install_root / ".env",
        install_root / "env.example",
        install_root / "env.exemple",
    ]

    # Override absoluto via variável (ex.: GESTAO_ENV=C:\path\custom.env)
    override = os.environ.get("GESTAO_ENV")
    candidates = [Path(override)] if override else []
    candidates += prod_candidates + dev_candidates

    _load_first_env(candidates)

    # ===== 2) Configs base =====
    cfg = {}
    cfg["TEMPLATE_FOLDER"] = os.getenv("TEMPLATE_FOLDER", "views")
    cfg["STATIC_FOLDER"]   = os.getenv("STATIC_FOLDER", "public")
    cfg["SECRET_KEY"]      = os.getenv("SECRET_KEY", "change-me")

    # ===== 3) Banco =====
    uri = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///gestor.db")
    if "%LOCALAPPDATA%" in uri and appdata:
        uri = uri.replace("%LOCALAPPDATA%", appdata.replace("\\", "/"))
    # sqlite:///arquivo_relativo -> envia para %LOCALAPPDATA%\Gestao\arquivo_relativo
    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        rel = uri[len("sqlite:///"):]
        if not (":" in rel or rel.startswith("/")) and appdata:
            data_dir = Path(appdata) / "Gestao"
            data_dir.mkdir(parents=True, exist_ok=True)
            uri = f"sqlite:///{(data_dir / rel).resolve().as_posix()}"
    cfg["SQLALCHEMY_DATABASE_URI"] = uri
    cfg["SQLALCHEMY_TRACK_MODIFICATIONS"] = _str2bool(os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "false"))
    cfg["SEED_ON_STARTUP"] = _str2bool(os.getenv("SEED_ON_STARTUP", "false"))

    # ===== 4) Resolve diretórios absolutos com overrides opcionais =====
    tpl_abs_env = os.getenv("TEMPLATE_FOLDER_ABS", "").strip()
    stc_abs_env = os.getenv("STATIC_FOLDER_ABS", "").strip()

    tpl = Path(tpl_abs_env) if tpl_abs_env else (install_root / cfg["TEMPLATE_FOLDER"])
    stc = Path(stc_abs_env) if stc_abs_env else (install_root / cfg["STATIC_FOLDER"])

    tpl = tpl.resolve()
    stc = stc.resolve()

    cfg["INSTALL_ROOT"]        = str(install_root)
    cfg["TEMPLATE_FOLDER_ABS"] = str(tpl)
    cfg["STATIC_FOLDER_ABS"]   = str(stc)

    # ===== 5) Logs de diagnóstico (não quebram execução) =====
    try:
        from config.logger import logger
        
        logger.info("INSTALL_ROOT=%s", cfg["INSTALL_ROOT"])
        logger.info("TEMPLATES  =%s", cfg["TEMPLATE_FOLDER_ABS"])
        logger.info("STATIC     =%s", cfg["STATIC_FOLDER_ABS"])
        logger.info("DB URI     =%s", cfg["SQLALCHEMY_DATABASE_URI"])

        missing = []
        if not Path(cfg["TEMPLATE_FOLDER_ABS"]).exists():
            missing.append(f"Templates não encontrados em: {cfg['TEMPLATE_FOLDER_ABS']}")
        if not Path(cfg["STATIC_FOLDER_ABS"]).exists():
            missing.append(f"Static não encontrado em: {cfg['STATIC_FOLDER_ABS']}")
        if missing:
            logger.error("Caminhos inválidos: %s", " | ".join(missing))
    except Exception:
        pass

    return cfg
