"""
CRUD de Produto + validação dos campos custom (extras) contra FieldDefinition.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config.db import db
from config.logger import get_logger
from enums.fieldType import FieldType
from model.fieldDefinitionModel import FieldDefinition
from model.produtoModel import Produto
from utils.api_error import api_error

logger = get_logger(__name__)


def _as_decimal(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _coerce_value(tipo: str, raw):
    """Tenta coercer; devolve (valor, err_msg). err_msg None se ok."""
    if raw is None or raw == "":
        return None, None

    if tipo == FieldType.TEXTO.value:
        return str(raw), None

    if tipo == FieldType.NUMERO.value:
        try:
            return float(raw), None
        except (TypeError, ValueError):
            return None, "Valor numérico inválido"

    if tipo == FieldType.DATA.value:
        if isinstance(raw, str):
            try:
                date.fromisoformat(raw)
                return raw, None
            except ValueError:
                return None, "Data inválida (use YYYY-MM-DD)"
        return None, "Data inválida (use YYYY-MM-DD)"

    if tipo == FieldType.BOOLEANO.value:
        if isinstance(raw, bool):
            return raw, None
        if isinstance(raw, (int, float)):
            return bool(raw), None
        if isinstance(raw, str):
            v = raw.strip().lower()
            if v in {"1", "true", "t", "yes", "y", "on", "sim"}:
                return True, None
            if v in {"0", "false", "f", "no", "n", "off", "nao", "não"}:
                return False, None
        return None, "Valor booleano inválido"

    if tipo == FieldType.SELECT.value:
        return str(raw), None

    return None, f"Tipo desconhecido: {tipo}"


def validate_extras(extras: dict | None) -> tuple[dict, dict]:
    """
    Valida o dict `extras` contra as FieldDefinition ativas para 'produto'.
    Retorna (extras_normalizadas, erros). Campos não definidos são rejeitados.
    """
    extras = extras or {}
    if not isinstance(extras, dict):
        return {}, {"_extras": "Campo 'extras' deve ser objeto JSON"}

    defs = (FieldDefinition.query
            .filter(FieldDefinition.deleted == 0,
                    FieldDefinition.entity == "produto")
            .all())
    by_name = {d.nome: d for d in defs}

    err: dict = {}
    out: dict = {}

    # campos desconhecidos
    for k in extras.keys():
        if k not in by_name:
            err[k] = "Campo customizado não definido"

    # validação por definition
    for d in defs:
        raw = extras.get(d.nome)
        if (raw is None or raw == "") and d.obrigatorio:
            err[d.nome] = f"Campo '{d.label}' é obrigatório"
            continue
        if raw is None or raw == "":
            continue

        value, msg = _coerce_value(d.tipo, raw)
        if msg:
            err[d.nome] = msg
            continue

        if d.tipo == FieldType.SELECT.value and d.opcoes and value not in d.opcoes:
            err[d.nome] = f"Valor deve ser uma das opções: {d.opcoes}"
            continue

        out[d.nome] = value

    return out, err


def _normalize_codigo_barras(raw) -> Optional[str]:
    """Trim e remoção de espaços internos. Vazio vira None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # leitores podem enviar caracteres de controle; removemos espaços.
    s = "".join(s.split())
    return s[:64]


def _validate_payload(data: dict, *, partial: bool = False) -> tuple[dict, dict]:
    err: dict = {}
    out: dict = {}

    if "nome" in data or not partial:
        nome = (data.get("nome") or "").strip()
        if not nome:
            err["nome"] = "Campo 'nome' Obrigatório"
        out["nome"] = nome

    if "preco" in data or not partial:
        out["preco"] = _as_decimal(data.get("preco") or 0, "0")

    if "quantidade" in data or not partial:
        try:
            out["quantidade"] = int(data.get("quantidade") or 0)
        except (TypeError, ValueError):
            err["quantidade"] = "Campo 'quantidade' deve ser inteiro"

    if "codigo_barras" in data:
        out["codigo_barras"] = _normalize_codigo_barras(data.get("codigo_barras"))

    if "extras" in data or not partial:
        extras_norm, extras_err = validate_extras(data.get("extras"))
        if extras_err:
            err["extras"] = extras_err
        out["extras"] = extras_norm

    return out, err


