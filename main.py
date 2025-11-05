import threading
import time
import webbrowser
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from app import create_app
from model.companieModel import companie  

app = create_app()

def _server_is_up(url: str, timeout_s: float = 10.0) -> bool:
    """Tenta acessar a URL até timeout; retorna True se responder."""
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            with urlopen(url, timeout=2) as resp:
                # Qualquer resposta HTTP já indica que o servidor subiu
                return True
        except (URLError, HTTPError):
            time.sleep(0.3)
    return False

def open_browser():
    with app.app_context():
        has_company = companie.query.first() is not None

    target = 'http://127.0.0.1:5000/login' if has_company else 'http://127.0.0.1:5000/cadastroCompanie'

    base = 'http://127.0.0.1:5000/'
    if _server_is_up(base, timeout_s=12.0):
        webbrowser.open_new(target)
    else:
        # fallback: tenta abrir mesmo assim
        webbrowser.open_new(target)

if __name__ == '__main__':
    # Dispara o open_browser em thread separada
    threading.Timer(0.5, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
