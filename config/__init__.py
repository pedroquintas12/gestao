import os
from dotenv import load_dotenv

# raiz do projeto (um nível acima de config/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, os.getenv("ENV_FILE", ".env")))

def _abs(p: str | None, default_rel: str) -> str:
    p = p or default_rel
    return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)

class Config:
    TEMPLATE_FOLDER = _abs(os.getenv("TEMPLATE_FOLDER", "views"), "views")
    STATIC_FOLDER   = _abs(os.getenv("STATIC_FOLDER",   "public"), "public")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite:///{os.path.join(BASE_DIR,'petgo.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    SEED_ON_STARTUP = os.getenv("SEED_ON_STARTUP", "false").lower() == "true"

config = Config()
