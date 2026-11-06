"""Native directory-plugin entry point; pip uses the package entry point."""

from .hermes_sentry import register

__all__ = ["register"]
