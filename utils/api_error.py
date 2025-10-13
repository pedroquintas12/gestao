import traceback
from flask import current_app, jsonify


def api_error(status:int, error:str, cause:str=None, details:dict=None, exc:Exception=None):
    payload = {"error": error}
    if cause: payload["cause"] = cause
    if details: payload["details"] = details
    if exc:
        current_app.logger.exception(f"{error}: {exc}")
        # Exibe stack só em debug:
        if current_app and current_app.debug:
            payload["trace"] = traceback.format_exc()
    return jsonify(payload), status