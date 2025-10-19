from functools import wraps
from flask import jsonify, session


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('is_admin') != True:
            return jsonify({"error":"Você não tem permissão para acessar essa página!"})  
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") :
            return jsonify({"error":"Você não esta logado para acessar essa pagina"})  
        return f(*args, **kwargs)
    return decorated_function