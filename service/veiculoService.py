
from flask import jsonify
from model.veiculoModel import veiculo
from config.db import db
class veiculoService:

    def valid_payload(data :dict) -> tuple[dict,dict]:
            err= {}
            out= {}

            id_cliente = data.get('id_cliente')
            placa = data.get('placa')
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
                "kilometragem":kilometragem
            })
            return out, err
            
    @staticmethod
    def create_veiculo(data: dict) -> veiculo:
        
        placa = data.get('placa')
        verify = veiculo.query.filter_by(placa = placa)
        if verify:
             from utils.api_error import api_error
             return api_error (400,"veiculo ja existente")
        
        payload,err = veiculoService.valid_payload(data)
        if err:
             from utils.api_error import api_error
             return api_error(400, "erro ao validar", err)
        try:
             app = veiculo(**payload)
             db.session.add(app)
             db.session.commit()
             return jsonify(app.to_dict())
        
        except Exception as e:
            from utils.api_error import api_error
            return api_error(400,"erro ao criar veiculo", details=e)