"""Hermes owns receiver startup and shutdown through its public platform contract."""

from aiohttp import web
from gateway.config import Platform
from gateway.platforms.base import BasePlatformAdapter, SendResult

from .receiver import Settings, create_app


class SentryAdapter(BasePlatformAdapter):
    def __init__(self, config, **kwargs):
        super().__init__(config=config, platform=Platform("sentry"))
        extra = config.extra or {}
        projects = extra.get("project_ids", [])
        if not isinstance(projects, list) or any(type(p) not in (str, int) for p in projects):
            raise ValueError("project_ids must be a list of numeric Sentry project IDs")
        self.settings = Settings(
            secret=config.token or "",
            project_ids=frozenset(str(p) for p in projects),
            host=extra.get("host", "127.0.0.1"),
            port=extra.get("port", 8650),
            upstream_port=extra.get("upstream_port", 8644),
            route=extra.get("route", "sentry"),
            profile=extra.get("profile"),
        )
        self.runner = None

    async def connect(self, *, is_reconnect=False):
        if self.runner is not None:
            return True
        runner = web.AppRunner(create_app(self.settings), access_log=None)
        await runner.setup()
        try:
            await web.TCPSite(runner, self.settings.host, self.settings.port).start()
        except Exception:
            await runner.cleanup()
            raise
        self.runner = runner
        self._mark_connected()
        return True

    async def disconnect(self):
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None
        self._mark_disconnected()

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        return SendResult(success=False, error="Sentry ingress has no outbound messaging channel")

    async def get_chat_info(self, chat_id):
        return {"name": "Sentry webhook ingress", "type": "channel"}
