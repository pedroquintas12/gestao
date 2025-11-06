# errors.py
from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
import traceback
from config.logger import get_logger
logger = get_logger(__name__)

class ValidationError(ValueError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field

def _json_error(code: str, message: str, status: int, extra=None):
    payload = {
        "error": code,
        "message": message,
        "status": status,
    }
    if extra is not None:
        # garanta que é serializável
        try:
            payload["extra"] = str(extra)
        except Exception:
            payload["extra"] = repr(extra)
    return jsonify(payload), status

def register_error_handlers(app):
    # Validation do domínio
    @app.errorhandler(ValidationError)
    def _handle_validation(err: ValidationError):
        logger.exception("ValidationError: %s", err)
        return _json_error("validation_error", str(err), 400, field=getattr(err, "field", None))

    # HTTPException (404, 405, 413, etc) -> JSON
    @app.errorhandler(HTTPException)
    def _handle_http(err: HTTPException):
        logger.exception("HTTPException: %s", err)
        return _json_error("http_error", err.description, err.code or 500)

    # Erros de banco (padroniza em 500; logs mantêm detalhes)
    @app.errorhandler(SQLAlchemyError)
    def _handle_sqlalchemy(err: SQLAlchemyError):
        logger.exception("SQLAlchemyError: %s", err)
        return _json_error("database_error", "Erro de banco de dados.", 500)

    # Qualquer outro erro não mapeado
    @app.errorhandler(Exception)
    def _handle_generic(err):
        logger.exception("Unhandled Exception: %s", err)
        return _json_error("internal_error", "Erro interno do servidor.", 500, extra=str(err))
