# config/logger.py
import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

APP_NAME = "Gestao"

def _resolve_log_dir() -> Path:
    # Windows: LOCALAPPDATA; fallback: ~/.gestao/logs
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / f".{APP_NAME.lower()}")
    p = Path(base) / APP_NAME / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p

LOG_DIR = _resolve_log_dir()
APP_LOG_PATH = LOG_DIR / "app.log"
ERR_LOG_PATH = LOG_DIR / "app_error.log"

class MaxLevelFilter(logging.Filter):
    """Permite apenas registros com level <= max_level (exclui os superiores)."""
    def __init__(self, max_level: int):
        super().__init__()
        self.max_level = max_level
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level

def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def configure_logging() -> logging.Logger:
    """
    Configura apenas uma vez. Retorna um logger de aplicação.
    - app.log: INFO e WARNING
    - app_error.log: ERROR e CRITICAL
    - console: DEBUG+ quando GESTAO_DEBUG=1
    """
    root = logging.getLogger()
    if root.handlers:  # já configurado
        return logging.getLogger(APP_NAME)

    root.setLevel(logging.DEBUG)  # mantenha baixo; handlers filtram

    fmt = _build_formatter()

    # Handler principal (INFO e WARNING) com rotação
    info_fh = RotatingFileHandler(
        APP_LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8", delay=True
    )
    info_fh.setLevel(logging.INFO)
    info_fh.setFormatter(fmt)
    info_fh.addFilter(MaxLevelFilter(logging.WARNING))  # até WARNING (exclui ERROR+)

    # Handler de erros (ERROR+)
    err_fh = RotatingFileHandler(
        ERR_LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8", delay=True
    )
    err_fh.setLevel(logging.ERROR)
    err_fh.setFormatter(fmt)

    root.addHandler(info_fh)
    root.addHandler(err_fh)

    # Console opcional (útil em dev/.bat). Só ativa quando GESTAO_DEBUG=1
    if os.environ.get("GESTAO_DEBUG") == "1":
        stream = getattr(sys, "__stdout__", None) or getattr(sys, "__stderr__", None)
        if stream:
            sh = logging.StreamHandler(stream=stream)
            sh.setLevel(logging.DEBUG)
            sh.setFormatter(fmt)
            root.addHandler(sh)

    app_logger = logging.getLogger(APP_NAME)
    app_logger.propagate = True  # usa handlers do root
    app_logger.debug("Logging configurado. app.log=%s | app_error.log=%s", APP_LOG_PATH, ERR_LOG_PATH)
    return app_logger

# Configura ao importar
logger = configure_logging()

def get_logger(name: str | None = None) -> logging.Logger:
    """
    Use nas demais modules: 
        from config.logger import get_logger
        log = get_logger(__name__)
    """
    log = logging.getLogger(name or APP_NAME)
    # evitar duplicação se alguém adicionar handler próprio por engano:
    if log is not logging.getLogger():  # não é o root
        log.propagate = True  # deixa o root escrever nos arquivos
        log.setLevel(logging.DEBUG)
    return log
