from flask import jsonify, request

from helpers.service_resulte_helper import service_result_to_response
from service.fieldDefinitionService import fieldDefinitionService
from utils.api_error import api_error


class fieldDefinitionController:

    def create():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return api_error(400, "JSON inválido ou ausente.")
        res = fieldDefinitionService.create(data)
        return service_result_to_response(res, key="campo", created=True)

    def get_all():
        entity = request.args.get("entity") or None
        items = fieldDefinitionService.list_all(entity=entity)
        return jsonify({"campos": [f.to_dict() for f in items]}), 200

    def get_one(id_field):
        res = fieldDefinitionService.get(id_field)
        return service_result_to_response(res, key="campo")

    def update(id_field):
        res = fieldDefinitionService.update(id_field, request.get_json(force=True) or {})
        return service_result_to_response(res, key="campo")

    def delete(id_field):
        res = fieldDefinitionService.delete(id_field)
        status = 200 if res.get("deleted") else res.get("status", 400)
        return jsonify(res), status
