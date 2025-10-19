from flask import Blueprint, render_template

front_bp = Blueprint('front',__name__)

@front_bp.route('/')
def index():
    return render_template('index.html')

@front_bp.route('/admin')
def admin():
    return render_template('admin.html')