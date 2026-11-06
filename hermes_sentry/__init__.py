"""An installable Sentry ingress platform for Hermes Agent."""


def register(ctx):
    from .adapter import SentryAdapter

    ctx.register_platform(
        name="sentry",
        label="Sentry webhooks",
        adapter_factory=SentryAdapter,
        check_fn=lambda: True,
        install_hint="Configure a Sentry signing secret and allowed project IDs",
        dashboard_description="Receive signed Sentry issue-alert webhooks on loopback",
        emoji="🚨",
    )
