# Maestro Chat UI

A lightweight, static web interface for the Maestro multi-agent orchestration system.

## Overview

This is a single-page web app featuring two side-by-side chat windows. Currently it operates as a static frontend with local echo functionality — no backend integration yet.

## How to Use

### Option 1: Open directly in a browser

Simply open `index.html` in any modern web browser:

```bash
# macOS
open ui/index.html

# Linux
xdg-open ui/index.html

# Windows
start ui/index.html
```

### Option 2: Serve with Python's built-in HTTP server

From the project root:

```bash
cd ui
python3 -m http.server 8080
```

Then navigate to [http://localhost:8080](http://localhost:8080) in your browser.

## Features

- **Two side-by-side chat panels** — "Chat 1" and "Chat 2"
- **Dark developer-tool theme** matching the Maestro project aesthetic
- **Responsive layout** — stacks vertically on narrow screens (< 700px)
- **Local echo mode** — messages are echoed back locally as a placeholder until backend integration is added
- **Keyboard support** — press Enter to send messages

## Future Plans

- WebSocket integration with the Maestro FastAPI backend
- Real-time streaming of agent responses
- Panel assignment to specific agents/workflows
