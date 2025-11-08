# Flashloan Arbitrage Bot

A GUI-based flashloan arbitrage bot built with Python and Node.js. This bot allows you to execute arbitrage operations while monitoring logs in real-time.

---

## Features

- Tkinter GUI for ETH amount input and log monitoring  
- Real-time log output with color support  
- Start/Stop controls for the bot  
- Environment-based configuration for secure private keys and RPC URLs  

---

## Complete Setup & Usage Guide

Follow these steps to get the bot running:

### 1. Install Python Dependencies

```bash
pip install tkinter
pip install scrolledtext
```
These packages are required for the GUI and log display.

## 2. Initialize Node.js Project

```bash
npx init -y
```
This creates a package.json file for managing Node.js dependencies required for the bot.

## 3. Configure Environment Variables
Configure the .env file in the project root with the following content:
```bash
PRIVATE_KEY=your_private_key_here
WS_RPC_URL=your_websocket_rpc_url_here
HTTP_RPC_URL=your_http_rpc_url_here
```
Notes:

Free RPC URLs can be obtained from Alchemy or similar providers.

Keep your private key secure — never share it publicly.

## 4. Launch the Bot
```bash
python main.py
```
Enter the amount of ETH you want to use.

Click Start to run the bot or Stop to terminate it.

Monitor real-time logs in the GUI window.
