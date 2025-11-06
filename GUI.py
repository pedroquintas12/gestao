# GUI.py
# Gestao - Atualização/Inicialização com GUI + aviso de update
# Requisitos: Python 3.12+, Tkinter (Windows já tem), internet para checar update (opcional)

import subprocess
import threading
import queue
import time
import webbrowser
import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import urllib.request, urllib.error
import json
import tempfile
# import hashlib  # (opcional) para validar SHA-256 do instalador

APP_URL = "http://127.0.0.1:5000"             
HEALTH_URL = APP_URL + "/"                   
HEALTH_TIMEOUT_S = 25                         

try:
    from version import __version__ as CURRENT_VERSION
except Exception:
    CURRENT_VERSION = "0.0.0"

LATEST_JSON_URL = "https://raw.githubusercontent.com/pedroquintas12/gestao/refs/heads/main/latest.json"

# Parâmetros do instalador Inno Setup para atualização
INSTALLER_ARGS = ["/VERYSILENT", "/NORESTART"]

# Passos de preparação/instalação locais antes de iniciar
STEPS = [
    ("Verificando ambiente", 'echo Verificando ambiente...'),
    ("Atualizando pip",       r'.\venv\Scripts\python.exe -m pip install --upgrade pip'),
    ("Instalando deps",       r'.\venv\Scripts\pip.exe install -r requirements.txt'),
    ("Iniciando servidor",    r'.\venv\Scripts\python.exe main.py'),
]

def _parse_ver(v: str):
    """Converte '1.2.3' -> tupla comparável (1,2,3). Imune a strings vazias."""
    v = (v or "").strip()
    if not v:
        return (0,)
    parts = []
    for p in v.split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return tuple(parts)

class UpdaterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestao - Atualização e Inicialização")
        self.geometry("860x560")
        self.minsize(760, 500)

        # =========================
        # BARRA DE ATUALIZAÇÃO (oculta no início)
        # =========================
        self.update_bar = ttk.Frame(self)
        self.update_bar.pack(fill="x", padx=12, pady=(10, 0))
        self.update_bar.pack_forget()

        self.update_msg = ttk.Label(self.update_bar, text="", foreground="#0a7")
        self.update_msg.pack(side="left")

        self.btn_update = ttk.Button(self.update_bar, text="Atualizar agora", command=self.on_update_click)
        self.btn_update.pack(side="right")

        # =========================
        # Cabeçalho / Progresso
        # =========================
        self.lbl_title = ttk.Label(self, text="Atualizando / Preparando o sistema...", font=("Segoe UI", 14, "bold"))
        self.lbl_title.pack(pady=(16, 6))

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=760)
        self.progress.pack()
        self.progress["value"] = 0
        self.progress["maximum"] = 100

        self.lbl_percent = ttk.Label(self, text="0%")
        self.lbl_percent.pack(pady=(4, 8))

        # =========================
        # Log estilo “terminal”
        # =========================
        frm_log = ttk.Frame(self)
        frm_log.pack(fill="both", expand=True, padx=12, pady=8)

        self.txt = tk.Text(frm_log, wrap="word", state="disabled", height=18)
        self.txt.pack(side="left", fill="both", expand=True)

        self.scroll = ttk.Scrollbar(frm_log, orient="vertical", command=self.txt.yview)
        self.scroll.pack(side="right", fill="y")
        self.txt.configure(yscrollcommand=self.scroll.set)

        # =========================
        # Rodapé (botões)
        # =========================
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill="x", padx=12, pady=10)

        self.btn_open = ttk.Button(frm_btn, text="Abrir o sistema", command=self.open_site, state="disabled")
        self.btn_open.pack(side="left")

        self.btn_close = ttk.Button(frm_btn, text="Fechar", command=self.on_close)
        self.btn_close.pack(side="right")

        # Estado interno
        self.log_queue = queue.Queue()
        self.latest_installer_url = None
        self.latest_meta = None  # guarda latest.json inteiro (se quiser validar sha256, etc.)

        # Threads
        self.worker = threading.Thread(target=self.run_steps, daemon=True)
        self.worker.start()

        # Timers/UI
        self.after(100, self.drain_log_queue)

        # Checagem de atualização em background
        threading.Thread(target=self.check_for_update, daemon=True).start()

    # ---------- UI helpers ----------
    def append_log(self, text: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", text)
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def set_progress(self, pct: float):
        pct = max(0.0, min(100.0, pct))
        self.progress["value"] = pct
        self.lbl_percent.config(text=f"{pct:.0f}%")

    def set_title(self, title: str):
        self.lbl_title.config(text=title)

    # ---------- Ações ----------
    def open_site(self):
        webbrowser.open_new(APP_URL)

    def on_close(self):
        self.destroy()

    def drain_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.append_log(msg)
        except queue.Empty:
            pass
        self.after(100, self.drain_log_queue)

    # ---------- Execução dos passos ----------
    def run_steps(self):
        total = len(STEPS)
        for idx, (title, cmd) in enumerate(STEPS, start=1):
            self.safe_set_title(f"{title}...")
            self.safe_log(f"\n=== {title} ===\n$ {cmd}\n")

            if title.lower().startswith("iniciando servidor"):
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        cwd=self.get_app_root(),
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )

                    start = time.time()
                    while time.time() - start < HEALTH_TIMEOUT_S:
                        if proc.stdout and not proc.poll():
                            try:
                                line = proc.stdout.readline()
                            except Exception:
                                line = ""
                            if line:
                                self.safe_log(line)

                        try:
                            with urllib.request.urlopen(HEALTH_URL, timeout=2):
                                self.safe_log("\n✔ Servidor respondeu ao health-check.\n")
                                break
                        except Exception:
                            time.sleep(0.3)

                    # marca a etapa como concluída
                    self.safe_set_progress((idx / total) * 100.0)
                    self.safe_set_title("Tudo pronto!")
                    self.safe_enable_open_button()
                    self.safe_log("\n✔ Inicialização concluída (servidor em background).\n")

                    # Continua “tail” dos logs do servidor
                    threading.Thread(target=self._tail_process, args=(proc,), daemon=True).start()
                    return
                except Exception as e:
                    self.safe_log(f"\nEXCEÇÃO ao iniciar servidor: {e}\n")
                    self.safe_set_title("Falha ao iniciar servidor")
                    return

            # Passos normais
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    cwd=self.get_app_root(),
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                for line in proc.stdout:
                    self.safe_log(line)
                ret = proc.wait()
                self.safe_log(f"\n[exit code: {ret}]\n")
                if ret != 0:
                    self.safe_log("ERRO: etapa falhou. Interrompendo.\n")
                    self.safe_set_title("Falha na atualização")
                    return
            except Exception as e:
                self.safe_log(f"\nEXCEÇÃO: {e}\n")
                self.safe_set_title("Falha na atualização")
                return

            self.safe_set_progress((idx / total) * 100.0)

        # Caso haja passos depois
        self.safe_set_title("Tudo pronto!")
        self.safe_set_progress(100.0)
        self.safe_enable_open_button()
        self.safe_log("\n✔ Concluído.\n")

    # ---------- Tail contínuo dos logs do servidor ----------
    def _tail_process(self, proc: subprocess.Popen):
        try:
            while True:
                if proc.stdout is None:
                    break
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                self.safe_log(line)
        except Exception:
            pass
        finally:
            code = proc.poll()
            if code is not None:
                self.safe_log(f"\n[servidor finalizou com código {code}]\n")

    # ---------- Thread-safe setters ----------
    def safe_log(self, msg: str):
        self.log_queue.put(msg)

    def safe_set_progress(self, pct: float):
        self.after(0, lambda: self.set_progress(pct))

    def safe_set_title(self, title: str):
        self.after(0, lambda: self.set_title(title))

    def safe_enable_open_button(self):
        self.after(0, lambda: self.btn_open.config(state="normal"))

    # ---------- util ----------
    def get_app_root(self) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return str(Path(__file__).resolve().parent)

    # =========================
    # UPDATE: checar e baixar
    # =========================
    def check_for_update(self):
        """Consulta latest.json e exibe a barra se houver versão nova."""
        try:
            req = urllib.request.Request(LATEST_JSON_URL, headers={"User-Agent": "Gestao-Updater"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            self.latest_meta = data
            latest = str(data.get("version", "")).strip()
            win = data.get("windows", {}) or {}
            self.latest_installer_url = win.get("installer_url")
            if latest and self.latest_installer_url:
                if _parse_ver(latest) > _parse_ver(CURRENT_VERSION):
                    self.after(0, lambda: self.show_update_bar(latest))
        except Exception as e:
            self.safe_log(f"\n[Aviso] Falha ao checar updates: {e}\n")

    def show_update_bar(self, latest):
        self.update_msg.config(text=f"Nova versão disponível: {latest} (você está na {CURRENT_VERSION})")
        self.update_bar.pack(fill="x", padx=12, pady=(10, 0))

    def on_update_click(self):
        if not getattr(self, "latest_installer_url", None):
            return
        self.btn_update.config(state="disabled")
        self.safe_log("\nBaixando atualizador...\n")
        threading.Thread(target=self.download_and_run_installer, daemon=True).start()

    def download_and_run_installer(self):
        url = self.latest_installer_url
        try:
            tmpdir = tempfile.gettempdir()
            basename = os.path.basename(url) or "Gestao-Setup.exe"
            dst = os.path.join(tmpdir, basename)

            with urllib.request.urlopen(url, timeout=120) as r, open(dst, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                read = 0
                chunk = 64 * 1024
                while True:
                    buf = r.read(chunk)
                    if not buf:
                        break
                    f.write(buf)
                    read += len(buf)
                    if total > 0:
                        self.safe_set_progress(min(99.0, (read / total) * 100.0))

            self.safe_log(f"\nDownload concluído: {dst}\n")

            # (Opcional) validar SHA-256 usando self.latest_meta["windows"]["sha256"]
            # if self.latest_meta:
            #     expected = str(self.latest_meta.get("windows", {}).get("sha256") or "").lower()
            #     if expected:
            #         got = hashlib.sha256(open(dst, "rb").read()).hexdigest().lower()
            #         if got != expected:
            #             raise Exception("SHA-256 inválido para o instalador baixado.")

            self.safe_set_title("Iniciando atualizador...")
            args = [dst] + INSTALLER_ARGS
            subprocess.Popen(args, shell=False)
            self.safe_log("Instalador iniciado. Siga as instruções.\n")
            # opcional: fechar GUI após iniciar instalador
            # self.after(1000, self.on_close)
        except Exception as e:
            self.safe_log(f"\nErro ao atualizar: {e}\n")
            self.after(0, lambda: self.btn_update.config(state="normal"))

if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = UpdaterGUI()
    app.mainloop()
