# services/vendaService.py
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from flask import make_response
from sqlalchemy import and_, func, or_, select
from typing import Optional, Tuple
from config.db import db
from model.companieModel import companie
from utils.api_error import api_error
from model.vendaModel import venda as Venda, VendaItem
from model.servicoModel import servico as Servico
from model.clienteModel import cliente as Cliente
from model.veiculoModel import veiculo as Veiculo
from model.caixaModel import caixa_lancamento as Caixa
from enums.forma_pagamentoEnum import FormaPagamento

def _num(v):
    try: return float(v)
    except: return 0.0

def _coerce_to_dt_start_of_day(v):
    """Aceita datetime|date|str|None e devolve datetime na 00:00."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, time.min)
    if isinstance(v, str):
        # espera 'YYYY-MM-DD'
        d = date.fromisoformat(v)
        return datetime.combine(d, time.min)
    raise TypeError(f"Tipo de data não suportado: {type(v)}")


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
        # garante Decimal
        v.total = Decimal(str(soma or 0))
    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}
        id_cliente = data.get("id_cliente")
        id_veiculo = data.get("id_veiculo")
        descricao  = data.get("descricao")

        if not id_cliente:
            err["id_cliente"] = "Campo 'id_cliente' Obrigatório"
        if not id_veiculo:
            err["id_veiculo"] = "Campo 'id_veiculo' Obrigatório"

        out.update({"id_cliente": id_cliente, "id_veiculo": id_veiculo, "descricao": descricao})
        return out, err

    @staticmethod
    def create(data: dict):
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
            qtd        = int(data.get("quantidade") or 1)
            desconto   = Decimal(str(data.get("desconto") or 0))

            if id_servico <= 0 or qtd <= 0:
                return api_error(400, "id_servico e quantidade são obrigatórios")

            with db.session.begin():
                v: Venda | None = db.session.execute(
                    select(Venda).where(Venda.id_venda == id_venda).with_for_update()
                ).scalar_one_or_none()
                if not v:
                    return api_error(404, "Venda não encontrada")

                # trava/pega o serviço
                s: Servico | None = db.session.execute(
                    select(Servico).where(Servico.id_servico == id_servico).with_for_update(read=True)
                ).scalar_one_or_none()
                if not s:
                    return api_error(404, "Serviço não encontrado")

                preco = Decimal(str(s.valor or 0))

                # procura item existente do mesmo serviço
                it: VendaItem | None = db.session.execute(
                    select(VendaItem)
                    .where(VendaItem.id_venda == v.id_venda,
                           VendaItem.id_servico == id_servico)
                    .with_for_update()
                ).scalar_one_or_none()

                if it:
                    # agrega
                    it.quantidade = int(it.quantidade or 0) + qtd
                    # acumula desconto na mesma linha (opcional: troque por max/desconto unitário se quiser)
                    it.desconto = Decimal(str(it.desconto or 0)) + desconto
                    # garante preço/descrição atualizados
                    it.preco_unit = preco
                    if hasattr(it, "descricao") and hasattr(s, "nome"):
                        it.descricao = it.descricao or s.nome
                else:
                    # cria nova linha
                    it = VendaItem(
                        id_venda=v.id_venda,
                        id_servico=id_servico,
                        descricao=getattr(s, "nome", None),
                        preco_unit=preco,
                        quantidade=qtd,
                        desconto=desconto,
                    )
                    db.session.add(it)

                # NÃO setar it.subtotal (é @property). Recalcular total da venda:
                vendaService._recalc_total_sql(v)

            return v
        except Exception as e:
            # não propague Exception crua — volte api_error p/ controller tratar
            return api_error(500, f"Falha ao adicionar item: {e}")

    @staticmethod
    def remove_item(id_venda: int, id_item: int):
        v = Venda.query.get(id_venda)
        if not v:
            return api_error(404, "Venda não encontrada")
        it = VendaItem.query.filter_by(id_item=id_item, id_venda=id_venda).first()
        if not it:
            return api_error(404, "Item não encontrado")
        db.session.delete(it)
        db.session.flush()
        vendaService._recalc_total_sql(v)
        db.session.commit()
        return v

   
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

        print(data_ini, data_fim_exclusive)

        # --- filtro de período com fim exclusivo ---
        if data_ini and data_fim_exclusive:
            base = base.filter(Venda.created_at >= data_ini,
                            Venda.created_at <  data_fim_exclusive)
        elif data_ini:
            prox = data_ini + timedelta(days=1)
            base = base.filter(Venda.created_at >= data_ini,
                            Venda.created_at <  prox)
        elif data_fim_exclusive:
            base = base.filter(Venda.created_at < data_fim_exclusive)

        # --- ids únicos + contagem coerente ---
        base = base.distinct().order_by(Venda.id_venda.desc())
        subq = base.subquery()
        total = db.session.query(func.count()).select_from(subq).scalar()

        # paginação nos ids distintos
        if page and per_page:
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 100))
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

    @staticmethod
    def get(id_venda: int):
        v = Venda.query.get(id_venda)
        if not v:
            return api_error(404, "Venda não encontrada")
        return v

    @staticmethod
    def update(id_venda: int, data: dict):
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
            v.pagamento = data.get("forma")

        db.session.commit()
        return v

    @staticmethod
    def finalizar(id_venda: int, data: dict | None = None):
        """
        Finaliza a venda:
        - Se já houver lançamento no caixa, atualiza (idempotente).
        - Se não houver, cria.
        - NÃO duplica.
        """
        payload   = data or {}
        forma     = payload.get("forma_pagamento")
        descricao = payload.get("descricao")
        print("FINALIZAR VENDA:", id_venda, payload)
        try:
            with db.session.begin():
                v: Venda | None = db.session.execute(
                    select(Venda).where(Venda.id_venda == id_venda).with_for_update()
                ).scalar_one_or_none()

                if not v:
                    return api_error(404, "Venda não encontrada")

                # precisa ter pelo menos 1 item
                if not v.itens:
                    return api_error(400, "Venda sem itens")

                # recalcula
                vendaService._recalc_total_sql(v)

                v.status    = "FINALIZADA"
                v.pagamento = (forma or getattr(v, "pagamento", None) or "PIX")

                # procura lançamento caixa
                cx: Caixa | None = db.session.execute(
                    select(Caixa).where(Caixa.venda_id == v.id_venda).with_for_update()
                ).scalar_one_or_none()

                valor = Decimal(str(v.total or 0))

                if cx:
                    cx.valor = valor 
                else:
                    db.session.add(Caixa(
                        venda_id=v.id_venda,
                        valor=valor,
                        descricao= descricao or f"VENDA #{v.id_venda}"
                    ))

            return v
        except Exception as e:
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
        except Exception as e:
            return api_error(500, f"Falha ao cancelar venda: {e}")


    @staticmethod
    def baixar_orcamento_pdf(orc_id: int):
        from service.createOrcamento import gerar_pdf_orcamento_venda_reportlab
        from flask import make_response
        from utils.api_error import api_error
        from config.db import db
        from model.companieModel import companie as Companie
        from model.vendaModel import venda as Venda

        empresa = Companie.query.get(1)
        if not empresa:
            return api_error(404, "Empresa não encontrada, cadastre uma empresa antes de gerar orçamentos.")

        venda_obj = Venda.query.get(orc_id)
        if not venda_obj:
            return api_error(404, "Orçamento (venda) não encontrado")

        # garante que relações lazy já estejam carregadas
        db.session.refresh(venda_obj)

        try:
            pdf_bytes = gerar_pdf_orcamento_venda_reportlab(
                companie_obj=empresa,
                venda_obj=venda_obj,
                validade_orcamento="7 dias",
                observacoes_finais="Obrigado pela preferência.",
            )
        except Exception as e:
            print("ERRO PDF:", e)
            return api_error(500, f"Erro ao gerar PDF: {e}")

        resp = make_response(pdf_bytes)
        resp.headers["Content-Type"] = "application/pdf"
        resp.headers["Content-Disposition"] = f'attachment; filename="orcamento_{orc_id:04d}.pdf"'
        return resp