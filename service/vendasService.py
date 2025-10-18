# services/vendaService.py
from decimal import Decimal
from sqlalchemy import func, or_, select
from typing import Optional, Tuple
from config.db import db
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
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        # join para permitir busca por nome do cliente / placa do veículo
        query = db.session.query(Venda).join(Cliente, Venda.id_cliente == Cliente.id_cliente)\
                                       .join(Veiculo, Venda.id_veiculo == Veiculo.id_veiculo)

        if status:
            query = query.filter(Venda.status == status)
        if pagamento:
            query = query.filter(Venda.pagamento == pagamento)

        if q:
            like = f"%{q.strip()}%"
            query = query.filter(or_(
                Venda.descricao.ilike(like),
                Cliente.nome.ilike(like),
                Veiculo.placa.ilike(like),
            ))

        query = query.order_by(Venda.id_venda.desc())
        total = query.count()

        if page and per_page:
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 100))
            itens = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            itens = query.all()

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
                    if descricao:
                        cx.descricao = descricao
                else:
                    db.session.add(Caixa(
                        venda_id=v.id_venda,
                        valor=valor,
                        descricao=descricao or f"VENDA #{v.id_venda}"
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


