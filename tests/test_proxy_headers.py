"""Derrière un proxy qui termine TLS, les pages lient leurs fichiers en HTTPS.

Les templates lient leurs CSS par `url_for('static', …)`, une URL absolue
construite avec le schéma que voit l'application. Derrière le proxy, ce schéma
est `http`, sauf si uvicorn lit `X-Forwarded-Proto`, ce qu'il ne fait que pour
les adresses de `FORWARDED_ALLOW_IPS`. Les requêtes de test viennent de
l'adresse `testclient` : comme un proxy dans un conteneur, il n'est jamais
`127.0.0.1`.
"""

import asyncio
import re
from pathlib import Path

import uvicorn

from oceens import main

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"

BEHIND_TLS = {"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.7"}


def served_by_run(monkeypatch, forwarded_allow_ips):
    """L'application telle que `run()` la sert, avec ce réglage."""
    if forwarded_allow_ips is None:
        monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    else:
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", forwarded_allow_ips)
    config = uvicorn.Config("oceens.main:app", **main.SERVER_OPTIONS)
    config.load()
    return config.loaded_app


def get(app, path, headers):
    """Une requête HTTP sur `app`, envoyée telle qu'uvicorn la lui passe."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"oceens.example")]
        + [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("testclient", 50000),
        "server": ("oceens.example", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = sent[0]["status"]
    body = b"".join(m.get("body", b"") for m in sent[1:]).decode()
    return status, body


def stylesheets(app, headers=None):
    status, page = get(app, "/", headers or {})
    assert status == 200
    links = re.findall(r'href="([^"]*\.css)"', page)
    assert links
    return links


def image_forwarded_allow_ips():
    """La valeur de `FORWARDED_ALLOW_IPS` que l'image fixe."""
    match = re.search(r'FORWARDED_ALLOW_IPS="([^"]*)"', DOCKERFILE.read_text())
    assert match, "le Dockerfile ne fixe pas FORWARDED_ALLOW_IPS"
    return match.group(1)


def test_the_image_links_its_css_over_https_behind_a_tls_proxy(monkeypatch):
    app = served_by_run(monkeypatch, image_forwarded_allow_ips())
    for link in stylesheets(app, BEHIND_TLS):
        assert link.startswith("https://"), link


def test_an_untrusted_proxy_is_not_believed(monkeypatch):
    app = served_by_run(monkeypatch, None)
    for link in stylesheets(app, BEHIND_TLS):
        assert link.startswith("http://"), link


def test_a_trusted_proxy_changes_nothing_for_a_plain_http_request(monkeypatch):
    app = served_by_run(monkeypatch, image_forwarded_allow_ips())
    for link in stylesheets(app):
        assert link.startswith("http://"), link
