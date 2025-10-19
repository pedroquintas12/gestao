from flask import Blueprint
from config.decorators import login_required
from service.auth import auth

auth_bp = Blueprint("auth_bp", __name__)

auth_bp.get("/login")(auth.login_form)

auth_bp.post("/login")(auth.login)

auth_bp.get("/me")(login_required(auth.me))

auth_bp.get("/logout")(auth.logout)