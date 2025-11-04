import config.logger   # inicializa logging
from app import create_app
import threading, webbrowser

app = create_app()

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/login')

if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
