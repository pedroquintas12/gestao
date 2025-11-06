# services/vendaService.py
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from flask import make_response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DataError, InvalidRequestError

from config.db import db
from config.logger import get_logger  
from model.companieModel import companie
from utils.api_error import api_error
from model.vendaModel import venda as Venda, VendaItem
from model.servicoModel import servico as Servico
from model.clienteModel import cliente as Cliente
from model.veiculoModel import veiculo as Veiculo
from model.caixaModel import caixa_lancamento as Caixa
from enums.forma_pagamentoEnum import FormaPagamento

logger = get_logger(__name__)

def _num(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def _coerce_to_dt_start_of_day(v):
    """Aceita datetime|date|str|None e devolve datetime na 00:00."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, time.min)
    if isinstance(v, str):
        try:
            d = date.fromisoformat(v)
        except ValueError as e:
            raise TypeError(f"Data inválida (use YYYY-MM-DD): {v}") from e
        return datetime.combine(d, time.min)
    raise TypeError(f"Tipo de data não suportado: {type(v)}")


def _as_decimal(value, default="0"):
    """Converte com segurança para Decimal."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _forma_pagamento_or_default(raw, fallback="PIX"):
    """Valida a forma de pagamento contra o Enum; usa fallback se inválida ou vazia."""
    if not raw:
        return fallback
    try:
        if isinstance(raw, str):
            raw = raw.strip().upper().replace(" ", "_")
            if raw in FormaPagamento.__members__:
                return raw
        if isinstance(raw, FormaPagamento):
            return raw.name
    except Exception:
        pass
    return fallback


class vendaService:

    @staticmethod
    def _recalc_total_sql(v: Venda) -> None:
        """
        Recalcula o total somando direto no banco (robusto contra coleção desatualizada).
        """
        soma = db.session.query(
            func.coalesce(
                func.sum(
                    (VendaItem.preco_unit * VendaItem.quantidade) - VendaItem.desconto
                ),
                0
            )
        ).filter(VendaItem.id_venda == v.id_venda).scalar()
        v.total = _as_decimal(soma, "0")

    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}
        id_cliente = data.get("id_cliente")
        id_veiculo = data.get("id_veiculo")
        descricao = data.get("descricao")

        if not id_cliente:
            err["id_cliente"] = "Campo 'id_cliente' Obrigatório"
        if not id_veiculo:
            err["id_veiculo"] = "Campo 'id_veiculo' Obrigatório"

        out.update({"id_cliente": id_cliente, "id_veiculo": id_veiculo, "descricao": descricao})
        return out, err

    @staticmethod
    def create(data: dict):
        try:
            payload, err = vendaService.valid_payload(data)
            if err:
                return api_error(400, "Erro no payload", details=err)

            if not Cliente.query.get(payload["id_cliente"]):
                return api_error(404, "Cliente inválido")
            if not Veiculo.query.get(payload["id_veiculo"]):
                return api_error(404, "Veículo inválido")

            v = Venda(
                id_cliente=payload["id_cliente"],
                id_veiculo=payload["id_veiculo"],
                descricao=payload.get("descricao"),
                status="EM_ANDAMENTO",
                pagamento=FormaPagamento.NÃO_PAGO.name,
                total=0
            )
            db.session.add(v)
            db.session.commit()
            return v
        except (IntegrityError, DataError) as e:
            db.session.rollback()
            logger.exception(f"Erro de integridade ao criar venda {e}")
            return api_error(
                400, "Dados inválidos para criar venda",
                details=str(e.orig) if getattr(e, "orig", None) else None
            )
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro SQLAlchemy ao criar venda {e}")
            return api_error(500, "Falha no banco ao criar venda", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro inesperado ao criar venda {e}")
            return api_error(500, f"Erro inesperado ao criar venda: {e}")

    # ------- Itens ---------
    @staticmethod
    def add_item(id_venda: int, data: dict):
        """
        Adiciona item a uma venda. Se o serviço já existir na venda,
        apenas incrementa a quantidade e acumula o desconto.
        NUNCA atribui em item.subtotal (é property).
        """
        try:
            id_servico = int(data.get("id_servico") or 0)
            qtd = int(data.get("quantidade") or 1)
            desconto = _as_decimal(data.get("desconto") or 0, "0")

            if id_servico <= 0 or qtd <= 0:
                return api_error(400, "id_servico e quantidade são obrigatórios e devem ser > 0")

            with db.session.begin():
                v: Venda | None = db.session.execute(
                    select(Venda).where(Venda.id_venda == id_venda).with_for_update()
                ).scalar_one_or_none()
                if not v:
                    return api_error(404, "Venda não encontrada")

                s: Servico | None = db.session.execute(
                    select(Servico).where(Servico.id_servico == id_servico).with_for_update(read=True)
                ).scalar_one_or_none()
                if not s:
                    return api_error(404, "Serviço não encontrado")

                preco = _as_decimal(s.valor or 0, "0")

                it: VendaItem | None = db.session.execute(
                    select(VendaItem)
                    .where(VendaItem.id_venda == v.id_venda,
                           VendaItem.id_servico == id_servico)
                    .with_for_update()
                ).scalar_one_or_none()

                if it:
                    it.quantidade = int(it.quantidade or 0) + qtd
                    it.desconto = _as_decimal(it.desconto or 0, "0") + desconto
                    it.preco_unit = preco
                    if hasattr(it, "descricao") and hasattr(s, "nome"):
                        it.descricao = it.descricao or s.nome
                else:
                    it = VendaItem(
                        id_venda=v.id_venda,
                        id_servico=id_servico,
                        descricao=getattr(s, "nome", None),
                        preco_unit=preco,
                        quantidade=qtd,
                        desconto=desconto,
                    )
                    db.session.add(it)

                vendaService._recalc_total_sql(v)

            return v
        except (IntegrityError, DataError, InvalidRequestError) as e:
            logger.exception(f"Erro de dados ao adicionar item {e}")
            return api_error(
                400, "Dados inválidos ao adicionar item",
                details=str(e.orig) if getattr(e, "orig", None) else str(e)
            )
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy ao adicionar item {e}")
            return api_error(500, "Falha no banco ao adicionar item", details=str(e))
        except Exception as e:
            logger.exception(f"Erro inesperado ao adicionar item {e}")
            return api_error(500, f"Falha ao adicionar item: {e}")

    @staticmethod
    def remove_item(id_venda: int, id_item: int):
        try:
            with db.session.begin():
                v = db.session.execute(
                    select(Venda).where(Venda.id_venda == id_venda).with_for_update()
                ).scalar_one_or_none()
                if not v:
                    return api_error(404, "Venda não encontrada")

                it = db.session.execute(
                    select(VendaItem)
                    .where(VendaItem.id_item == id_item, VendaItem.id_venda == id_venda)
                    .with_for_update()
                ).scalar_one_or_none()
                if not it:
                    return api_error(404, "Item não encontrado")

                db.session.delete(it)
                vendaService._recalc_total_sql(v)

            return v
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy ao remover item {e}")
            return api_error(500, "Falha no banco ao remover item", details=str(e))
        except Exception as e:
            logger.exception(f"Erro inesperado ao remover item {e}")
            return api_error(500, f"Erro ao remover item: {e}")

    @staticmethod
    def list_vendas(
        q: Optional[str] = None,
        status: Optional[str] = None,
        pagamento: Optional[str] = None,
        data_ini: Optional[datetime] = None,            # inclusive (>=)
        data_fim_exclusive: Optional[datetime] = None,  # exclusivo (<)
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        try:
            data_ini = _coerce_to_dt_start_of_day(data_ini)
            data_fim_exclusive = _coerce_to_dt_start_of_day(data_fim_exclusive)

            base = (
                db.session.query(Venda.id_venda)
                .join(Cliente, Venda.id_cliente == Cliente.id_cliente)
                .join(Veiculo, Venda.id_veiculo == Veiculo.id_veiculo)
            )

            if status:
                base = base.filter(Venda.status == status)
            if pagamento:
                base = base.filter(Venda.pagamento == pagamento)

            if q:
                like = f"%{q.strip()}%"
                base = base.filter(or_(
                    Venda.descricao.ilike(like),
                    Cliente.nome.ilike(like),
                    Veiculo.placa.ilike(like),
                ))

            # --- filtro de período com fim exclusivo ---
            if data_ini and data_fim_exclusive:
                base = base.filter(Venda.created_at >= data_ini,
                                   Venda.created_at < data_fim_exclusive)
            elif data_ini:
                prox = data_ini + timedelta(days=1)
                base = base.filter(Venda.created_at >= data_ini,
                                   Venda.created_at < prox)
            elif data_fim_exclusive:
                base = base.filter(Venda.created_at < data_fim_exclusive)

            base = base.distinct().order_by(Venda.id_venda.desc())
            subq = base.subquery()
            total = db.session.query(func.count()).select_from(subq).scalar() or 0

            # paginação
            if page and per_page:
                try:
                    page = max(1, int(page))
                    per_page = max(1, min(int(per_page), 100))
                except Exception:
                    page, per_page = 1, 24

                ids_rows = (db.session.query(subq.c.id_venda)
                            .order_by(subq.c.id_venda.desc())
                            .offset((page - 1) * per_page)
                            .limit(per_page)
                            .all())
            else:
                ids_rows = (db.session.query(subq.c.id_venda)
                            .order_by(subq.c.id_venda.desc())
                            .all())

            ids = [r[0] for r in ids_rows]
            itens = []
            if ids:
                itens = (db.session.query(Venda)
                         .filter(Venda.id_venda.in_(ids))
                         .order_by(Venda.id_venda.desc())
                         .all())

            return itens, total
        except TypeError as e:
            logger.exception(f"Parâmetros de data inválidos em list_vendas {e}")
            return [], 0
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy em list_vendas {e}")
            return [], 0
        except Exception as e:
            logger.exception(f"Erro inesperado em list_vendas {e}")
            return [], 0

    @staticmethod
    def get(id_venda: int):
        try:
            v = Venda.query.get(id_venda)
            if not v:
                return api_error(404, "Venda não encontrada")
            return v
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy em get {e}")
            return api_error(500, "Falha no banco ao buscar venda", details=str(e))
        except Exception as e:
            logger.exception(f"Erro inesperado em get {e}")
            return api_error(500, f"Erro ao buscar venda: {e}")

    @staticmethod
    def update(id_venda: int, data: dict):
        try:
            v = Venda.query.get(id_venda)
            if not v:
                return api_error(404, "Venda não encontrada")

            if "id_cliente" in data and data["id_cliente"]:
                if not Cliente.query.get(data["id_cliente"]):
                    return api_error(404, "Cliente inválido")
                v.id_cliente = data["id_cliente"]

            if "id_veiculo" in data and data["id_veiculo"]:
                if not Veiculo.query.get(data["id_veiculo"]):
                    return api_error(404, "Veículo inválido")
                v.id_veiculo = data["id_veiculo"]

            if "descricao" in data:
                v.descricao = data.get("descricao")

            if "forma" in data:
                v.pagamento = _forma_pagamento_or_default(
                    data.get("forma"),
                    fallback=v.pagamento or "PIX"
                )

            db.session.commit()
            return v
        except (IntegrityError, DataError) as e:
            db.session.rollback()
            logger.exception(f"Erro de dados em update {e}")
            return api_error(
                400, "Dados inválidos ao atualizar venda",
                details=str(e.orig) if getattr(e, "orig", None) else None
            )
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Erro SQLAlchemy em update {e}")
            return api_error(500, "Falha no banco ao atualizar venda", details=str(e))
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Erro inesperado em update {e}")
            return api_error(500, f"Erro ao atualizar venda: {e}")

    @staticmethod
    def finalizar(id_venda: int, data: dict | None = None):
        """
        Finaliza a venda:
        - Se já houver lançamento no caixa, atualiza (idempotente).
        - Se não houver, cria.
        - NÃO duplica.
        """
        payload = data or {}
        forma = payload.get("forma_pagamento")
        descricao = payload.get("descricao")
        try:
            with db.session.begin():
                v: Venda | None = db.session.execute(
                    select(Venda).where(Venda.id_venda == id_venda).with_for_update()
                ).scalar_one_or_none()

                if not v:
                    return api_error(404, "Venda não encontrada")

                if not v.itens:
                    return api_error(400, "Venda sem itens")

                vendaService._recalc_total_sql(v)
                v.status = "FINALIZADA"
                v.pagamento = _forma_pagamento_or_default(
                    forma, fallback=getattr(v, "pagamento", None) or "PIX"
                )

                cx: Caixa | None = db.session.execute(
                    select(Caixa).where(Caixa.venda_id == v.id_venda).with_for_update()
                ).scalar_one_or_none()

                valor = _as_decimal(v.total or 0, "0")

                if cx:
                    cx.valor = valor
                else:
                    db.session.add(Caixa(
                        venda_id=v.id_venda,
                        valor=valor,
                        descricao=descricao or f"VENDA #{v.id_venda}"
                    ))
            return v
        except (IntegrityError, DataError) as e:
            logger.exception(f"Erro de dados ao finalizar venda {e}")
            return api_error(
                400, "Dados inválidos ao finalizar venda",
                details=str(e.orig) if getattr(e, "orig", None) else None
            )
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy ao finalizar venda {e}")
            return api_error(500, "Falha no banco ao finalizar venda", details=str(e))
        except Exception as e:
            logger.exception(f"Erro inesperado ao finalizar venda {e}")
            return api_error(500, f"Falha ao finalizar venda: {e}")

    @staticmethod
    def cancelar(id_venda: int):
        try:
            with db.session.begin():
                v: Venda | None = db.session.execute(
                    select(Venda).where(Venda.id_venda == id_venda).with_for_update()
                ).scalar_one_or_none()

                if not v:
                    return api_error(404, "Venda não encontrada")

                v.status = "CANCELADA"

                cx: Caixa | None = db.session.execute(
                    select(Caixa).where(Caixa.venda_id == v.id_venda).with_for_update()
                ).scalar_one_or_none()

                if cx:
                    db.session.delete(cx)

            return v
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy ao cancelar venda {e}")
            return api_error(500, "Falha no banco ao cancelar venda", details=str(e))
        except Exception as e:
            logger.exception(f"Erro inesperado ao cancelar venda {e}")
            return api_error(500, f"Falha ao cancelar venda: {e}")

    @staticmethod
    def baixar_orcamento_pdf(orc_id: int):
        from service.createOrcamento import gerar_pdf_orcamento_venda_reportlab
        from flask import make_response
        from utils.api_error import api_error
        from config.db import db
        from model.companieModel import companie as Companie
        from model.vendaModel import venda as Venda

        try:
            empresa = Companie.query.get(1)
            if not empresa:
                return api_error(404, "Empresa não encontrada, cadastre uma empresa antes de gerar orçamentos.")

            venda_obj = Venda.query.get(orc_id)
            if not venda_obj:
                return api_error(404, "Orçamento (venda) não encontrado")

            db.session.refresh(venda_obj)

            pdf_bytes = gerar_pdf_orcamento_venda_reportlab(
                companie_obj=empresa,
                venda_obj=venda_obj,
                validade_orcamento="7 dias",
                observacoes_finais="Obrigado pela preferência.",
            )

            resp = make_response(pdf_bytes)
            resp.headers["Content-Type"] = "application/pdf"
            resp.headers["Content-Disposition"] = f'attachment; filename="orcamento_{orc_id:04d}.pdf"'
            return resp
        except FileNotFoundError as e:
            logger.exception(f"Template/arquivo não encontrado ao gerar PDF {e}")
            return api_error(500, f"Recurso de PDF ausente: {e}")
        except SQLAlchemyError as e:
            logger.exception(f"Erro SQLAlchemy ao preparar PDF {e}")
            return api_error(500, "Falha no banco ao preparar PDF", details=str(e))
        except Exception as e:
            logger.exception(f"Erro inesperado ao gerar PDF {e}")
            return api_error(500, f"Erro ao gerar PDF: {e}")
