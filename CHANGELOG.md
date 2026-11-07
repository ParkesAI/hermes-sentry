# Changelog

## 0.1.1 — 2026-11-07

- Optional target profile forwards signed deliveries to Hermes's native
  profile-prefixed webhook URL. Omission preserves the default-profile behavior.
- Validate profile names before constructing URLs; no fallback when the configured
  destination is unavailable. Authentication and payload bytes are unchanged.

## 0.1.0 — 2026-11-06

- Initial Sentry issue-alert receiver with raw-body signature verification,
  project filtering, loopback-only binding, timestamped V2 forwarding and native
  Hermes delivery identities.
- Native platform-plugin lifecycle and standard Python wheel packaging.
- Synthetic HTTP regression tests, CI, security policy and installation docs.
- Qualified with the real Hermes 0.23.0 SDK and a provider-originated Sentry test
  delivery through public HTTPS to a completed, tool-free agent response.
