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

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x580")
        self.configure(bg="#11131a")
        self.resizable(False, False)
        self.streamer = None

        # ---- Gradient Background (Canvas Overlay) ----
        self.canvas = tk.Canvas(self, width=900, height=580, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.gradient_bg()

        # ---- Title ----
        title = tk.Label(self, text=APP_TITLE, font=("Consolas", 20, "bold"),
                         fg="#00ffff", bg="#11131a")
        title.place(x=290, y=15)

        # ---- ETH Input ----
        self.eth_var = tk.StringVar(value="0.25")
        tk.Label(self, text="ETH Amount:", font=("Consolas", 13, "bold"),
                 fg="#00ffcc", bg="#11131a").place(x=120, y=80)
        self.eth_entry = tk.Entry(self, textvariable=self.eth_var, font=("Consolas", 12),
                                  width=10, bg="#181b2e", fg="#00ffff", insertbackground="white",
                                  relief="flat", justify="center")
        self.eth_entry.place(x=250, y=82)

        # ---- Buttons ----
        self.start_btn = tk.Button(self, text="▶ Start", command=self.start,
                                   font=("Consolas", 12, "bold"),
                                   bg="#00ff66", fg="#0b0b0b",
                                   activebackground="#00ff99", activeforeground="black",
                                   relief="flat", width=10)
        self.stop_btn = tk.Button(self, text="■ Stop", command=self.stop,
                                  font=("Consolas", 12, "bold"),
                                  bg="#ff3333", fg="white",
                                  activebackground="#ff5555", relief="flat", width=10, state="disabled")
        self.save_btn = tk.Button(self, text="💾 Save Logs", command=self.save_logs,
                                  font=("Consolas", 12, "bold"),
                                  bg="#0099ff", fg="white",
                                  activebackground="#33ccff", relief="flat", width=12)

        self.start_btn.place(x=400, y=80)
        self.stop_btn.place(x=540, y=80)
        self.save_btn.place(x=680, y=80)

        # ---- Log Box ----
        self.log = tk.Text(self, wrap="word", font=("Consolas", 11),
                           bg="#001a00", fg="#39ff14",
                           insertbackground="white", relief="flat", padx=10, pady=10)
        self.log.place(x=60, y=140, width=780, height=380)

        scrollbar = tk.Scrollbar(self, command=self.log.yview)
        scrollbar.place(x=840, y=140, height=380)
        self.log.config(yscrollcommand=scrollbar.set)

        # Color tags
        self.log.tag_configure("META", foreground="#00ffff")
        for code, color in ANSI_COLORS.items():
            self.log.tag_configure(color, foreground=color)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- Gradient ----
    def gradient_bg(self):
        for i in range(0, 580):
            r = int(17 + (60 - 17) * (i / 580))
            g = int(19 + (10 - 19) * (i / 580))
            b = int(26 + (46 - 26) * (i / 580))
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.create_line(0, i, 900, i, fill=color, width=1)
        self.canvas.lower("all")

    # ---- Process Control ----
    def start(self):
        if self.streamer and self.streamer.proc and self.streamer.proc.poll() is None:
            self._log_meta("Bot already running.")
            return
        amount = self.eth_var.get().strip()
        if not amount:
            messagebox.showwarning("Missing Input", "Please enter ETH amount.")
            return
        try:
            float(amount)
        except ValueError:
            messagebox.showerror("Invalid", "ETH amount must be numeric.")
            return
        if not shutil_which("node"):
            messagebox.showerror("Missing Node", "Node.js not found in PATH.")
            return
        if not os.path.exists(JS_ENTRYPOINT):
            messagebox.showerror("Missing Script", f"Cannot find '{JS_ENTRYPOINT}'.")
            return

        cmd = ["node", JS_ENTRYPOINT, amount]
        self.streamer = ProcessStreamer(cmd)
        self.streamer.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.eth_entry.config(state="disabled")
        self._log_meta(f"Starting bot with {amount} ETH ...")
        self._drain_queue()

    def stop(self):
        if self.streamer:
            self.streamer.kill()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.eth_entry.config(state="normal")
        self._log_meta("Bot stopped.")

    def save_logs(self):
        content = self.log.get("1.0", "end-1c")
        if not content.strip():
            self._log_meta("No logs to save.")
            return
        fname = filedialog.asksaveasfilename(
            title="Save Logs", defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if fname:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(content)
            self._log_meta(f"Logs saved to {fname}")

    # ---- Queue Drain ----
    def _drain_queue(self):
        if not self.streamer:
            return
        try:
            while True:
                tag, line = self.streamer.q.get_nowait()
                if tag in ("OUT", "ERR"):
                    self._append_ansi(line)
                elif tag == "DONE":
                    rc = self.streamer.proc.returncode
                    self._log_meta(f"Process exited with code {rc}.")
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.eth_entry.config(state="normal")
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)

    # ---- Helpers ----
    def _append_ansi(self, text: str):
        for seg, color in split_ansi_segments(text):
            if not seg:
                continue
            if color:
                self.log.insert("end", seg, color)
            else:
                self.log.insert("end", seg)
        self.log.see("end")

    def _log_meta(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n", ("META",))
        self.log.see("end")

    def on_close(self):
        if self.streamer:
            self.streamer.kill()
        self.destroy()

def shutil_which(cmd):
    from shutil import which
    return which(cmd) is not None

if __name__ == "__main__":
    App().mainloop()
