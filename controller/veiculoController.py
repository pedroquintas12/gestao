# controller/veiculoController.py
from math import ceil
from flask import Blueprint, request, jsonify
from service.veiculoService import veiculoService
from helpers.service_resulte_helper import service_result_to_response

class veiculoController:
    
    def create():
        res = veiculoService.create_veiculo(request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="veiculo", created=True, with_children=False)

    def get_all():
        """
        GET /api/veiculos?q=...&id_cliente=...&page=1&per_page=24
        """
        args = request.args
        q = args.get("q") or None
        id_cliente = args.get("id_cliente", type=int) or None

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

        veiculos, total = veiculoService.list_veiculos(
            q=q,
            id_cliente=id_cliente,
            page=page,
            per_page=per_page,
        )

        total_pages = ceil(total / per_page) if per_page else 1
        has_next = page < total_pages
        has_prev = page > 1

        return jsonify({
            "veiculos": [v.to_dict(with_children=False) for v in veiculos],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        }), 200

    def get_one(id_veiculo):
        res = veiculoService.get(id_veiculo)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 404)
        return service_result_to_response(res, key="veiculo", created=True, with_children=False)

    def update(id_veiculo):
        res = veiculoService.update(id_veiculo, request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="veiculo", created=True, with_children=False)


    def delete(id_veiculo):
        res = veiculoService.delete(id_veiculo)
        status = 200 if res.get("deleted") else res.get("status", 400)
        return jsonify(res), status
