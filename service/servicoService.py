# services/servicoService.py
from typing import Optional, Tuple
from model.servicoModel import servico
from config.db import db
from utils.api_error import api_error

class servicoService:
    @staticmethod
    def valid_payload(data: dict) -> tuple[dict, dict]:
        err, out = {}, {}
        nome  = data.get("nome")
        valor = data.get("valor")

        if not nome:
            err["nome"] = "Campo 'nome' Obrigatório"
        if valor is None:
            err["valor"] = "Campo 'valor' Obrigatório"

        out.update({"nome": nome, "valor": valor})
        return out, err

    @staticmethod
    def create_service(data: dict) -> servico | dict:
        payload, err = servicoService.valid_payload(data)
        if err:
            return api_error(400, "Erro no payload", details=err)
        obj = servico(**payload)
        db.session.add(obj)
        db.session.commit()
        return obj

    @staticmethod
    def update_service(id_servico: int, data: dict) -> servico | dict:
        obj = servico.query.get(id_servico)
        if not obj:
            return api_error(404, "Serviço não encontrado")

        payload, err = servicoService.valid_payload({**obj.to_dict(), **(data or {})})
        if err:
            return api_error(400, "Erro no payload", details=err)

        obj.nome  = payload["nome"]
        obj.valor = payload["valor"]
        db.session.commit()
        return obj

    @staticmethod
    def list_services(
        q: Optional[str] = None,
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        query = servico.query.filter_by(deleted=False)

        if q:
            like = f"%{q.strip()}%"
            query = query.filter(servico.nome.ilike(like))

        query = query.order_by(servico.id_servico.desc())
        total = query.count()

        if page and per_page:
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 100))
            itens = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            itens = query.all()

        return itens, total

    @staticmethod
    def get_service(id_servico: int) -> servico | dict:
        obj = servico.query.get(id_servico)
        if not obj or obj.deleted:
            return api_error(404, "Serviço não encontrado")
        return obj

    @staticmethod
    def delete_service(id_servico: int) -> dict:
        obj = servico.query.get(id_servico)
        if not obj:
            return api_error(404, "Serviço não encontrado")
        obj.deleted = id_servico
        db.session.commit()
        return {"deleted": True}
