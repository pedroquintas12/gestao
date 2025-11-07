from flask import Blueprint, render_template, g

from config.decorators import login_required,admin_required
from model.companieModel import companie
try:
    from config.version import __version__ as CURRENT_VERSION
except Exception:
    CURRENT_VERSION = "1.0.0"

front_bp = Blueprint('front',__name__)

def get_company_ctx():
    """
    Busca a empresa dentro do application/request context.
    Usa cache em g por requisição para não repetir a query.
    """
    if getattr(g, "_company_ctx", None) is not None:
        return g._company_ctx

    obj = companie.query.first()
    ctx = obj.to_dict() if obj else {"nome": "Gestão", "logo": None}
    g._company_ctx = ctx
    return ctx

@front_bp.route("/")
@login_required
def index():
    ctx = get_company_ctx()
    return render_template(
        "index.html",
        version=CURRENT_VERSION,
        logo=ctx.get("logo"),
        companie=ctx.get("nome"),
    )

@front_bp.route("/admin")
@admin_required
def admin():
    ctx = get_company_ctx()
    return render_template(
        "admin.html",
        version=CURRENT_VERSION,
        logo=ctx.get("logo"),
        companie=ctx.get("nome"),
    )

@front_bp.route('/cadastroCompanie')
def cadastro_companie():
    return render_template('cadastroCompanie.html')