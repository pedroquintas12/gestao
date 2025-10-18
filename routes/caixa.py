from math import ceil
from flask import Blueprint, request, jsonify
from datetime import datetime, date
from sqlalchemy import func, cast, Date
from config.db import db
from controller.caixaController import caixaController as Cc

caixa_bp = Blueprint("caixa", __name__, url_prefix="/api/caixa")

caixa_bp.get("")(Cc.get_all)
