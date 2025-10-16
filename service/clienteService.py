
from flask import jsonify
from model.clienteModel import cliente
from config.db import db
class clienteService():
    def valid_payload(data :dict) -> tuple[dict,dict]:
        err= {}
        out= {}

        nome = data.get("nome")

        if not nome:
            err[nome] = "Campo 'nome' Obrigatorio"

        cpf = data.get("cpf")
        
        out.update({
            "nome": nome,
            "cpf": cpf
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
        except Exception as e:
            from utils.api_error import api_error
            return api_error(400,"erro ao criar cliente", exc=e)
    

    @staticmethod
    def update_cliente(cid:int,data:dict) -> cliente:
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
        
    

