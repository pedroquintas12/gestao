from math import ceil
from flask import jsonify, request
from helpers.service_resulte_helper import service_result_to_response
from service.servicoService import servicoService

class servicoController:
    
    def create():
        data =request.get_json(silent= True)
        app = servicoService.create_service(data)
        return service_result_to_response(app, key="servico", created=True)
    
    def get_all():
        """
        GET /api/servicos?q=...&page=1&per_page=24
        """
        args = request.args
        q = args.get("q") or None

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

        servicos, total = servicoService.list_services(
            q=q,
            page=page,
            per_page=per_page,
        )

        total_pages = ceil(total / per_page) if per_page else 1
        has_next = page < total_pages
        has_prev = page > 1

        return jsonify({
            "servicos": [s.to_dict() for s in servicos],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        }), 200
    
    def get_one(id_servico):
        res = servicoService.get_service(id_servico)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 404)
        return service_result_to_response(res, key="servico", created=False)

    def update(id_servico):
        res = servicoService.update_service(id_servico, request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="servico", created=False)

    def delete(id_servico):
        res = servicoService.delete_service(id_servico)
        status = 200 if res.get("deleted") else res.get("status", 400)
        return jsonify(res), status