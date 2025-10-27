from flask import jsonify, request
from helpers.service_resulte_helper import service_result_to_response
from service.companieSerive import companieSerive

class companieController:

    def create_companie():
        data =request.get_json(silent= True)
        app = companieSerive.create_companie(data)
        return service_result_to_response(app, key="companie", created=True)
    
    def get_one(id_companie):
        res = companieSerive.get_companie(id_companie)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 404)
        return service_result_to_response(res, key="companie", created=False)
    
