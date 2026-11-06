# Verification and compatibility

## Current evidence

The initial version is under qualification. Passing the isolated tests does not
establish a live Sentry delivery, a connected Hermes gateway, or completed agent
analysis. This document will record the completed release checks without host
addresses, credentials, project/organization identities or deployment settings.

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
