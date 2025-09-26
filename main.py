# main.py
"""FastMCP time server + flexible GitHub repo tools (read/write/list/delete via PAT) + Render deploy hook."""
from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastmcp import FastMCP

__all__ = ["app", "mcp"]

mcp = FastMCP("time-mcp-server")

# =========================
# Time / TZ helpers
# =========================

CITY_TO_TZ: Dict[str, str] = {
    # DACH
    "berlin": "Europe/Berlin",
    "münchen": "Europe/Berlin",
    "munich": "Europe/Berlin",
    "hamburg": "Europe/Berlin",
    "köln": "Europe/Berlin",
    "cologne": "Europe/Berlin",
    "frankfurt": "Europe/Berlin",
    "stuttgart": "Europe/Berlin",
    "leipzig": "Europe/Berlin",
    "dresden": "Europe/Berlin",
    "zürich": "Europe/Zurich",
    "zurich": "Europe/Zurich",
    "wien": "Europe/Vienna",
    "vienna": "Europe/Vienna",
    # Europa
    "madrid": "Europe/Madrid",
    "barcelona": "Europe/Madrid",
    "paris": "Europe/Paris",
    "london": "Europe/London",
    "dublin": "Europe/Dublin",
    "lisbon": "Europe/Lisbon",
    "roma": "Europe/Rome",
    "rome": "Europe/Rome",
    "milano": "Europe/Rome",
    "milan": "Europe/Rome",
    "prague": "Europe/Prague",
    "praha": "Europe/Prague",
    "budapest": "Europe/Budapest",
    "warsaw": "Europe/Warsaw",
    "moscow": "Europe/Moscow",
    "moskau": "Europe/Moscow",
    "st. petersburg": "Europe/Moscow",
    "istanbul": "Europe/Istanbul",
    "athens": "Europe/Athens",
    "oslo": "Europe/Oslo",
    "stockholm": "Europe/Stockholm",
    "helsinki": "Europe/Helsinki",
    # Nordamerika
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "toronto": "America/Toronto",
    "mexico city": "America/Mexico_City",
    # Südamerika
    "são paulo": "America/Sao_Paulo",
    "sao paulo": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "santiago": "America/Santiago",
    "bogotá": "America/Bogota",
    "bogota": "America/Bogota",
    "lima": "America/Lima",
    # Asien
    "tokyo": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "kolkata": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    # Ozeanien / Afrika
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland",
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "nairobi": "Africa/Nairobi",
}

def _normalize_key(s: str) -> str:
    return s.strip().replace("_", " ").replace("-", " ").casefold()

def _resolve_timezone(timezone_name: Optional[str] = None, city: Optional[str] = None) -> ZoneInfo:
    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            pass
    if city:
        key = _normalize_key(city)
        for k in (key, key.replace(".", "")):
            if k in CITY_TO_TZ:
                try:
                    return ZoneInfo(CITY_TO_TZ[k])
                except ZoneInfoNotFoundError:
                    break
    return ZoneInfo("UTC")

@mcp.tool(
    description=(
        "Gibt die aktuelle Zeit zurück. Ohne Parameter in UTC. "
        "Optional per IANA-Zeitzone ('Europe/Madrid') oder Städtenamen ('Madrid')."
    )
)
def current_time(timezone_name: str | None = None, city: str | None = None, as_utc: bool = False) -> str:
    if as_utc:
        return datetime.now(timezone.utc).isoformat()
    tz = _resolve_timezone(timezone_name=timezone_name, city=city)
    return datetime.now(tz).isoformat()

# =========================
# GitHub tools (via PAT)
# =========================

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

