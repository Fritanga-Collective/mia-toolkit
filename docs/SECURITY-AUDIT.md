# MIA Toolkit — Security Audit (2026-06-07)

MIA Toolkit promises that your medical images **never leave your computer**,
that the app **sends nothing on its own**, and that everything runs **fully
offline**. Because the tool is aimed at patients and at clinics that must pass
an IT security review, we audited the code against those promises and published
the result here.

## Method

- **Read-only sweep** of every place the app handles untrusted input (imaging
  discs, USB folders, downloaded ZIPs, the update file) and does filesystem or
  process work.
- **Adversarial pass**: independent reviewers built malicious inputs (zip-slip
  archives, decompression bombs, symlink traps, hostile filenames and DICOM
  fields, malformed/oversized update files, TLS-downgrade redirects) and ran
  them against the real code.
- **Regression tests**: every finding — and every defense that already held —
  is locked by a test under [`tests/security/`](../tests/security). They run in
  CI on every change.

## What already held

- **Zip-slip is blocked** — extraction refuses any member whose real path
  escapes the destination (verified against `../`, `..\`, absolute paths,
  embedded NULs, and symlinked destinations).
- **Symlink ZIP members are inert** — the extractor never creates symlinks.
- **No shell** — the damaged-disc `dd` fallback and disc eject use argument
  lists, never a shell string; hostile filenames can't inject commands.
- **TLS is verified** — the update check uses a CA-verified context
  (`CERT_REQUIRED`, hostname checking on) and ships its own CA bundle so it
  stays verified inside the packaged app.
- **The request carries no identifiers** — no query string, no version, a
  constant `User-Agent`; the update check runs only when you click it.

## What we hardened in v0.1.8

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| A1 | High | A crafted DICOM field (`PatientName`, `StudyDescription`) could become a live spreadsheet **formula** in the generated inventory, running when opened. | Cell values starting with `= + - @` (or tab/CR) are stored as literal text. |
| A2 | High | `shutil.copy2` **follows symlinks**, so a crafted USB/ZIP could copy the *contents* of any file the user can read (e.g. `/etc/passwd`) into the project. | Symlinks are skipped (never followed) and recorded in the manifest. |
| A3 | High | **Nested-zip amplification** — a tiny archive could expand to many GB, and the pre-copy size estimate couldn't see it. | A cumulative uncompressed-byte budget, shared across all nesting levels. |
| A4 | Med | Single-member **decompression bomb**. | Same cumulative budget; oversized archives are refused before extraction. |
| A5 | Med | A pathological path (over the OS length limit) raised an uncaught error that **aborted the whole import** and skipped the manifest. | Each file is isolated: one bad entry is recorded as a failure; the import continues. |
| A6 | Med | The update check read the response **without a size limit** (a hostile endpoint could stream gigabytes into memory). | The read is capped; oversized responses are refused. |
| A7 | Med | A redirect could **downgrade HTTPS→HTTP** on the follow-up fetch. | Non-HTTPS redirects are refused. |
| A8 | Low | A malformed `version` value could show a **spoofed update prompt**. | `version` must be a sane digits-and-dots string or the check fails. |
| A9 | Low | An over-long ZIP member name raised a raw OS error. | Rejected with a clear message. |
| A10 | Low | A `name.zip` next to a file literally named `name_contents` (the expansion dir's name) could crash nested extraction. | The expansion directory name is uniquified. |
| A11 | Low | A filename containing a newline could **forge manifest lines**. | Control characters are escaped when written to the manifest. |
| A12 | Low | Many unreadable files made retry backoff **block cancellation**. | Cancellation is checked during retry waits. |

The manifest is also now written atomically (temp file + rename) so an
interrupted run can't leave it half-written.

## Accepted risks (by design, documented)

- **Patient data in filenames / inventory / manifest** stays on your machine.
  It is never uploaded — the app has no server and no telemetry. Writing your
  own study metadata into your own inventory is the point of the tool.
- **macOS `disable-library-validation` entitlement** is required by the
  PyInstaller runtime to load its bundled libraries; the app is still signed
  with the hardened runtime and notarized by Apple. Revisited if a trimmed
  build launches without it.

## How to verify

- **Code**: it's MIT-licensed — read every line.
- **Tests**: `pytest tests/security` reproduces each finding and its fix.
- **Downloads**: each release publishes SHA-256 checksums (in `version.json`);
  macOS builds are notarized (`spctl --assess` shows *Notarized Developer ID*).
- **Disclosure**: see [`SECURITY.md`](../SECURITY.md) to report an issue.
