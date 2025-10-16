# errors.py
from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
import traceback


class ValidationError(ValueError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field

def _json_error(error: str, message: str, status: int, **extra):
    payload = {"error": error, "message": message, "status": status}
    payload.update({k: v for k, v in extra.items() if v is not None})
    return jsonify(payload), status

def register_error_handlers(app):
    # Validation do domínio
    @app.errorhandler(ValidationError)
    def _handle_validation(err: ValidationError):
        return _json_error("validation_error", str(err), 400, field=getattr(err, "field", None))

    # HTTPException (404, 405, 413, etc) -> JSON
    @app.errorhandler(HTTPException)
    def _handle_http(err: HTTPException):
        # err.description já traz a mensagem “bonita”
        return _json_error("http_error", err.description, err.code or 500)

    # Erros de banco (padroniza em 500; logs mantêm detalhes)
    @app.errorhandler(SQLAlchemyError)
    def _handle_sqlalchemy(err: SQLAlchemyError):
        current_app.logger.exception("SQLAlchemyError")
        return _json_error("database_error", "Erro de banco de dados.", 500)

    # Qualquer outro erro não mapeado
    @app.errorhandler(Exception)
    def _handle_generic(err: Exception):
        current_app.logger.exception("Unhandled exception")
        # Em dev, opcional: expor um id/stack curto
        if app.debug or app.config.get("EXPOSE_TRACE_IN_ERRORS"):
            tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))
            return _json_error("internal_error", "Erro interno do servidor.", 500, trace=tb[-5000:])
        return _json_error("internal_error", "Erro interno do servidor.", 500)
