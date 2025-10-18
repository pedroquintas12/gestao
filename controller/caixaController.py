from datetime import datetime, date as date_cls, timedelta, time as time_cls
from sqlalchemy import and_, func
from flask import request, jsonify
from config.db import db
from model.caixaModel import caixa_lancamento as CaixaModel  # ajuste o import ao seu projeto

def _parse_date(s: str | None, default: date_cls | None = None) -> date_cls | None:
    if not s:
        return default
    # aceita "YYYY-MM-DD" (valor do input type=date)
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return default

class caixaController:
    @staticmethod
    def get_all():
        args = request.args

        data      = args.get("data") or None
        data_ini  = args.get("data_ini") or None
        data_fim  = args.get("data_fim") or None

        # paginação segura
        try:
            page = max(1, int(args.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = int(args.get("per_page", 24))
        except (TypeError, ValueError):
            per_page = 24
        per_page = max(1, min(per_page, 100))

        q = CaixaModel.query  # .filter_by(cancelado=False) se quiser ocultar cancelados
        filtros = []

        # monta intervalo de datas sem usar funções específicas do SGBD
        if data:
            d = _parse_date(data, default=date_cls.today())
            start_dt = datetime.combine(d, time_cls.min)            # 00:00:00
            end_dt   = datetime.combine(d + timedelta(days=1), time_cls.min)  # dia seguinte 00:00:00
            filtros.append(and_(CaixaModel.created_at >= start_dt,
                                CaixaModel.created_at <  end_dt))
        else:
            di = _parse_date(data_ini, default=None)
            df = _parse_date(data_fim, default=None)
            if di and df:
                start_dt = datetime.combine(di, time_cls.min)
                # limite exclusivo: dia após df às 00:00
                end_dt   = datetime.combine(df + timedelta(days=1), time_cls.min)
                filtros.append(and_(CaixaModel.created_at >= start_dt,
                                    CaixaModel.created_at <  end_dt))

        if filtros:
            q = q.filter(and_(*filtros))

        # totalizador com o MESMO filtro
        total_valor = (db.session.query(func.coalesce(func.sum(CaixaModel.valor), 0.0))
                       .filter(and_(*filtros)) if filtros else
                       db.session.query(func.coalesce(func.sum(CaixaModel.valor), 0.0))
                      ).scalar() or 0.0

        q = q.order_by(CaixaModel.created_at.desc())

        total_regs = q.count()
        itens = (q.offset((page - 1) * per_page)
                 .limit(per_page)
                 .all())

        # se seu model não garante ISO nas datas, serialize aqui
        def _serialize(i: CaixaModel):
            d = i.to_dict() if hasattr(i, "to_dict") else {
                "id": i.id,
                "venda_id": getattr(i, "venda_id", None),
                "descricao": getattr(i, "descricao", None),
                "valor": float(getattr(i, "valor", 0.0) or 0.0),
                "tipo": getattr(i, "tipo", None),
                "origem": getattr(i, "origem", None),
                "cancelado": bool(getattr(i, "cancelado", False)),
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            }
            # garante ISO string nas datas
            for k in ("created_at", "updated_at"):
                if isinstance(d.get(k), datetime):
                    d[k] = d[k].isoformat()
            return d

        total_pages = (total_regs + per_page - 1) // per_page

        return jsonify({
            "lancamentos": [_serialize(i) for i in itens],
            "total_valor": float(total_valor),
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_regs,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }), 200
