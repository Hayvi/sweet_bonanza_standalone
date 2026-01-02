# Sweet Bonanza 1000 - Standalone Launcher

A standalone launcher for Sweet Bonanza 1000 (Game ID: 95426) with virtual wallet balance integration.

## Features

- 🎰 Launches Sweet Bonanza 1000 demo game
- 💰 Custom virtual wallet balance displayed directly in-game
- 🔄 Real-time balance sync - wins/losses update the CREDIT display
- 🎯 Canvas interception replaces the game's balance with your custom balance

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

Launch with default balance ($1000):
```bash
python launcher.py
```

Launch with custom balance:
```bash
python launcher.py --balance 500
```

Launch on different port:
```bash
python launcher.py --balance 777.77 --port 8080
```

## How It Works

1. The launcher starts a local HTTP server with a virtual wallet
2. Fetches the demo game URL from MelBet API
3. Launches Chromium with the balance interception extension
4. The extension intercepts canvas rendering to display your custom balance
5. Win/loss deltas are tracked and synced to your virtual wallet in real-time
6. The in-game CREDIT display updates automatically as you play

## Files

- `launcher.py` - Main launcher script
- `extension/` - Browser extension for balance interception
  - `pragmatic_specific.js` - Canvas interception for Pragmatic Play games
  - `content.js` - Content script for balance sync
  - `manifest.json` - Extension manifest

## Technical Details

The extension uses Manifest V3 with `world: "MAIN"` to inject directly into the page's JavaScript context. This allows intercepting `CanvasRenderingContext2D.prototype.fillText` before the game renders any text, enabling real-time balance replacement.

The extension polls the wallet API every second to get the current balance and broadcasts updates to the game iframe via postMessage.

Only values > $5000 are replaced to preserve game UI elements (bet amounts, buy prices, win displays, etc.).
