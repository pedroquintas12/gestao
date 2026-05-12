from math import ceil

from flask import jsonify, request

from helpers.service_resulte_helper import service_result_to_response
from service.produtoService import produtoService
from utils.api_error import api_error


class produtoController:

    def create():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return api_error(400, "JSON inválido ou ausente.")
        res = produtoService.create(data)
        return service_result_to_response(res, key="produto", created=True)

    def get_all():
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

        rows, total = produtoService.list_all(q=q, page=page, per_page=per_page)

        total_pages = ceil(total / per_page) if per_page else 1
        return jsonify({
            "produtos": [p.to_dict() for p in rows],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            }
        }), 200

    def get_one(id_produto):
        res = produtoService.get(id_produto)
        return service_result_to_response(res, key="produto")

    def get_by_codigo(codigo):
        res = produtoService.get_by_codigo(codigo)
        return service_result_to_response(res, key="produto")

    def update(id_produto):
        res = produtoService.update(id_produto, request.get_json(force=True) or {})
        return service_result_to_response(res, key="produto")

    def delete(id_produto):
        res = produtoService.delete(id_produto)
        status = 200 if res.get("deleted") else res.get("status", 400)
        return jsonify(res), status

    def adjust_quantidade(id_produto):
        """POST /api/produtos/<id>/ajustar  body: {"delta": <int>}"""
        data = request.get_json(silent=True) or {}
        delta = data.get("delta", 0)
        res = produtoService.adjust_quantidade(id_produto, delta)
        return service_result_to_response(res, key="produto")
