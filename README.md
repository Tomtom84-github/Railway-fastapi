# FastMCP HTTP Time Server

Dieses Repository stellt einen minimalen [FastMCP](https://gofastmcp.com/) Server bereit,
der über den HTTP (Streamable) Transport die aktuelle Uhrzeit als Tool anbietet. Die App ist
bereit für Railway-Deployments, funktioniert aber ebenso lokal.

## 🚀 Setup

```bash
pip install -r requirements.txt
```

## ▶️ Startbefehle

- Produktion (Railway o. Ä.):
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
- Lokal als Skript mit integriertem Server:
  ```bash
  python main.py
  ```

## 🛠️ Tooling

Der Server registriert ein einziges Tool `current_time`, welches den aktuellen UTC-Zeitstempel
im ISO-8601-Format zurückgibt.

## 📚 Ressourcen

- FastMCP Dokumentation: https://gofastmcp.com/
- Streamable HTTP Deployment Guide: https://gofastmcp.com/deployment/running-server