class GitHubClient:
    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mcp-time-server/1.1",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=20.0, headers=self._headers, base_url=GITHUB_API_BASE)

    # -------- Contents API (files/dirs) --------
    def get_content(self, owner: str, repo: str, path: str, ref: Optional[str] = None) -> dict:
        params = {"ref": ref} if ref else None
        with self._client() as c:
            r = c.get(f"/repos/{owner}/{repo}/contents/{path}", params=params)
            r.raise_for_status()
            return r.json()

    def put_content(
        self,
        owner: str,
        repo: str,
        path: str,
        content_text: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
        author: Optional[dict] = None,
        committer: Optional[dict] = None,
    ) -> dict:
        payload: Dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content_text.encode("utf-8")).decode("ascii"),
        }
        if branch:
            payload["branch"] = branch
        if sha:
            payload["sha"] = sha
        if author:
            payload["author"] = author
        if committer:
            payload["committer"] = committer
        with self._client() as c:
            r = c.put(f"/repos/{owner}/{repo}/contents/{path}", json=payload)
            r.raise_for_status()
            return r.json()

    def delete_content(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> dict:
        payload: Dict[str, Any] = {"message": message}
        if branch:
            payload["branch"] = branch
        if sha:
            payload["sha"] = sha
        with self._client() as c:
            r = c.delete(f"/repos/{owner}/{repo}/contents/{path}", json=payload)
            r.raise_for_status()
            return r.json()

    # -------- Trees API (recursive listing) --------
    def get_tree(self, owner: str, repo: str, tree_sha_or_ref: str, recursive: bool = True) -> dict:
        params = {"recursive": "1"} if recursive else None
        with self._client() as c:
            r = c.get(f"/repos/{owner}/{repo}/git/trees/{tree_sha_or_ref}", params=params)
            r.raise_for_status()
            return r.json()

def _require_token() -> str:
    token = os.getenv(GITHUB_TOKEN_ENV)
    if not token:
        raise RuntimeError(
            f"Missing {GITHUB_TOKEN_ENV}. "
            "Set a GitHub Personal Access Token with appropriate repo scope in your deployment environment."
        )
    return token

# ---- Tools: read / write single file ----

@mcp.tool(
    description=(
        "Liest eine Datei aus einem GitHub-Repository. "
        "Parameter: owner, repo, path, optional ref (Branch/Tag/SHA). "
        "Gibt Base64-kodierte 'content' zurück, falls type='file'."
    )
)
def github_read_file(owner: str, repo: str, path: str, ref: str | None = None) -> dict:
    client = GitHubClient(_require_token())
    data = client.get_content(owner, repo, path, ref=ref)
    return {
        "type": data.get("type"),
        "name": data.get("name"),
        "path": data.get("path"),
        "sha": data.get("sha"),
        "size": data.get("size"),
        "encoding": data.get("encoding"),
        "content": data.get("content"),
        "download_url": data.get("download_url"),
        "html_url": data.get("html_url"),
        "_ref": ref,
    }

@mcp.tool(
    description=(
        "Erstellt/aktualisiert eine Datei in einem GitHub-Repository. "
        "Parameter: owner, repo, path, content (reiner Text), message. "
        "Optional: branch, sha (zum Update bestehender Dateien), author/committer."
    )
)
def github_write_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
    author_name: str | None = None,
    author_email: str | None = None,
    committer_name: str | None = None,
    committer_email: str | None = None,
) -> dict:
    client = GitHubClient(_require_token())
    author = {"name": author_name, "email": author_email} if author_name and author_email else None
    committer = {"name": committer_name, "email": committer_email} if committer_name and committer_email else None
    data = client.put_content(
        owner=owner,
        repo=repo,
        path=path,
        content_text=content,
        message=message,
        branch=branch,
        sha=sha,
        author=author,
        committer=committer,
    )
    commit = data.get("commit") or {}
    content_info = data.get("content") or {}
    return {
        "path": content_info.get("path"),
        "sha": content_info.get("sha"),
        "branch": branch,
        "commit_sha": (commit.get("sha") if isinstance(commit, dict) else None),
        "commit_url": (commit.get("html_url") if isinstance(commit, dict) else None),
    }

# ---- Tools: delete file ----

@mcp.tool(
    description=(
        "Löscht eine Datei in einem GitHub-Repository. "
        "Parameter: owner, repo, path, message (Commit-Message). Optional: branch, sha. "
        "Wenn 'sha' fehlt, wird versucht, sie automatisch zu ermitteln."
    )
)
def github_delete_file(
    owner: str,
    repo: str,
    path: str,
    message: str,
    branch: str | None = None,
    sha: str | None = None,
) -> dict:
    client = GitHubClient(_require_token())
    use_sha = sha
    if not use_sha:
        try:
            cur = client.get_content(owner, repo, path, ref=branch)
            use_sha = cur.get("sha")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Could not resolve sha for delete: {e.response.status_code} {e.response.text}")
    data = client.delete_content(owner, repo, path, message=message, branch=branch, sha=use_sha)
    commit = data.get("commit") or {}
    return {
        "deleted_path": path,
        "branch": branch,
        "commit_sha": (commit.get("sha") if isinstance(commit, dict) else None),
        "commit_url": (commit.get("html_url") if isinstance(commit, dict) else None),
    }

# ---- Tools: list directory & tree ----

