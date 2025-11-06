# controller/vendaController.py
from datetime import date, datetime, time, timedelta
from math import ceil
from flask import Blueprint, request, jsonify
from helpers.service_resulte_helper import service_result_to_response
from service.vendasService import vendaService
from config.logger import logger

def _parse_ymd_to_dt(s: str | None):
    """Converte 'YYYY-MM-DD' -> datetime(YYYY,MM,DD, 00:00:00)."""
    if not s:
        return None
    # aceita apenas 'YYYY-MM-DD'
    d = date.fromisoformat(s)  # levanta ValueError se formato inválido
    return datetime.combine(d, time.min)

class vendaController:

    def create():
        res = vendaService.create(request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="venda", created=True, with_children=True)

    def get_all():
        """
        GET /api/vendas?q=...&status=...&pagamento=...&data_ini=2025-01-01&data_fim=2025-01-31&page=1&per_page=24
        - data_ini e data_fim são opcionais, formato YYYY-MM-DD
        """
        args = request.args
        q         = args.get("q") or None
        status    = args.get("status") or None
        pagamento = args.get("pagamento") or None

        # datas
        data_ini = _parse_ymd_to_dt(args.get("data_ini"))
        data_fim = _parse_ymd_to_dt(args.get("data_fim"))
        # fim exclusivo: < (end_date + 1 dia) para cobrir até 23:59:59 do dia final
        data_fim_exclusive = (data_fim + timedelta(days=1)) if data_fim else None

        # paginação
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

        vendas, total = vendaService.list_vendas(
            q=q,
            status=status,
            pagamento=pagamento,
            data_ini=data_ini,
            data_fim_exclusive=data_fim_exclusive,
            page=page,
            per_page=per_page,
        )

        total_pages = ceil(total / per_page) if per_page else 1
        has_next = page < total_pages
        has_prev = page > 1

        return jsonify({
            "vendas": [v.to_dict(with_children=True) for v in vendas],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        }), 200
    def get_one(id_venda):
        res = vendaService.get(id_venda)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 404)
        return service_result_to_response(res, key="venda", created=False, with_children=True)

    def update(id_venda):
        res = vendaService.update(id_venda, request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="venda", created=False, with_children=True)

    def add_item(id_venda):
        res = vendaService.add_item(id_venda, request.get_json(force=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="venda", created=False, with_children=True)

    def del_item(id_venda, id_item):
        res = vendaService.remove_item(id_venda, id_item)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="venda", created=False, with_children=True)

    def finalizar(id_venda):
        res = vendaService.finalizar(id_venda, request.get_json(silent=True) or {})
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="venda", created=False, with_children=True)

    def cancelar(id_venda):
        res = vendaService.cancelar(id_venda)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return service_result_to_response(res, key="venda", created=False, with_children=True)
    def baixar_orcamento_pdf(orc_id):
        res = vendaService.baixar_orcamento_pdf(orc_id)
        if isinstance(res, dict) and res.get("error"):
            return jsonify(res), res.get("status", 400)
        return res