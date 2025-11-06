# GUI.py
# Gestao - Atualização/Inicialização com GUI + aviso de update

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
import ctypes  # para UAC (elevação)

APP_URL = "http://127.0.0.1:5000"
HEALTH_URL = APP_URL + "/"
HEALTH_TIMEOUT_S = 25

# versão atual (gerada no workflow em version.py)
try:
    from version import __version__ as CURRENT_VERSION
except Exception:
    CURRENT_VERSION = "0.0.0"

# onde checar a última versão
LATEST_JSON_URL = "https://raw.githubusercontent.com/pedroquintas12/gestao/refs/heads/main/latest.json"

# args padrão do instalador (modo silencioso)
INSTALLER_ARGS_SILENT = ["/VERYSILENT", "/NORESTART", "/CLOSEAPPLICATIONS"]
# args com UI (para fallback e diagnóstico)
INSTALLER_ARGS_UI = ["/NORESTART", "/CLOSEAPPLICATIONS"]

# processos do sistema a encerrar (NÃO inclua a própria GUI aqui!)
KILL_IMAGES = ["launcher.exe", "python.exe", "pythonw.exe", "Gestao.exe"]

# passos antes do servidor subir
STEPS = [
    ("Verificando ambiente", 'echo Verificando ambiente...'),
    ("Atualizando pip",       r'.\venv\Scripts\python.exe -m pip install --upgrade pip'),
    ("Instalando deps",       r'.\venv\Scripts\pip.exe install -r requirements.txt'),
    ("Iniciando servidor",    r'.\venv\Scripts\python.exe main.py'),
]


def _parse_ver(v: str):
    """Converte '1.2.3' -> (1,2,3) para comparação segura."""
    v = (v or "").strip()
    if not v:
        return (0,)
    parts = []
    for p in v.split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return tuple(parts)


def launch_elevated(exe_path: str, args_list: list[str]) -> bool:
    """Executa EXE elevado via UAC. Retorna True se iniciou."""
    params = " ".join(args_list)
    workdir = os.path.dirname(exe_path) or None
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, workdir, 1)
        return rc > 32
    except Exception:
        return False


class UpdaterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestao - Atualização e Inicialização")
        self.geometry("860x560")
        self.minsize(760, 500)

        # ===== Barra de atualização (oculta no início)
        self.update_bar = ttk.Frame(self)
        self.update_bar.pack(fill="x", padx=12, pady=(10, 0))
        self.update_bar.pack_forget()

        self.update_msg = ttk.Label(self.update_bar, text="", foreground="#0a7")
        self.update_msg.pack(side="left")

        self.btn_update = ttk.Button(self.update_bar, text="Atualizar agora", command=self.on_update_click)
        self.btn_update.pack(side="right")

        # ===== Cabeçalho / Progresso
        self.lbl_title = ttk.Label(self, text="Atualizando / Preparando o sistema...", font=("Segoe UI", 14, "bold"))
        self.lbl_title.pack(pady=(16, 6))

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=760)
        self.progress.pack()
        self.progress["value"] = 0
        self.progress["maximum"] = 100

        self.lbl_percent = ttk.Label(self, text="0%")
        self.lbl_percent.pack(pady=(4, 8))

        # ===== Log tipo terminal
        frm_log = ttk.Frame(self)
        frm_log.pack(fill="both", expand=True, padx=12, pady=8)

        self.txt = tk.Text(frm_log, wrap="word", state="disabled", height=18)
        self.txt.pack(side="left", fill="both", expand=True)

        self.scroll = ttk.Scrollbar(frm_log, orient="vertical", command=self.txt.yview)
        self.scroll.pack(side="right", fill="y")
        self.txt.configure(yscrollcommand=self.scroll.set)

        # ===== Rodapé
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill="x", padx=12, pady=10)

        self.btn_open = ttk.Button(frm_btn, text="Abrir o sistema", command=self.open_site, state="disabled")
        self.btn_open.pack(side="left")

        self.btn_close = ttk.Button(frm_btn, text="Fechar", command=self.on_close)
        self.btn_close.pack(side="right")

        # ===== Estado
        self.log_queue = queue.Queue()
        self.latest_installer_url = None
        self.latest_meta = None
        self.server_proc: subprocess.Popen | None = None

        # ===== Threads
        self.worker = threading.Thread(target=self.run_steps, daemon=True)
        self.worker.start()

        self.after(100, self.drain_log_queue)

        # checagem de update em background
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
                    self.server_proc = proc

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

                    self.safe_set_progress((idx / total) * 100.0)
                    self.safe_set_title("Tudo pronto!")
                    self.safe_enable_open_button()
                    self.safe_log("\n✔ Inicialização concluída (servidor em background).\n")

                    threading.Thread(target=self._tail_process, args=(proc,), daemon=True).start()
                    return
                except Exception as e:
                    self.safe_log(f"\nEXCEÇÃO ao iniciar servidor: {e}\n")
                    self.safe_set_title("Falha ao iniciar servidor")
                    return

            # passos normais
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

        self.safe_set_title("Tudo pronto!")
        self.safe_set_progress(100.0)
        self.safe_enable_open_button()
        self.safe_log("\n✔ Concluído.\n")

    # ---------- Tail contínuo ----------
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
    def safe_log(self, msg: str): self.log_queue.put(msg)
    def safe_set_progress(self, pct: float): self.after(0, lambda: self.set_progress(pct))
    def safe_set_title(self, title: str): self.after(0, lambda: self.set_title(title))
    def safe_enable_open_button(self): self.after(0, lambda: self.btn_open.config(state="normal"))

    # ---------- util ----------
    def get_app_root(self) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return str(Path(__file__).resolve().parent)

    # ---------- encerramento total (menos a GUI) ----------
    def _run_quiet(self, cmd: str):
        try:
            subprocess.run(cmd, shell=True, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def kill_everything(self):
        """Encerra o servidor iniciado pela GUI e mata processos conhecidos (exceto esta GUI)."""
        self.safe_log("\nEncerrando processos do sistema...\n")

        # 1) encerra o servidor que a GUI iniciou
        try:
            if self.server_proc and (self.server_proc.poll() is None):
                self.safe_log("• Finalizando processo do servidor iniciado pela GUI...\n")
                try:
                    self.server_proc.terminate()
                except Exception:
                    pass
                for _ in range(10):
                    if self.server_proc.poll() is not None:
                        break
                    time.sleep(0.1)
                if self.server_proc.poll() is None:
                    try:
                        self.safe_log("• Servidor resistente — aplicando kill()...\n")
                        self.server_proc.kill()
                    except Exception:
                        pass
        except Exception:
            pass

        # 2) mata processos por imagem (com filhos)
        for img in KILL_IMAGES:
            self._run_quiet(f'taskkill /IM {img} /F /T')

        time.sleep(0.4)  # tempo para liberar handles
        self.safe_log("• Processos encerrados (ou não encontrados).\n")

    # =========================
    # UPDATE
    # =========================
    def check_for_update(self):
        """Consulta latest.json e mostra aviso se houver versão mais nova."""
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
        """Baixa o instalador, encerra tudo, tenta iniciar elevado (silencioso); se falhar, inicia com UI e log; encerra a GUI."""
        url = self.latest_installer_url
        try:
            tmpdir = tempfile.gettempdir()
            basename = os.path.basename(url) or "Gestao-Setup.exe"
            dst = os.path.join(tmpdir, basename)

            # 1) Download
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

            # 2) Mata tudo (menos esta GUI)
            self.safe_set_title("Encerrando o sistema para atualizar...")
            self.kill_everything()
            time.sleep(0.5)

            # 3) Monta args com LOG em %TEMP%
            log_path = os.path.join(tmpdir, "gestao_installer.log")
            args_silent = INSTALLER_ARGS_SILENT + [f"/LOG={log_path}"]
            args_ui = INSTALLER_ARGS_UI + [f"/LOG={log_path}"]

            # 4) Tenta iniciar ELEVADO (silencioso)
            self.safe_set_title("Iniciando atualizador...")
            started_elev = launch_elevated(dst, args_silent)

            # fallback com UI (para ver mensagens se UAC/elevação falhar)
            if not started_elev:
                try:
                    subprocess.Popen([dst] + args_ui, shell=False)
                    self.safe_log("\n(Aviso) UAC elevado falhou. Iniciando instalador com interface.\n")
                except Exception as e:
                    self.safe_log(f"\nFalha ao iniciar instalador: {e}\nLog: {log_path}\n")
                    self.after(0, lambda: self.btn_update.config(state="normal"))
                    return

            # 5) Dá um tempo para o instalador abrir de fato
            time.sleep(1.5 if started_elev else 2.5)

            # 6) Fecha a GUI (libera qualquer lock residual)
            self.safe_set_progress(100.0)
            self.safe_log(f"Instalador iniciado. (Log: {log_path}) Encerrando a aplicação...\n")
            time.sleep(0.2)
            os._exit(0)

        except Exception as e:
            self.safe_log(f"\nErro ao atualizar: {e}\n")
            self.after(0, lambda: self.btn_update.config(state="normal"))


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app = UpdaterGUI()
    app.mainloop()
