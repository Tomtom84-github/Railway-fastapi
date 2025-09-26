# FastMCP HTTP Time Server

Dieses Repository stellt einen minimalen [FastMCP](https://gofastmcp.com/) Server bereit,
der über den HTTP (Streamable) Transport die aktuelle Uhrzeit als Tool anbietet. Die App ist
bereit für Railway-Deployments, funktioniert aber ebenso lokal.

## 🚀 Setup

Installiere die Abhängigkeiten mit den HTTP-Extras von FastMCP:

```bash
pip install -r requirements.txt
```

Alternativ kannst du via `uv` oder Poetry arbeiten, solange `fastmcp[http]` installiert wird.

## ▶️ Startbefehle

| Umgebung                     | Befehl                                                       |
| ---------------------------- | ------------------------------------------------------------ |
| Produktion (z. B. Railway)   | `uvicorn main:app --host 0.0.0.0 --port 8000`                |
| Lokales Testen per Skript    | `python main.py`                                             |
| Optional: FastMCP CLI        | `fastmcp run main.py --transport http --host 0.0.0.0 --port 8000` |

Alle Varianten starten denselben HTTP (Streamable) Endpunkt unter `/mcp/`.

## 🛠️ Tooling

Der Server registriert ein einziges Tool `current_time`, welches den aktuellen UTC-Zeitstempel
im ISO-8601-Format zurückgibt. Der Name des Servers lautet `time-mcp-server` – das entspricht
dem Wert in `FastMCP("time-mcp-server")` und taucht auch in Client-UIs auf.

## 🔧 Deployment-Hinweise

- `railway.json` verwendet Nixpacks und startet Uvicorn automatisch mit den oben genannten Parametern.
- Für lokale Tests genügt `python main.py`; der integrierte Runner setzt `transport="http"` und lauscht
  auf allen Interfaces (`0.0.0.0`), sodass auch Container-Deployments funktionieren.

## 📚 Ressourcen

- FastMCP Dokumentation: https://gofastmcp.com/
- Streamable HTTP Deployment Guide: https://gofastmcp.com/deployment/running-server
