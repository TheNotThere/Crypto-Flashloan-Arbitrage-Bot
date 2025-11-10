import os
import time
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Abridge • Flashloan Arbitrage Bot"
JS_ENTRYPOINT = "abridge-bot.js"

ANSI_COLORS = {
    "31": "#f97373",
    "32": "#4ade80",
    "33": "#fde68a",
    "34": "#60a5fa",
    "35": "#f472b6",
    "36": "#67e8f9",
    "37": "#e5e7eb",
}
RESET_CODE = "0"
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
        m_end = text.find("m", esc)
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
            for line in iter(stream.readline, ""):
                if self._stop.is_set():
                    break
                self.q.put((tag, line))
            stream.close()

        t1 = threading.Thread(target=reader, args=(self.proc.stdout, "OUT"), daemon=True)
        t2 = threading.Thread(target=reader, args=(self.proc.stderr, "ERR"), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
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

        self.bg = "#05060a"
        self.card_bg = "#0b0f16"
        self.text_main = "#e5e7eb"
        self.text_muted = "#9ca3af"
        self.accent = "#38bdf8"
        self.accent_soft = "#0f172a"

        self.title(APP_TITLE)
        self.geometry("960x600")
        self.configure(bg=self.bg)
        self.resizable(False, False)
        self.streamer = None
        self.status_var = tk.StringVar(value="Idle")
        self.eth_var = tk.StringVar(value="0.25")

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self._configure_styles()

        self.splash_frame = None
        self.welcome_frame = None
        self.main_frame = None
        self.log = None
        self.start_btn = None
        self.stop_btn = None

        self._build_splash()
        self.after(1600, self._show_welcome)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_styles(self):
        self.style.configure("App.TFrame", background=self.bg)
        self.style.configure("Card.TFrame", background=self.card_bg)
        self.style.configure("Header.TLabel", background=self.bg, foreground=self.text_main, font=("Segoe UI", 18, "bold"))
        self.style.configure("SplashTitle.TLabel", background=self.bg, foreground=self.text_main, font=("Segoe UI", 26, "bold"))
        self.style.configure("SplashSub.TLabel", background=self.bg, foreground=self.text_muted, font=("Segoe UI", 11))
        self.style.configure("Section.TLabel", background=self.card_bg, foreground=self.text_main, font=("Segoe UI", 12, "bold"))
        self.style.configure("Body.TLabel", background=self.card_bg, foreground=self.text_muted, font=("Segoe UI", 10))
        self.style.configure("Status.TLabel", background=self.card_bg, foreground=self.accent, font=("Segoe UI", 10, "bold"))
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=6,
            foreground=self.bg,
            background=self.accent,
        )
        self.style.map(
            "Primary.TButton",
            background=[("disabled", "#1e293b"), ("active", "#0ea5e9")],
            foreground=[("disabled", "#6b7280")],
        )
        self.style.configure(
            "Ghost.TButton",
            font=("Segoe UI", 10),
            padding=6,
            foreground=self.text_main,
            background=self.accent_soft,
        )
        self.style.map(
            "Ghost.TButton",
            background=[("active", "#111827")],
            foreground=[("disabled", "#6b7280")],
        )

    def _build_splash(self):
        self.splash_frame = tk.Frame(self, bg=self.bg)
        self.splash_frame.pack(fill="both", expand=True)

        inner = tk.Frame(self.splash_frame, bg=self.bg)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        title = ttk.Label(inner, text="ABRIDGE", style="SplashTitle.TLabel")
        subtitle = ttk.Label(inner, text="Flashloan Arbitrage Bot", style="SplashSub.TLabel")

        bar = ttk.Progressbar(inner, mode="indeterminate", length=200)
        bar.start(10)

        title.pack(pady=(0, 4))
        subtitle.pack(pady=(0, 16))
        bar.pack()

    def _show_welcome(self):
        if self.splash_frame is not None:
            self.splash_frame.destroy()
            self.splash_frame = None
        self._build_welcome()

    def _build_welcome(self):
        self.welcome_frame = tk.Frame(self, bg=self.bg)
        self.welcome_frame.pack(fill="both", expand=True)

        inner = tk.Frame(self.welcome_frame, bg=self.bg)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        title = ttk.Label(inner, text="Welcome back!", style="SplashTitle.TLabel")
        subtitle = ttk.Label(
            inner,
            text="Ready when you are. Review logs or jump straight into a new run.",
            style="SplashSub.TLabel",
        )

        btn = ttk.Button(inner, text="Go to dashboard", style="Primary.TButton", command=self._show_dashboard)

        title.pack(pady=(0, 6))
        subtitle.pack(pady=(0, 18))
        btn.pack(ipadx=12, ipady=2)

    def _show_dashboard(self):
        if self.splash_frame is not None:
            self.splash_frame.destroy()
            self.splash_frame = None
        if self.welcome_frame is not None:
            self.welcome_frame.destroy()
            self.welcome_frame = None
        self._build_main_layout()

    def _build_main_layout(self):
        self.main_frame = ttk.Frame(self, style="App.TFrame")
        self.main_frame.pack(fill="both", expand=True, padx=24, pady=24)

        header = ttk.Frame(self.main_frame, style="App.TFrame")
        header.pack(fill="x")

        header_label = ttk.Label(header, text="Dashboard", style="Header.TLabel")
        header_label.pack(side="left")

        content = ttk.Frame(self.main_frame, style="App.TFrame")
        content.pack(fill="both", expand=True, pady=(18, 0))

        left_card = ttk.Frame(content, style="Card.TFrame", padding=20)
        left_card.pack(side="left", fill="y")

        right_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        right_card.pack(side="left", fill="both", expand=True, padx=(16, 0))

        section_title = ttk.Label(left_card, text="Run bot", style="Section.TLabel")
        section_title.pack(anchor="w")

        status_label = ttk.Label(left_card, textvariable=self.status_var, style="Status.TLabel")
        status_label.pack(anchor="w", pady=(4, 12))

        amount_label = ttk.Label(left_card, text="ETH amount", style="Body.TLabel")
        amount_label.pack(anchor="w")

        amount_entry = ttk.Entry(left_card, textvariable=self.eth_var, font=("Segoe UI", 10), justify="center")
        amount_entry.pack(fill="x", pady=(4, 16))
        self.eth_entry = amount_entry

        btn_row1 = ttk.Frame(left_card, style="Card.TFrame")
        btn_row1.pack(fill="x", pady=(0, 8))

        self.start_btn = ttk.Button(
            btn_row1,
            text="Start bot",
            style="Primary.TButton",
            command=self.start,
        )
        self.start_btn.pack(side="left", fill="x", expand=True)

        self.stop_btn = ttk.Button(
            btn_row1,
            text="Stop bot",
            style="Ghost.TButton",
            command=self.stop,
            state="disabled",
        )
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        btn_row2 = ttk.Frame(left_card, style="Card.TFrame")
        btn_row2.pack(fill="x", pady=(4, 0))

        save_btn = ttk.Button(
            btn_row2,
            text="Save logs",
            style="Ghost.TButton",
            command=self.save_logs,
        )
        save_btn.pack(side="left", fill="x", expand=True)

        about_btn = ttk.Button(
            btn_row2,
            text="About the devs",
            style="Ghost.TButton",
            command=self.show_about,
        )
        about_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        log_label = ttk.Label(right_card, text="Log output", style="Section.TLabel")
        log_label.pack(anchor="w", pady=(0, 8))

        log_container = tk.Frame(right_card, bg=self.card_bg, highlightthickness=0)
        log_container.pack(fill="both", expand=True)

        self.log = tk.Text(
            log_container,
            wrap="word",
            font=("Consolas", 10),
            bg=self.card_bg,
            fg=self.text_main,
            insertbackground=self.text_main,
            relief="flat",
            padx=12,
            pady=12,
        )
        self.log.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.config(yscrollcommand=scrollbar.set)

        self.log.tag_configure("META", foreground=self.accent)
        for code, color in ANSI_COLORS.items():
            self.log.tag_configure(color, foreground=color)

    def start(self):
        if self.streamer and self.streamer.proc and self.streamer.proc.poll() is None:
            self._log_meta("Bot already running.")
            return

        amount = self.eth_var.get().strip()
        if not amount:
            messagebox.showwarning("Missing input", "Please enter an ETH amount.")
            return
        try:
            float(amount)
        except ValueError:
            messagebox.showerror("Invalid value", "ETH amount must be numeric.")
            return

        if not shutil_which("node"):
            messagebox.showerror("Node.js not found", "Node.js is not available in PATH.")
            return

        if not os.path.exists(JS_ENTRYPOINT):
            messagebox.showerror("Missing script", f"Cannot find '{JS_ENTRYPOINT}'.")
            return

        cmd = ["node", JS_ENTRYPOINT, amount]
        self.streamer = ProcessStreamer(cmd)
        self.streamer.start()

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.eth_entry.configure(state="disabled")
        self.status_var.set("Running")
        self._log_meta(f"Starting bot with {amount} ETH...")
        self._drain_queue()

    def stop(self):
        if self.streamer:
            self.streamer.kill()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.eth_entry.configure(state="normal")
        self.status_var.set("Idle")
        self._log_meta("Bot stopped.")

    def save_logs(self):
        content = self.log.get("1.0", "end-1c")
        if not content.strip():
            self._log_meta("No logs to save.")
            return
        fname = filedialog.asksaveasfilename(
            title="Save logs",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if fname:
            with open(fname, "w", encoding="utf-8") as f:
                f.write(content)
            self._log_meta(f"Logs saved to {fname}")

    def show_about(self):
        messagebox.showinfo(
            "About the devs",
            "Abridge Flashloan Arbitrage Bot\n\nBuilt by the Abridge team.\nFocused on fast, efficient cross-pool opportunities.",
        )

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
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.eth_entry.configure(state="normal")
                    self.status_var.set("Idle")
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)

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
