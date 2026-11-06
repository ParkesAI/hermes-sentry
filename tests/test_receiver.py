"""Observable HTTP boundaries, using generated keys and synthetic Sentry events only."""

import hashlib
import hmac
import io
import json
import secrets
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hermes_sentry.receiver import MAX_BODY_BYTES, Settings, create_app


class ReceiverTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.secret = secrets.token_hex(32)
        self.deliveries = []
        self.upstream_status = 202
        self.redirect_followed = False

        async def upstream(request):
            body = await request.read()
            timestamp = request.headers["X-Webhook-Timestamp"]
            expected = hmac.new(
                self.secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
            ).hexdigest()
            self.assertEqual(request.headers["X-Webhook-Signature-V2"], expected)
            self.deliveries.append((body, dict(request.headers)))
            return web.json_response(
                {"status": "accepted"},
                status=self.upstream_status,
                headers={"Location": "/unexpected"} if self.upstream_status == 302 else {},
            )

        async def unexpected(request):
            self.redirect_followed = True
            return web.json_response({"status": "accepted"}, status=202)

        app = web.Application()
        app.router.add_post("/webhooks/sentry", upstream)
        app.router.add_route("*", "/unexpected", unexpected)
        self.backend = TestServer(app, host="127.0.0.1")
        await self.backend.start_server()
        self.addAsyncCleanup(self.backend.close)
        self.settings = Settings(
            secret=self.secret,
            project_ids=frozenset({"101"}),
            upstream_port=self.backend.port,
        )
        self.client = TestClient(TestServer(create_app(self.settings), host="127.0.0.1"))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)
        self.body = json.dumps(
            {
                "action": "triggered",
                "data": {"event": {"project": 101, "title": "Synthetic error"}},
            },
            indent=2,
        ).encode()

    def headers(self, body=None, **extra):
        signature = hmac.new(
            self.secret.encode(), self.body if body is None else body, hashlib.sha256
        ).hexdigest()
        return {
            "Sentry-Hook-Signature": signature,
            "Sentry-Hook-Resource": "event_alert",
            **extra,
        }

    async def test_signed_bytes_survive_and_identity_cannot_be_spoofed(self):
        for supplied_id in ["first-forged-id", "second-forged-id"]:
            response = await self.client.post(
                "/sentry",
                data=self.body,
                headers=self.headers(**{"X-GitHub-Delivery": supplied_id}),
            )
            self.assertEqual(response.status, 202)
        self.assertEqual(len(self.deliveries), 2)
        expected_id = "sentry-" + hashlib.sha256(self.body).hexdigest()
        for body, headers in self.deliveries:
            self.assertEqual(body, self.body)
            self.assertEqual(headers["X-GitHub-Delivery"], expected_id)
            self.assertEqual(headers["X-GitHub-Event"], "sentry.event_alert")
            self.assertNotIn("Authorization", headers)

    async def test_unsigned_wrong_key_and_tampered_requests_never_reach_upstream(self):
        cases = [({}, self.body), (self.headers(), self.body + b" ")]
        cases.append(({**self.headers(), "Sentry-Hook-Signature": "0" * 64}, self.body))
        for headers, body in cases:
            with self.subTest(headers=list(headers)):
                response = await self.client.post("/sentry", data=body, headers=headers)
                self.assertEqual(response.status, 401)
        self.assertFalse(self.deliveries)

    async def test_signed_other_project_and_non_alert_resources_are_ignored(self):
        bodies = [
            b'{"data":{"event":{"project":202}}}',
            b'{"data":{"event":{"project":true}}}',
            b'{"data":{"event":{"project":{"id":101}}}}',
            b"{}",
        ]
        for body in bodies:
            response = await self.client.post("/sentry", data=body, headers=self.headers(body))
            self.assertEqual(response.status, 200)
            self.assertEqual((await response.json())["status"], "ignored")
        response = await self.client.post(
            "/sentry",
            data=self.body,
            headers=self.headers(**{"Sentry-Hook-Resource": "installation"}),
        )
        self.assertEqual(response.status, 200)
        self.assertFalse(self.deliveries)

    async def test_signed_invalid_json_fails_without_dispatch(self):
        for body in [b"not-json", b"[]", b"\xff"]:
            response = await self.client.post("/sentry", data=body, headers=self.headers(body))
            self.assertEqual(response.status, 400)
        self.assertFalse(self.deliveries)

    async def test_backend_errors_and_redirects_are_retryable_not_acknowledged(self):
        for status in [401, 429, 500, 302]:
            self.upstream_status = status
            response = await self.client.post("/sentry", data=self.body, headers=self.headers())
            self.assertEqual(response.status, 503)
        self.assertFalse(self.redirect_followed)

    async def test_backend_connection_failure_is_retryable(self):
        await self.backend.close()
        response = await self.client.post("/sentry", data=self.body, headers=self.headers())
        self.assertEqual(response.status, 503)

    async def test_size_limit_and_route_scope(self):
        body = b" " * (MAX_BODY_BYTES + 1)
        response = await self.client.post(
            "/sentry", data=io.BytesIO(body), headers=self.headers(body)
        )
        self.assertEqual(response.status, 413)
        self.assertEqual((await self.client.get("/sentry")).status, 405)
        self.assertEqual((await self.client.post("/other")).status, 404)
        response = await self.client.get("/health")
        self.assertEqual(await response.json(), {"status": "ok"})
        self.assertFalse(self.deliveries)


class SettingsTest(unittest.TestCase):
    def test_invalid_settings_fail_closed_and_secret_is_not_in_repr(self):
        secret = secrets.token_hex(32)
        valid = {"secret": secret, "project_ids": frozenset({"101"})}
        self.assertNotIn(secret, repr(Settings(**valid)))
        for update in [
            {"secret": ""},
            {"secret": "<Sentry integration Client Secret>"},
            {"project_ids": frozenset()},
            {"project_ids": frozenset({"not-an-id"})},
            {"host": "0.0.0.0"},
            {"port": 0},
            {"port": True},
            {"upstream_port": 8650},
            {"route": "../other"},
        ]:
            with self.subTest(fields=list(update)):
                with self.assertRaises(ValueError):
                    Settings(**{**valid, **update})


if __name__ == "__main__":
    unittest.main()
