# Verification and compatibility

## Current evidence

Qualification completed on 2026-11-06 against Hermes Agent 0.23.0, commit
`2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`.

- CI passes on Python 3.11–3.14: eight HTTP/configuration tests, lint, format,
  wheel/source builds and distribution checks. A separate job runs two lifecycle
  and native-signature contract tests against the pinned real Hermes SDK.
- A plugin-manager installation started the platform in an isolated gateway.
  A signed synthetic alert produced one user message and one completed assistant
  response. Invalid signatures returned 401. Replaying identical bytes with
  different caller delivery headers did not create another activation.
- A production gateway received a Sentry **built-in test action** over public
  HTTPS. Sentry's delivery record reported `event_alert.triggered` and HTTP 202.
  The corresponding Hermes session contained one user message, one completed
  assistant response and zero tool calls. This exercised Sentry's own signing
  and delivery, rather than a locally signed fixture.
- The public ingress rejected an unsigned POST with 401; the health endpoint
  and unrelated paths were not published. Both plugin and native listeners
  were bound to loopback. The gateway's existing private services remained
  available after restart.
- Wheel metadata/discovery was checked in a clean environment. Source and
  distributions were scanned for secrets and reviewed for deployment identifiers.

These checks establish delivery and analysis with a controlled provider test,
not a production incident, a load test, or an independent security audit. The
workflow is configured for new and regressed errors; sustained production
operation and every Sentry/Hermes version combination have not been qualified.
Metric alerts are not supported.

### Known Hermes packaging limitation

Hermes 0.23.0 combines enabled profile dependencies into a uv workspace. Two
independently installed buildable copies of `hermes-sentry` collide on the Python
distribution name. Qualification used a temporary ingress profile, removed its
installation, then enabled a single production ingress profile. Multi-profile
installation is not supported by this release. No generated Hermes workspace
files were modified to bypass this limitation.

## Repeatable release checks

1. Run every development command from the README on a clean checkout.
2. Run `hermes plugins doctor .` with a supported Hermes installation. Confirm
   that the `sentry` platform is registered through the public plugin API.
3. Build the wheel and source archive; verify metadata and package contents with
   `scripts/check_distribution.py`. Install the wheel into an isolated environment
   and verify its `hermes_agent.plugins` entry point resolves to this package.
4. Install the exact candidate commit through the Hermes plugin manager. Use a
   protected synthetic local configuration, not production credentials in the
   repository. Start and stop the platform through the gateway and confirm the
   loopback port is released on shutdown.
5. Send a signed synthetic Sentry issue alert through the plugin into a real
   native webhook route. Confirm native admission and a completed agent response.
6. Replay the exact body with changed caller delivery headers. Confirm one
   logical native delivery/agent activation, not two. Send unsigned and tampered
   requests and confirm they create no session.
7. Confirm an unapproved project does not dispatch and a native outage yields a
   retryable failure. Confirm only the intended HTTPS path is publicly reachable.
8. Exercise an actual Sentry test delivery if available, then confirm its source
   and actual Hermes result. Record this separately from a locally signed fixture.
9. Scan the complete working tree, distributions and Git history for secrets and
   deployment identifiers. Use a public contribution identity in Git metadata.
10. Release a reviewed immutable commit only after CI passes. Attach build
    artifacts/checksums and describe any remaining coverage limitations.

## Repository quality benchmarks

The project structure was compared with these public repositories:

- [Nous Research's official plugins](https://github.com/NousResearch/hermes-official-plugins):
  native manifests, MIT licensing, contribution instructions and CI.
- [Inkbox's Hermes platform plugin](https://github.com/inkbox-ai/hermes-agent-plugin):
  platform lifecycle, configuration reference, setup/diagnostics, smoke-test
  instructions and security-boundary documentation. Its much broader feature set
  is not a scope target for this receiver.
- [Hermes Advisor](https://github.com/ljubomirj/hermes-advisor-plugin):
  a standalone plugin repository with a manifest, README, MIT license and scripts.

Comparison is a packaging and documentation benchmark, not a security endorsement
or proof that this plugin has equivalent operational maturity.
