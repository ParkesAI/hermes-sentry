"""Sentry authentication and a bounded bridge to native Hermes webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
from dataclasses import dataclass, field

from aiohttp import ClientError, ClientSession, ClientTimeout, web

LOG = logging.getLogger(__name__)
CLIENT = web.AppKey("upstream_client", ClientSession)
MAX_BODY_BYTES = 1_048_576


@dataclass(frozen=True)
class Settings:
    secret: str = field(repr=False)
    project_ids: frozenset[str]
    host: str = "127.0.0.1"
    port: int = 8650
    upstream_port: int = 8644
    route: str = "sentry"

    def __post_init__(self):
        if (
            not isinstance(self.secret, str)
            or len(self.secret) < 32
            or any(c.isspace() or c in "<>" for c in self.secret)
        ):
            raise ValueError("A Sentry signing secret of at least 32 characters is required")
        if not self.project_ids or any(
            not isinstance(p, str) or not re.fullmatch(r"[0-9]+", p) for p in self.project_ids
        ):
            raise ValueError("Provide an explicit allowlist of numeric Sentry project IDs")
        if self.host not in {"127.0.0.1", "::1"}:
            raise ValueError("The receiver must bind to a loopback address")
        for port in (self.port, self.upstream_port):
            if type(port) is not int or not 1 <= port <= 65535:
                raise ValueError("Ports must be integers from 1 to 65535")
        if self.port == self.upstream_port:
            raise ValueError("Receiver and native webhook ports must differ")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.route):
            raise ValueError("Invalid native webhook route name")

    @property
    def upstream_url(self) -> str:
        return f"http://127.0.0.1:{self.upstream_port}/webhooks/{self.route}"


def create_app(settings: Settings) -> web.Application:
    """Own the HTTP client for exactly the lifetime of this receiver."""
    app = web.Application(client_max_size=MAX_BODY_BYTES)

    async def client_lifecycle(app):
        async with ClientSession(timeout=ClientTimeout(total=5), trust_env=False) as client:
            app[CLIENT] = client
            yield

    async def health(request):
        return web.json_response({"status": "ok"})

    async def receive(request):
        signature = request.headers.get("Sentry-Hook-Signature", "")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", signature):
            return web.json_response({"error": "invalid signature"}, status=401)
        body = await request.read()
        expected = hmac.new(settings.secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature.lower(), expected):
            return web.json_response({"error": "invalid signature"}, status=401)
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"error": "invalid JSON"}, status=400)
        if not isinstance(payload, dict):
            return web.json_response({"error": "expected a JSON object"}, status=400)
        resource = request.headers.get("Sentry-Hook-Resource", "")
        if resource != "event_alert":
            return web.json_response({"status": "ignored", "reason": "unsupported resource"})
        data = payload.get("data")
        event = data.get("event") if isinstance(data, dict) else None
        project = event.get("project") if isinstance(event, dict) else None
        if type(project) not in (str, int) or str(project) not in settings.project_ids:
            return web.json_response({"status": "ignored", "reason": "project not allowed"})
        # Preserve signed bytes; derive identity rather than trusting caller headers.
        timestamp = str(int(time.time()))
        native_signature = hmac.new(
            settings.secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature-V2": native_signature,
            "X-Webhook-Timestamp": timestamp,
            "X-GitHub-Event": "sentry.event_alert",
            "X-GitHub-Delivery": "sentry-" + hashlib.sha256(body).hexdigest(),
        }
        try:
            async with app[CLIENT].post(
                settings.upstream_url, data=body, headers=headers, allow_redirects=False
            ) as response:
                if response.status >= 300:
                    LOG.warning("Native webhook receiver returned HTTP %s", response.status)
                    return web.json_response({"error": "native receiver unavailable"}, status=503)
                # Acceptance is not agent completion; native Hermes owns durable processing.
                return web.json_response({"status": "accepted"}, status=202)
        except (ClientError, TimeoutError):
            LOG.warning("Native webhook receiver unavailable")
            return web.json_response({"error": "native receiver unavailable"}, status=503)

    app.cleanup_ctx.append(client_lifecycle)
    app.router.add_get("/health", health)
    app.router.add_post("/sentry", receive)
    return app
