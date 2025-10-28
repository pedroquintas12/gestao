from flask import Blueprint, render_template

from config.decorators import login_required,admin_required



front_bp = Blueprint('front',__name__)

@login_required
@front_bp.route('/')
def index():
    return render_template('index.html')

@admin_required
@front_bp.route('/admin')
def admin():
    return render_template('admin.html')

@front_bp.route('/cadastroCompanie')
def cadastro_companie():
    return render_template('cadastroCompanie.html')