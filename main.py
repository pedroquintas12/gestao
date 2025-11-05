import threading
import webbrowser
from app import create_app
from model.companieModel import companie  

app = create_app()


def open_browser():
    with app.app_context():
        has_company = companie.query.first() is not None

    target = 'http://127.0.0.1:5000/login' if has_company else 'http://127.0.0.1:5000/cadastroCompanie'
    
    webbrowser.open_new(target)

if __name__ == '__main__':
    # Dispara o open_browser em thread separada
    threading.Timer(0.5, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
