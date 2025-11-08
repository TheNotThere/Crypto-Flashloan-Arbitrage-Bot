import os
import time
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Flashloan Arbitrage Bot"
JS_ENTRYPOINT = "abridge-bot.js"

ANSI_COLORS = {
    '31': '#ff4d4f', '32': '#39ff14', '33': '#ffff66',
    '34': '#00bfff', '35': '#ff00ff', '36': '#00ffff', '37': '#ffffff'
}
RESET_CODE = '0'
ANSI_TOKEN = "\x1b["

def split_ansi_segments(text: str):
    i = 0
    color = None
    while i < len(text):
        esc = text.find(ANSI_TOKEN, i)
        if esc == -1:
            yield (text[i:], color)
            break
        if esc > i:
            yield (text[i:esc], color)
        m_end = text.find('m', esc)
        if m_end == -1:
            yield (text[esc:], color)
            break
        code = text[esc + 2:m_end]
        if code == RESET_CODE:
            color = None
        elif code in ANSI_COLORS:
            color = ANSI_COLORS[code]
        i = m_end + 1

class ProcessStreamer:
    def __init__(self, cmd, cwd=None):
        self.cmd = cmd
        self.cwd = cwd
        self.proc = None
        self.q = queue.Queue()
        self._stop = threading.Event()

    def start(self):
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        def reader(stream, tag):
            for line in iter(stream.readline, ''):
                if self._stop.is_set():
                    break
                self.q.put((tag, line))
            stream.close()
        t1 = threading.Thread(target=reader, args=(self.proc.stdout, "OUT"), daemon=True)
        t2 = threading.Thread(target=reader, args=(self.proc.stderr, "ERR"), daemon=True)
        t1.start(); t2.start()
        t1.join(); t2.join()
        self.q.put(("DONE", ""))

    def kill(self):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass
        self._stop.set()

# ----------------------------
# Main App
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x580")
        self.configure(bg="#11131a")
        self.resizable(False, False)
        self.streamer = None

        self.canvas = tk.Canvas(self, width=900, height=580, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.gradient_bg()

        title = tk.Label(self, text=APP_TITLE, font=("Consolas", 20, "bold"),
                         fg="#00ffff", bg="#11131a")
        title.place(x=290, y=15)

        self.eth_var = tk.StringVar(value="0.25")
        tk.Label(self, text="ETH Amount:", font=("Consolas", 13, "bold"),
                 fg="#00ffcc", bg="#11131a").place(x=120, y=80)
        self.eth_entry = tk.Entry(self, textvariable=self.eth_var, font=("Consolas", 12),
                                  width=10, bg="#181b2e", fg="#00ffff", insertbackground="white",
                                  relief="flat", justify="center")
        self.eth_entry.place(x=250, y=82)
