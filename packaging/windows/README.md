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

## Architecture / Windows on ARM

The build is **x64**. The installer sets `ArchitecturesAllowed=x64compatible`, so it
also installs on **Windows 11 on ARM**, where the app runs under Windows' built-in
x64 emulation. (With plain `x64` the installer *refuses* to run on ARM —
"This program does not support the version of Windows your computer is running" —
before emulation can help.) `x64compatible` requires **Inno Setup 6.3+** (the CI
`choco install innosetup` is current; install 6.3+ locally). A **native ARM64**
build is a possible later step — not shipped yet.

## Signing — SignPath Foundation (the Windows "notarization")

Windows has no notarization service like Apple's; the equivalent is an
**Authenticode signature** plus reputation, so SmartScreen stops flagging
"unknown publisher." We sign via **SignPath Foundation** — free code signing for
open-source projects, with native GitHub Actions integration. The visible
publisher on the certificate is **"SignPath Foundation"**.

> Why not Microsoft Trusted Signing? Its identity validation is only offered in
> the **USA / Canada / EU / UK** — unavailable from Mexico (for individuals and
> orgs alike). The full Trusted Signing runbook is kept dormant internally in
> case Microsoft expands regions.

The release workflow is **already wired**: after Inno Setup builds the
installer, it uploads the unsigned exe as a CI artifact, submits a SignPath
signing request, swaps in the signed result, and fails the build unless
`Get-AuthenticodeSignature` reports `Valid`. The publish job only ever picks up
the final artifact — the unsigned intermediate can't ship. Everything is gated
on the `SIGNPATH_API_TOKEN` secret, so builds stay unsigned until approval.

### One-time setup

1. **Apply** at signpath.org → Open Source program (SignPath Foundation).
   Requirements we already meet: public repo, OSI license (MIT, see `LICENSE`),
   builds produced by GitHub Actions from the repo. Review takes ~1–3 weeks.
2. On approval, in SignPath create/confirm the **project** (`mia-toolkit`), its
   **artifact configuration** (the installer .exe), and the
   **`release-signing` policy**; create a **CI user API token**.
3. Add to GitHub: secret **`SIGNPATH_API_TOKEN`** (the gate) and repo variable
   **`SIGNPATH_ORG_ID`** (the organization id). Slugs in the workflow must match
   the project/policy names above; verify the
   `signpath/github-action-submit-signing-request` version pin.
4. Add the SignPath attribution to the README (Foundation requirement), e.g.
   "Free code signing provided by [SignPath.io](https://signpath.io), certificate
   by SignPath Foundation."
5. Tag a release → the Windows job ships a signed installer or fails loudly.

Notes:
- **Reputation still warms up over downloads** — a correct signature reduces but
  doesn't instantly remove SmartScreen prompts.
- Want deep-signing of the inner app exe too? Configure it in the SignPath
  artifact configuration (or add a second signing request before Inno packs it).
