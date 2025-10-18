# helpers/service_resulte_helper.py
from flask import jsonify, Response
import inspect

def _to_dict_optional(model_obj, with_children):
    """Chama to_dict respeitando a assinatura do modelo."""
    fn = getattr(model_obj, "to_dict", None)
    if not callable(fn):
        return model_obj

    if with_children is None:
        return fn()

    params = inspect.signature(fn).parameters
    if "with_children" in params:
        return fn(with_children=with_children)
    return fn()

def service_result_to_response(res, key: str, *, created: bool = False, with_children: bool | None = None):
    """
    with_children:
      - None  -> usa o default do modelo (opcional de verdade)
      - True/False -> força o valor, quando o modelo suportar
    """
    if hasattr(res, "to_dict"):
        body = {key: _to_dict_optional(res, with_children)}
        return jsonify(body), (201 if created else 200)

    if isinstance(res, tuple) and 2 <= len(res) <= 3:
        return res

    if isinstance(res, Response):
        return res

    if isinstance(res, dict) and res.get("error"):
        return jsonify(res), res.get("status", 400)

    # 5) 
    return jsonify(res), 200
