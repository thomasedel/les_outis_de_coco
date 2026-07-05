import threading
import webbrowser
import time
import sys
import os
import socket
from app import create_app


def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    if port_is_free(5000):
        # Première instance : on lance Flask + navigateur
        app = create_app()

        t = threading.Thread(target=open_browser)
        t.daemon = True
        t.start()

        app.run(
            host='127.0.0.1',
            port=5000,
            debug=False,
            use_reloader=False
        )
    else:
        # Déjà lancé : on ouvre juste un nouvel onglet
        webbrowser.open('http://127.0.0.1:5000')
