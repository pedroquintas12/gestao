
from sqlalchemy import or_
from typing import Optional, Tuple
from flask import jsonify
from model.clienteModel import cliente
from config.db import db
class clienteService():
    def valid_payload(data :dict) -> tuple[dict,dict]:
        err= {}
        out= {}

        nome = data.get("nome")
        numero = data.get("numero")

        if not nome:
            err[nome] = "Campo 'nome' Obrigatorio"

        cpf = data.get("cpf")
        
        out.update({
            "nome": nome,
            "cpf": cpf,
            "numero":numero
        })
        return out, err
            

    @staticmethod
    def create_cliente(data: dict) -> cliente:
        payload,err = clienteService.valid_payload(data)
        if err:
            from utils.api_error import api_error
            return api_error(400,"erro ao validar cliente", err)
        try:
            app = cliente(**payload)
            db.session.add(app)
            db.session.commit()
            return app
        except Exception as e:
            from utils.api_error import api_error
            return api_error(400,"erro ao criar cliente", details=e)
    

    @staticmethod
    def update_cliente(cid:int, data:dict) -> cliente:
        c = cliente.query.get_or_404(cid)
        payload,err = clienteService.valid_payload(data)
        if err:
            from utils.api_error import api_error
            return api_error(400,"erro ao validar cliente", err)
        try:
            for k,v in payload.items():
                setattr(c,k,v)
            db.session.add(c)
            db.session.commit()
            return jsonify({c.to_dict()}),200
        except Exception as e:
            db.session.rollback()
            return api_error(500, "Falha ao atualizar cliente", {"detail": str(e)})
        
    @staticmethod
    def list_cliente(
        q: Optional[str] = None,
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        """
        Retorna (itens, total_filtrado)
        - itens: lista de clientes (já paginada)
        - total_filtrado: total de registros após filtros (sem paginação)
        """
        # base query
        query = cliente.query.filter_by(deleted=False)

        # filtro de busca
        if q:
            like_query = f"%{q.strip()}%"
            query = query.filter(or_(
                cliente.nome.ilike(like_query),
                cliente.cpf.ilike(like_query),
                cliente.numero.ilike(like_query),
            ))

        query = query.order_by(cliente.id_cliente.desc())

        total = query.count()

        if page and per_page:
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 100))
            itens = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            itens = query.all()

        return itens, total
        
        

    def get(id_cliente: int):
        obj = cliente.query.get(id_cliente)

        if not obj or obj.deleted != 0:
            from utils.api_error import api_error
            return api_error(404, "Cliente não encontrado")
        return obj

    @staticmethod
    def delete(id_cliente: int):
        obj = cliente.query.get(id_cliente)
        if not obj:
            from utils.api_error import api_error
            return api_error(404, "Cliente não encontrado")
        obj.deleted = id_cliente
        db.session.commit()
        return {"deleted": True}

