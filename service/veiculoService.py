
from sqlalchemy import or_
from typing import Optional, Tuple
from flask import jsonify
from model.clienteModel import cliente
from model.veiculoModel import veiculo
from config.db import db
class veiculoService:

    def valid_payload(data :dict) -> tuple[dict,dict]:
            err= {}
            out= {}

            id_cliente = data.get('id_cliente')
            placa = (data.get('placa') or '').strip().upper()
            observacao= data.get('obs')
            kilometragem = data.get('km')

            if not id_cliente:
                err[id_cliente] = "Campo 'id_cliente' Obrigatorio"
            if not placa:
                err[placa] = "Campo 'placa' Obrigatorio"

            
            out.update({
                "id_cliente": id_cliente,
                "placa":placa,
                "observacao":observacao,
                "marca":data.get('marca'),
                "modelo":data.get('modelo'),
                "cor":data.get('cor'),
                "kilometragem":kilometragem
            })
            return out, err
            
    @staticmethod
    def create_veiculo(data: dict) -> veiculo:
        
        placa = data.get('placa')
        verify = veiculo.query.filter_by(placa = placa).all()
        if verify:
             from utils.api_error import api_error
             return api_error (400,"veiculo ja existente")
        
        payload,err = veiculoService.valid_payload(data)
        print(payload,err)
        if err:
             from utils.api_error import api_error
             return api_error(400, "erro ao validar", err)
        try:
             app = veiculo(**payload)
             db.session.add(app)
             db.session.commit()
             return app 
        
        except Exception as e:
            from utils.api_error import api_error
            return api_error(400,"erro ao criar veiculo", details=e)
        
    @staticmethod
    def list_veiculos(
        q: Optional[str] = None,
        id_cliente: Optional[int] = None,
        page: Optional[int] = 1,
        per_page: Optional[int] = 24
    ) -> Tuple[list, int]:
        query = veiculo.query.filter_by(deleted=False)

        if id_cliente:
            query = query.filter(veiculo.id_cliente == id_cliente)

        if q:
            like = f"%{q.strip()}%"
            query = query.filter(or_(
                veiculo.placa.ilike(like),
                veiculo.observacao.ilike(like),
            ))

        query = query.order_by(veiculo.id_veiculo.desc())
        total = query.count()

        if page and per_page:
            page = max(1, int(page))
            per_page = max(1, min(int(per_page), 100))
            itens = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            itens = query.all()

        return itens, total
    
    @staticmethod
    def update(id_veiculo: int, data: dict):
        obj = veiculo.query.get(id_veiculo)
        if not obj or obj.deleted:
            from utils.api_error import api_error
            return api_error(404, "Veículo não encontrado")
        merged = {
            "id_cliente": obj.id_cliente,
            "placa": obj.placa,
            "kilometragem": obj.kilometragem,
            "observacao": obj.observacao,
            "marca": obj.marca,
            "modelo": obj.modelo,
            "cor": obj.cor,
            **(data or {})
        }
        payload, err = veiculoService.valid_payload(merged)
        if err:
            return api_error(400, "Erro no payload", details=err)

        # valida cliente
        if not cliente.query.get(payload["id_cliente"]):
            return api_error(404, "Cliente inválido")

        obj.id_cliente  = payload["id_cliente"]
        obj.placa       = payload["placa"]
        obj.kilometragem= payload.get("kilometragem")
        obj.observacao  = payload.get("observacao")
        obj.marca       = payload.get("marca")
        obj.modelo      = payload.get("modelo")
        obj.cor         = payload.get("cor")
        db.session.commit()
        return obj

    @staticmethod
    def get(id_veiculo: int):
        obj = veiculo.query.get(id_veiculo)
        if not obj or obj.deleted:
            from utils.api_error import api_error
            return api_error(404, "Veículo não encontrado")
        return obj

    @staticmethod
    def delete(id_veiculo: int):
        obj = veiculo.query.get(id_veiculo)
        if not obj:
            from utils.api_error import api_error
            return api_error(404, "Veículo não encontrado")
        obj.deleted = id_veiculo
        db.session.commit()
        return {"deleted": True}
    
    

