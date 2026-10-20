# Security Policy

## Reporting a vulnerability

Please report suspected security issues privately, either:

- through GitHub's **private vulnerability reporting** (the "Report a
  vulnerability" button on this repo's
  [Security tab](https://github.com/Fritanga-Collective/mia-toolkit/security)), or
- by email to **support@miatools.tech**.

Please don't open a public issue for a security problem.

Include enough detail to reproduce (affected version, OS, and steps or a proof
of concept). We aim to acknowledge within a few days. Please give us a
reasonable chance to release a fix before any public disclosure.

We don't run a paid bug-bounty program, but we're glad to credit reporters in
the release notes and the advisory unless you prefer to stay anonymous.

## How we handle a report

1. **Triage:** we confirm the issue, assess severity and affected versions, and
   keep you updated.
2. **Fix:** developed privately (in a GitHub Security Advisory's private fork
   when the issue warrants one).
3. **Release:** a patched version through the normal signed-release pipeline.
4. **Disclose:** we publish a GitHub Security Advisory (with a CVE when it
   applies) and note the fix in the release notes. Institutional licensees are
   also notified by email.

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

- **Checksums:** every installer's SHA-256 is in
  `https://miatools.tech/version.json`. Releases after v0.1.13 also attach a
  `SHA256SUMS` file: `shasum -a 256 -c SHA256SUMS --ignore-missing`.
- **Provenance:** releases after v0.1.13 carry GitHub build-provenance
  attestations: `gh attestation verify <file> --repo Fritanga-Collective/mia-toolkit`.
  A CycloneDX SBOM per platform (`*.cdx.json`) is attached too.
- **macOS:** builds are signed (Apple Developer ID) and notarized by Apple since
  v0.1.5; confirm with `spctl --assess --type execute -vv "MIA Toolkit.app"`.
- **Windows:** the installer is **not code-signed yet**, so Windows SmartScreen
  shows an "unknown publisher" prompt. Use the checksum or attestation above to
  verify it.