class produtoService:

    @staticmethod
    def list_all(
        q: Optional[str] = None,
        page: int = 1,
        per_page: int = 24,
    ) -> Tuple[list, int]:
        try:
            base = Produto.query.filter(Produto.deleted == 0)
            if q:
                like = f"%{q.strip()}%"
                base = base.filter(or_(
                    Produto.nome.ilike(like),
                    Produto.codigo_barras.ilike(like),
                ))

            total = base.count()
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 100))

            rows = (base.order_by(Produto.id_produto.desc())
                        .offset((page - 1) * per_page)
                        .limit(per_page)
                        .all())
            return rows, total
        except SQLAlchemyError as e:
            logger.exception(f"Erro ao listar produtos {e}")
            return [], 0

    @staticmethod
    def get(id_produto: int):
        p = Produto.query.get(id_produto)
        if not p or p.deleted:
            return api_error(404, "Produto não encontrado")
        return p

    @staticmethod
    def get_by_codigo(codigo: str):
        codigo = _normalize_codigo_barras(codigo)
        if not codigo:
            return api_error(400, "Código vazio")
        p = (Produto.query
             .filter(Produto.deleted == 0, Produto.codigo_barras == codigo)
             .first())
        if not p:
            return api_error(404, "Produto não encontrado")
        return p

    @staticmethod
    def create(data: dict):
        payload, err = _validate_payload(data, partial=False)
        if err:
            return api_error(400, "Erro no payload", details=err)

        try:
            p = Produto(
                nome=payload["nome"],
                preco=payload["preco"],
                quantidade=payload.get("quantidade", 0),
                codigo_barras=payload.get("codigo_barras"),
                extras=payload.get("extras") or {},
            )
            db.session.add(p)
            db.session.commit()
            return p
        except IntegrityError as e:
            db.session.rollback()
            logger.warning(f"Código de barras duplicado: {e}")
            return api_error(409, "Já existe um produto com esse código de barras")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao criar produto {e}")
            return api_error(500, "Falha no banco ao criar produto", details=str(e))

    @staticmethod
    def update(id_produto: int, data: dict):
        p = Produto.query.get(id_produto)
        if not p or p.deleted:
            return api_error(404, "Produto não encontrado")

        payload, err = _validate_payload(data, partial=True)
        if err:
            return api_error(400, "Erro no payload", details=err)

        for attr in ("nome", "preco", "quantidade", "codigo_barras", "extras"):
            if attr in payload:
                setattr(p, attr, payload[attr])

        try:
            db.session.commit()
            return p
        except IntegrityError as e:
            db.session.rollback()
            logger.warning(f"Código de barras duplicado: {e}")
            return api_error(409, "Já existe um produto com esse código de barras")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao atualizar produto {e}")
            return api_error(500, "Falha no banco ao atualizar produto", details=str(e))

    @staticmethod
    def delete(id_produto: int):
        p = Produto.query.get(id_produto)
        if not p or p.deleted:
            return {"deleted": False, "status": 404, "error": "Produto não encontrado"}
        try:
            p.deleted = 1
            db.session.commit()
            return {"deleted": True}
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao deletar produto {e}")
            return {"deleted": False, "status": 500, "error": str(e)}

    @staticmethod
    def adjust_quantidade(id_produto: int, delta: int):
        """Soma `delta` (pode ser negativo) na quantidade. Não permite ficar < 0."""
        p = Produto.query.get(id_produto)
        if not p or p.deleted:
            return api_error(404, "Produto não encontrado")
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            return api_error(400, "Delta inválido")

        nova = (p.quantidade or 0) + delta
        if nova < 0:
            return api_error(400, "Quantidade resultante seria negativa")

        p.quantidade = nova
        try:
            db.session.commit()
            return p
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro ao ajustar quantidade {e}")
            return api_error(500, "Falha no banco ao ajustar quantidade", details=str(e))
