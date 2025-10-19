from datetime import time
from threading import Thread
import threading
import webbrowser
from app import create_app

app = create_app()


def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/login')

if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()  # abre 1s depois
    app.run(host='127.0.0.1', port=5000, debug=False)