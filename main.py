import tkinter as tk
from tkinter import scrolledtext
import subprocess
import re
import itertools

bot_process = None

# ---- Bot control ----
def start_bot():
    global bot_process
    if bot_process:
        log("Bot already running!\n")
        return

    amount = eth_entry.get().strip()
    if not amount:
        log("Please enter an amount in ETH.\n")
        return

    log(f"Starting bot with {amount} ETH...\n")

    bot_process = subprocess.Popen(
        ["node", "abridge-bot.js", amount],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    start_btn.config(state="disabled")
    eth_entry.config(state="disabled")
    window.after(100, read_output)

def stop_bot():
    global bot_process
    if bot_process:
        bot_process.kill()
        log("Bot stopped.\n")
        bot_process = None
    else:
        log("Bot is not running.\n")
    start_btn.config(state="normal")
    eth_entry.config(state="normal")

def read_output():
    if bot_process:
        output = bot_process.stdout.readline()
        if output:
            log(output)
        window.after(100, read_output)

# ---- ANSI color support ----
ansi_colors = {
    '30': '#000000', '31': '#ff5555', '32': '#50fa7b', '33': '#f1fa8c',
    '34': '#bd93f9', '35': '#ff79c6', '36': '#8be9fd', '37': '#ffffff',
    '90': '#888888', '91': '#ff6e6e', '92': '#69ff94', '93': '#ffffa5',
    '94': '#d6acff', '95': '#ff92df', '96': '#a4ffff', '97': '#ffffff',
}
ansi_escape = re.compile(r'\x1b\[(\d+)m')

def log(message):
    pos = 0
    current_color = "#b3f7b3"
    for match in ansi_escape.finditer(message):
        text_segment = message[pos:match.start()]
        if text_segment:
            log_box.insert(tk.END, text_segment, current_color)
        pos = match.end()
        code = match.group(1)
        if code == '0':
            current_color = "#b3f7b3"
        elif code in ansi_colors:
            current_color = ansi_colors[code]
    remaining = message[pos:]
    if remaining:
        log_box.insert(tk.END, remaining, current_color)
    log_box.see(tk.END)

# ---- GUI Setup ----
window = tk.Tk()
window.title("Flashloan Arbitrage Bot")
window.geometry("800x600")
window.config(bg="#18181c")
window.resizable(False, False)

# --- Animated Title Glow ---
colors = itertools.cycle(["#ff79c6", "#bd93f9", "#8be9fd", "#50fa7b", "#f1fa8c"])
def glow_title():
    color = next(colors)
    title_label.config(fg=color)
    window.after(500, glow_title)

title_label = tk.Label(window, text="Flashloan Arbitrage Bot",
                       font=("Comic Sans MS", 18, "bold"),
                       bg="#18181c", fg="#ff92df")
title_label.pack(pady=15)
glow_title()

# --- Amount Input Box ---
amount_frame = tk.Frame(window, bg="#18181c")
amount_frame.pack(pady=10)

tk.Label(amount_frame, text="ETH Amount:", font=("Comic Sans MS", 13, "bold"),
         bg="#18181c", fg="#f8f8f2").grid(row=0, column=0, padx=8)

eth_entry = tk.Entry(amount_frame, width=15, font=("Consolas", 12),
                     bg="#2b2b30", fg="#8be9fd", insertbackground="white",
                     relief="flat", justify="center")
eth_entry.grid(row=0, column=1, padx=5, ipadx=4, ipady=4)
eth_entry.insert(0, "0.25")

# --- Start/Stop Buttons ---
btn_frame = tk.Frame(window, bg="#18181c")
btn_frame.pack(pady=15)

start_btn = tk.Button(btn_frame, text="Start", command=start_bot,
                      width=12, font=("Comic Sans MS", 11, "bold"),
                      bg="#50fa7b", fg="#18181c", relief="flat",
                      activebackground="#69ff94", activeforeground="#18181c",
                      cursor="hand2")
stop_btn = tk.Button(btn_frame, text="Stop", command=stop_bot,
                     width=12, font=("Comic Sans MS", 11, "bold"),
                     bg="#ff5555", fg="#fff", relief="flat",
                     activebackground="#ff6e6e", activeforeground="#fff",
                     cursor="hand2")
start_btn.grid(row=0, column=0, padx=15)
stop_btn.grid(row=0, column=1, padx=15)

# --- Log Box ---
log_box = scrolledtext.ScrolledText(window, width=70, height=16,
                                    bg="#1e1e22", fg="#b3f7b3",
                                    insertbackground="white",
                                    font=("Consolas", 10),
                                    borderwidth=0, relief="flat")
log_box.pack(pady=10, padx=15)
log_box.tag_configure("center", justify="center")

# --- Color Tags for ANSI Codes ---
for code, color in ansi_colors.items():
    log_box.tag_configure(color, foreground=color)

# --- Cute bottom credit ---
credit = tk.Label(window, text="Made with love by Ayden",
                  font=("Comic Sans MS", 10), bg="#18181c", fg="#6272a4")
credit.pack(pady=5)

window.mainloop()