@mcp.tool(
    description=(
        "Listet den Inhalt eines Verzeichnisses über die Contents API. "
        "Parameter: owner, repo, optional path (Standard: '' für Repo-Root), optional ref. "
        "Gibt eine Liste aus Files/Dirs mit Typ, Pfad, Größe (bei Dateien)."
    )
)
def github_list_dir(owner: str, repo: str, path: str | None = "", ref: str | None = None) -> List[dict]:
    client = GitHubClient(_require_token())
    path_param = path or ""
    data = client.get_content(owner, repo, path_param, ref=ref)
    items = data if isinstance(data, list) else [data]
    result: List[dict] = []
    for it in items:
        result.append({
            "type": it.get("type"),
            "name": it.get("name"),
            "path": it.get("path"),
            "sha": it.get("sha"),
            "size": it.get("size"),
            "html_url": it.get("html_url"),
            "download_url": it.get("download_url"),
        })
    return result

@mcp.tool(
    description=(
        "Listet den kompletten Git-Tree (rekursiv) über die Trees API. "
        "Parameter: owner, repo, ref (Branch/Tag/SHA). Optional: recursive=True, path_prefix zum Filtern."
    )
)
def github_list_tree(
    owner: str,
    repo: str,
    ref: str,
    recursive: bool = True,
    path_prefix: str | None = None,
) -> dict:
    client = GitHubClient(_require_token())
    tree = client.get_tree(owner, repo, ref, recursive=recursive)
    entries = tree.get("tree", [])
    if path_prefix:
        pref = path_prefix.rstrip("/") + "/"
        entries = [e for e in entries if e.get("path", "").startswith(pref)]
    return {
        "truncated": tree.get("truncated"),
        "sha": tree.get("sha"),
        "count": len(entries),
        "entries": entries,  # each: {path, mode, type, sha, size}
    }

# =========================
# Render.com: Deploy-Webhook
# =========================

RENDER_DEPLOY_HOOK_ENV = "RENDER_DEPLOY_HOOK_URL"

def _resolve_render_webhook(full_url: str | None, service_id: str | None, key: str | None) -> str:
    """
    Liefert die endgültige Webhook-URL:
    - 1) explizit übergeben (full_url) ODER
    - 2) aus service_id + key gebaut ODER
    - 3) aus ENV RENDER_DEPLOY_HOOK_URL
    """
    if full_url:
        return full_url.strip()
    if service_id and key:
        return f"https://api.render.com/deploy/{service_id.strip()}?key={key.strip()}"
    env_url = os.getenv(RENDER_DEPLOY_HOOK_ENV)
    if env_url:
        return env_url.strip()
    raise RuntimeError(
        "Keine Render-Webhook-URL gefunden. Entweder 'full_url' übergeben, "
        "oder 'service_id' + 'key', oder setze die Umgebungsvariable RENDER_DEPLOY_HOOK_URL."
    )

@mcp.tool(
    description=(
        "Löst ein Deployment auf Render.com aus (Deploy Hook). Standard: POST auf den Webhook. "
        "Parameter: full_url ODER (service_id + key). Fallback: ENV 'RENDER_DEPLOY_HOOK_URL'."
    )
)
def render_trigger_deploy(
    full_url: str | None = None,
    service_id: str | None = None,
    key: str | None = None,
    method: str | None = "POST",
    timeout_seconds: float | int = 20,
) -> dict:
    """
    Triggert den Deploy-Hook.
    Gibt Statuscode, Text/JSON und die effektive URL zurück.
    """
    url = _resolve_render_webhook(full_url=full_url, service_id=service_id, key=key)
    meth = (method or "POST").upper()

    try:
        with httpx.Client(timeout=float(timeout_seconds), follow_redirects=True) as c:
            if meth == "POST":
                r = c.post(url, json={})
            elif meth == "GET":
                r = c.get(url)
            else:
                raise ValueError(f"Unsupported method: {meth} (verwende POST oder GET)")

        try:
            body = r.json()
        except Exception:
            body = r.text

        return {
            "ok": r.is_success,
            "status_code": r.status_code,
            "url": str(r.request.url),
            "method": meth,
            "headers_sent": dict(r.request.headers),
            "response": body,
        }
    except httpx.HTTPError as e:
        return {
            "ok": False,
            "error": f"http_error: {type(e).__name__}: {e}",
            "url": url,
            "method": meth,
        }

# =========================
# ASGI
# =========================

app = mcp.http_app()

def create_app() -> object:
    return app

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
