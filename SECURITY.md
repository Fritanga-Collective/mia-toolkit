# Security Policy

## Reporting a vulnerability

Please report suspected security issues privately to **mia-tools@fritanga.co**.

Include enough detail to reproduce (affected version, OS, and steps or a proof
of concept). We aim to acknowledge within a few days. Please give us a
reasonable chance to release a fix before any public disclosure.

We don't run a paid bug-bounty program, but we're glad to credit reporters in
the release notes unless you prefer to stay anonymous.

## Supported versions

Security fixes target the **latest release**. Please reproduce on the current
version before reporting.

## Scope and design

MIA Toolkit runs fully on your computer:

- No server, no account, no telemetry. The app's only network action is the
  user-initiated **Check for Updates**, which fetches one static version file
  and carries no personal data or identifiers.
- Your medical images and their metadata never leave your machine.

A summary of our latest review and the defenses in place is in
[`docs/SECURITY-AUDIT.md`](docs/SECURITY-AUDIT.md).

## Verifying downloads

Each release publishes SHA-256 checksums (see `version.json` on the website and
the release assets). macOS builds are signed and notarized by Apple; you can
confirm with `spctl --assess --type execute -vv "MIA Toolkit.app"`.
