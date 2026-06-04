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

## Signing — Microsoft Trusted Signing (the Windows "notarization")

Windows has no notarization service like Apple's; the equivalent is an
**Authenticode signature** plus reputation, so SmartScreen and **Smart App
Control** stop flagging "unknown publisher." Since June 2023, OV/EV certs must
live on a hardware token/HSM (can't be a CI-friendly `.p12`), so the recommended
route is **Microsoft Trusted Signing**: cloud-based, RSA (Smart App Control
accepts it), pay-as-you-go (~$10/mo tier), no token, signs straight from CI.

The release workflow is **already wired** — it signs the bundled app exe (before
Inno packaging) *and* the final installer, then verifies the signature. It's
gated on `AZURE_CLIENT_ID`, so until the secrets exist the build stays unsigned.

### One-time setup

1. **Azure** → create a **Trusted Signing account** + a **Certificate profile**
   (Public Trust). Identity validation takes a few business days. Note the
   **endpoint** region (e.g. `https://eus.codesigning.azure.net`), the **account
   name**, and the **profile name**.
2. Create an **app registration (service principal)**; grant it the **Trusted
   Signing Certificate Profile Signer** role on the account. Note tenant id,
   client id, and a client secret.
3. Add these **GitHub repo secrets** (exact names the workflow reads):
   `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`,
   `TRUSTED_SIGNING_ENDPOINT`, `TRUSTED_SIGNING_ACCOUNT`,
   `TRUSTED_SIGNING_PROFILE`.
4. Tag a release → the Windows job signs + timestamps both exes. Verify locally
   with `Get-AuthenticodeSignature .\MIA-Toolkit-Setup-<ver>.exe` (Status =
   `Valid`) or `signtool verify /pa /v <file>`.

Notes:
- **Reputation builds over downloads** — even correctly signed installers can
  show SmartScreen briefly until Microsoft accrues reputation; an EV-backed
  identity warms up faster.
- Confirm the `azure/trusted-signing-action` version pinned in the workflow is
  current before the first signed release.
- *Legacy alternative:* if you ever have an exportable OV `.p12`, you can sign
  with `signtool.exe` (`/fd SHA256 /tr <rfc3161-timestamp> /td SHA256`) instead —
  but Trusted Signing is preferred and already wired.
