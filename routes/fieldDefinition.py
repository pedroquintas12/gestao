from flask import Blueprint

from config.decorators import login_required
from controller.fieldDefinitionController import fieldDefinitionController as FC

field_definition_bp = Blueprint(
    "field_definition_bp", __name__, url_prefix="/api/field-definitions"
)

field_definition_bp.post("")(login_required(FC.create))
field_definition_bp.get("")(login_required(FC.get_all))
field_definition_bp.get("/<int:id_field>")(login_required(FC.get_one))
field_definition_bp.add_url_rule(
    "/<int:id_field>",
    view_func=login_required(FC.update),
    methods=["PUT", "PATCH"],
)
field_definition_bp.delete("/<int:id_field>")(login_required(FC.delete))
