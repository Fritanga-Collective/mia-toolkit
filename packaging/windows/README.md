# Windows packaging

Builds a per-user installer (`.exe`) — **on Windows** (PyInstaller can't
cross-compile from macOS, so this normally runs on the Windows CI runner).

```
packaging/windows/
├── mia-windows.spec   # PyInstaller spec -> dist/MIAToolkit/ (one-dir build)
└── installer.iss      # Inno Setup -> dist/MIA-Toolkit-Setup-<ver>.exe
```

## Build (on a Windows machine or runner)

```powershell
pip install -e ".[build]"
pyinstaller packaging\windows\mia-windows.spec --noconfirm
# Inno Setup (install via: choco install innosetup)
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\installer.iss
# -> dist\MIA-Toolkit-Setup-0.1.0.exe
```

The installer is **per-user** (`PrivilegesRequired=lowest`) — no admin prompt,
installs to `%LOCALAPPDATA%\Programs`.

## Signing — currently **unsigned** on Windows

**The Windows installer is not code-signed yet.** Windows has no notarization
service like Apple's; the equivalent is an **Authenticode signature** plus
reputation. Until we have a certificate, the installer will trigger a Microsoft
**SmartScreen** "Windows protected your PC / unknown publisher" prompt.

### Installing the unsigned build (for users)

It's safe to install — you just have to tell Windows to proceed:

1. Download `MIA-Toolkit-Setup-<version>.exe` from the
   [Releases page](https://github.com/Fritanga-Collective/mia-toolkit/releases/latest).
2. Run it. If SmartScreen appears, click **More info → Run anyway**.
3. (Optional) Verify the download matches the SHA-256 published in the release's
   `version.json` before running.

> Prefer a managed channel? We're working toward winget/package-manager
> distribution; until then the Releases page is the source of truth.

### Why unsigned (status, 2026-06-10)

Both viable signing paths are currently closed:

- **Microsoft Trusted Signing** — identity validation only offered in the
  **USA / Canada / EU / UK**, unavailable from Mexico (individuals and orgs
  alike). Runbook kept dormant internally in case regions expand.
- **SignPath Foundation** (free OSS signing) — **application rejected
  (2026-06-10)** on public-traction grounds (stars/forks/references/articles),
  explicitly *not* a quality judgment. They invite reapplication once the
  project has broader recognition, so this is parked, not closed.

Options under review: reapply to SignPath after growing traction, or purchase a
certificate (e.g. **Certum Open Source Code Signing** — individual validation,
cloud-token signing that works in CI). macOS builds remain signed + notarized.

### The pipeline is wired and dormant

`release.yml` is already set up to sign when a certificate exists: after Inno
Setup builds the installer it uploads the unsigned exe as a CI artifact, submits
a SignPath signing request, swaps in the signed result, and fails the build
unless `Get-AuthenticodeSignature` reports `Valid`. The publish job only picks up
the final artifact — an unsigned intermediate can't ship through that path.
Everything is gated on the `SIGNPATH_API_TOKEN` secret; it's **unset**, so the
signing step is skipped and the plain (unsigned) installer ships, as today.

### If/when we get a signing path

For SignPath (on a future approval): create/confirm the **project**
(`mia-toolkit`), its **artifact configuration** (the installer .exe), and the
**`release-signing` policy**; create a CI user API token; add the
`SIGNPATH_API_TOKEN` secret + `SIGNPATH_ORG_ID` variable (slugs must match the
workflow); verify the `signpath/github-action-submit-signing-request` pin; add
the SignPath attribution line to `README.md`; tag a release → signed installer
or loud failure. For a **purchased cert**, swap the SignPath step for the CA's
cloud-signing action (e.g. Certum SimplySign / SSL.com eSigner) behind the same
gate. Either way, reputation **warms up over downloads** — only an EV cert
removes the SmartScreen prompt instantly.
