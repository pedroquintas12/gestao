from math import ceil
from flask import jsonify, request
from service.clienteService import clienteService
from helpers.service_resulte_helper import service_result_to_response
from utils.api_error import api_error

class clienteController:

    def create():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return api_error(400,"JSON inválido ou ausente.")
        c = clienteService.create_cliente(data)
        return service_result_to_response(c, key="cliente", created=True, with_children=False)
    
    
    def get_all():
        """
        GET /clientes?q=...&page=1&per_page=24
        """
        args = request.args
        q = args.get("q") or None

        # paginação segura
        try:
            page = int(args.get("page", 1))
        except ValueError:
            page = 1
        try:
            per_page = int(args.get("per_page", 24))
        except ValueError:
            per_page = 24
        per_page = max(1, min(per_page, 100))
        page = max(1, page)

        clientes, total = clienteService.list_cliente(
            q=q,
            page=page,
            per_page=per_page,
        )

        total_pages = ceil(total / per_page) if per_page else 1
        has_next = page < total_pages
        has_prev = page > 1

        return jsonify({
            "clientes": [c.to_dict() for c in clientes],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        }), 200
    
    def get_one(id_cliente):
        res = clienteService.get(id_cliente)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 404)
        return service_result_to_response(res, key="cliente", created=False, with_children=True)

    def update(id_cliente):
        res = clienteService.update_cliente(id_cliente, request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="cliente", created=False, with_children=False)

    def delete(id_cliente):
        res = clienteService.delete(id_cliente)
        status = 200 if res.get("deleted") else res.get("status", 400)
        return jsonify(res), status