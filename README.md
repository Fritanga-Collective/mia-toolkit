# Medical Imaging Archive Toolkit

A small set of Python scripts for compiling years of medical imaging CDs into a single, radiologist-friendly archive on macOS.

## What this is for

If you (or a family member) have accumulated a stack of imaging CDs — MRIs, CTs, X-rays from different hospitals over many years — you have a problem: each CD is on its own, the discs are slowly degrading, and any radiologist trying to compare studies across time has to juggle 20+ separate viewers. This toolkit consolidates everything into one standards-compliant DICOM archive that loads into any PACS as a single "CD."

The workflow is three steps: **rip** each CD to disk, **inventory** what you have, **build** a unified DICOMDIR archive. The result is a single folder you copy to a USB drive and hand to the radiologist.

This is for personal use, longitudinal review, and second-opinion consultations. It is not a diagnostic tool, does not interpret images, and does not replace professional radiological review.

## Requirements

- macOS (the auto-detection and eject features are Mac-specific; Linux works for most things)
- Python 3.7+
- An external USB optical drive if your Mac doesn't have one (~$25)
- A USB stick or small external SSD for the final deliverable

## Setup (one time, ~5 minutes)

Pick any folder, drop the three scripts into it, install dependencies:

```bash
mkdir -p ~/Documents/MedicalArchive
cd ~/Documents/MedicalArchive
# Move rip_cd.py, dicom_inventory.py, build_dicomdir.py here

pip3 install pydicom openpyxl --break-system-packages
```

That's the entire setup. The three scripts define the project; everything else is generated as you run them.

## The workflow

Open Terminal once, navigate to the folder, and leave it open:

```bash
cd ~/Documents/MedicalArchive
```

### Phase 1 — Rip each CD to disk

```bash
# Insert a CD, wait ~10 seconds for macOS to mount it
python3 rip_cd.py
# Disc auto-ejects when done. Insert next disc. Run again. Repeat.
```

Each disc gets copied into `raw_discs/disc_NN_YYYY-MM-DD_<label>/`. The number auto-increments (01, 02, 03...) so they sort chronologically by import order. Most discs rip in 2–10 minutes; older or scratched ones can take 20–30.

If a disc fails partway through, run with `-n <same number>` to resume into the same folder — already-copied files are skipped.

Aging CDs (10+ years old) sometimes have unreadable sectors. The script automatically retries each file 3 times with backoff, then falls back to `dd conv=noerror` for stubborn sectors. The `_manifest.txt` in each disc folder records what worked and what didn't.

### Phase 2 — Build the inventory

```bash
python3 dicom_inventory.py
```

This walks `raw_discs/` and produces `inventory.xlsx` with three sheets:

- **Studies** — one row per study, sorted by date, with checkmarks for each sequence present (T1, T2, FLAIR, DWI, T1+Gd, MRA/CTA)
- **Series Detail** — every series broken out by sequence type, contrast, slice thickness
- **Consistency Check** — every unique patient name/ID/birthdate found, so you can spot if a stranger's disc got mixed in (or, more commonly, the same patient registered differently across hospitals)

Open it in Excel or Numbers. This is your at-a-glance view: scroll the columns and you immediately see which years are missing post-contrast, whether you have any vascular imaging, and so on.

### Phase 3 — Compile the archive

```bash
python3 build_dicomdir.py
```

This produces `Archive/`, a single DICOM file-set with a `DICOMDIR` index at the root. The output structure follows the international standard for portable medical media — any PACS, Horos, OsiriX, RadiAnt, Weasis, or 3D Slicer will recognize it.

The script auto-deduplicates by SOPInstanceUID (in case files appeared on multiple CDs) and auto-repairs minor non-conformities that real hospital DICOMs often have (missing StudyID, etc.) — placeholder values are filled in only where required by the file-set spec, never replacing actual clinical data.

## Folder structure after running everything

```
MedicalArchive/
├── rip_cd.py
├── dicom_inventory.py
├── build_dicomdir.py
├── README.md
├── raw_discs/                    <- your working copy of each CD
│   ├── disc_01_YYYY-MM-DD_.../
│   │   ├── _manifest.txt
│   │   └── DICOM/...
│   ├── disc_02_.../
│   └── ...
├── inventory.xlsx                <- master spreadsheet
└── Archive/                      <- the deliverable
    ├── DICOMDIR                  <- this is what the radiologist points at
    ├── PT000000/
    │   ├── ST000000/
    │   │   └── SE000000/
    │   │       └── IM000000
    │   └── ...
    └── README.txt
```

## What each script does in detail

### `rip_cd.py`

Auto-detects mounted CDs by looking for `DICOMDIR`, `DICOM/`, or `IMAGES/` at the volume root. Walks the entire tree (DICOM files often have no `.dcm` extension on hospital CDs — they're detected by magic bytes). Copies everything into a new disc folder. Writes a `_manifest.txt` recording total files, successes, retries, failures, total bytes, and elapsed time. Ejects the disc on macOS when done.

Useful options:

- `python3 rip_cd.py /Volumes/MEDICAL_CD` — explicit source instead of auto-detect
- `python3 rip_cd.py -n 5` — force into `disc_05_...` (for resuming a partial rip)
- `python3 rip_cd.py --no-eject` — keep the disc inserted
- `python3 rip_cd.py -v` — verbose, prints every file

### `dicom_inventory.py`

Walks any directory tree, finds DICOM files by magic bytes, groups them by StudyInstanceUID and SeriesInstanceUID (not by folder structure, which is inconsistent across hospitals). Heuristically classifies each series as T1, T2, FLAIR, DWI, ADC, T1+Gd, MRA, CTA, etc. — patterns include both English and Spanish keywords so "RM ENCEFALO CON GADOLINIO" and "Ax T1 POST GAD" both get tagged correctly.

Useful options:

- `python3 dicom_inventory.py /some/other/path` — scan a different folder
- `python3 dicom_inventory.py -o my_inventory.xlsx` — custom output name
- `python3 dicom_inventory.py -v` — show progress every 500 files

### `build_dicomdir.py`

Walks the source tree, indexes every DICOM file into an in-memory file-set (deduplicated by SOPInstanceUID), then writes the whole thing out in canonical DICOM PS3.10 Media Storage format: a `DICOMDIR` index plus a normalized `PT/ST/SE/IM` folder hierarchy. Also writes a human-readable `README.txt` inside the archive listing every study chronologically.

Useful options:

- `python3 build_dicomdir.py -o /Volumes/USB/Archive` — write directly to a USB drive
- `python3 build_dicomdir.py /custom/source -o /custom/dest`
- `python3 build_dicomdir.py -v` — verbose

## Common scenarios

**A disc was so damaged the script couldn't read several files.** Try cleaning gently with a microfiber cloth (center-to-edge motion, never circular). If that doesn't help, try a different optical drive — they vary widely in tolerance for marginal media. As a last resort, install `ddrescue` (`brew install ddrescue`) and image the whole disc to a `.iso`:

```bash
diskutil list                              # find your CD device
ddrescue -r3 /dev/disk2 disc.iso disc.log  # may take hours
hdiutil mount disc.iso                     # mount the image
python3 rip_cd.py /Volumes/<mount_point>   # rip the image
```

**A new CD shows up later.** Drop it into the workflow:

```bash
python3 rip_cd.py                       # it gets the next disc number
python3 dicom_inventory.py              # regenerates inventory.xlsx
rm -rf Archive                          # remove old archive
python3 build_dicomdir.py               # rebuild with the new disc included
```

**The Consistency Check shows two different PatientIDs.** Almost always this means the same patient was registered differently at different hospitals (different ID systems, different name spellings, transposed dates of birth). Note which IDs map to the same person — the radiologist's PACS can merge them on import. If you see an ID that genuinely doesn't belong to your relative, find which disc folder it came from (use the Series Detail sheet) and decide whether to remove that folder from `raw_discs/`.

**A disc has very long paths or special characters that cause errors.** This is rare but happens with some European hospital systems. Run with `-v` to see exactly which file causes the issue, then check `_manifest.txt` to see if the script gave up or recovered.

**Wanting to test the Archive before delivering it.** Install Horos (free, [horosproject.org](https://horosproject.org)), open it, then File → Import → Import Files → point at `Archive/DICOMDIR`. All your studies should appear in the database. If they don't, run `build_dicomdir.py -v` to see what was skipped.

## Delivering to the radiologist

Buy a USB drive — 32 GB is plenty unless you have many CT angiograms. A small portable SSD reads much faster (500+ MB/s vs ~10 MB/s for a typical USB stick) and is worth the small extra cost if the radiologist will be loading 5,000+ images.

```bash
USB=/Volumes/<your_usb_name>
DEST="$USB/CaseReview_$(date +%Y%m%d)"
mkdir -p "$DEST"
cp -R Archive "$DEST/"
cp inventory.xlsx "$DEST/"
# Add a cover_note.pdf with your specific questions
```

The cover note is what turns this from "here's a USB drive of stuff" into "here's a specific case with specific questions." One page is enough:

- Patient identifiers (name, DOB)
- Brief clinical history (3–4 lines)
- The specific questions you want answered
- Your contact info

## Troubleshooting

**"No mounted CDs detected."** macOS sometimes takes 10–15 seconds to mount a CD. Wait, check Finder shows the disc, then re-run. If still nothing, the disc may be unreadable in this drive — try a different drive.

**"pydicom not installed."** Run the install command in the Setup section. If pip itself isn't found, install Python from python.org and retry.

**Permissions errors writing files.** Usually means the destination is on a read-only filesystem (some external drives default to that). Reformat the drive as exFAT or APFS using Disk Utility.

**Script hangs on a specific file.** A bad sector being retried by macOS. Wait — the script has internal timeouts and will eventually give up and move on. If it hangs for more than a few minutes, Ctrl+C and re-run; resume support will pick up where it left off.

**Inventory shows "Other" for sequences I know are real.** The series description from that hospital doesn't match my keyword patterns. Open the Series Detail sheet, find the description string, and let me know — easy to add.

**Archive folder is huge.** Each MRI study is typically 50–500 MB; CTs can be 1–2 GB each. Twenty-three studies might total 5–15 GB. This is normal.

## What this toolkit does not do

It does not interpret images, segment lesions, perform volumetric measurements, register studies for comparison, or generate radiology reports. Those tools exist (3D Slicer, FreeSurfer, ITK-SNAP, FSL, OsiriX MD, commercial AI tools like icobrain or QyScore) but require domain expertise to use responsibly. This toolkit is purely about organization and delivery — getting your data into a state where a qualified professional can review it efficiently.

It also does not anonymize. If you're sharing data with a research group or posting publicly, you'll need an anonymization tool — `pydicom` has utilities for this, and tools like DicomCleaner provide a UI.

## Development

The three commands are now thin shims over the `mia.core` package, which holds
the same logic in a UI-agnostic form (each worker reports progress through a
callback and can be cancelled) so it can drive both the CLI and the upcoming
GUI. The standalone usage above is unchanged.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # installs pydicom, openpyxl, pytest
pytest                    # run the test suite
```

Console entry points are also installed: `mia-rip`, `mia-inventory`, `mia-build`.

### Desktop app

A Tkinter GUI wraps the same three actions for non-technical users (macOS for
now). Launch it with:

```bash
python -m mia.gui        # or the installed `mia` command
```

The home screen offers **Guided Setup** — a step-by-step wizard (Welcome → Rip →
Review inventory → Build & deliver → Done) that auto-manages a single project
folder under `~/Documents/MedicalArchive` and only asks for the USB drive at the
end — plus the three individual tools (Rip a CD, Build Inventory, Build Archive)
for people who already know the flow.

Every screen has a live plain-language log, an expandable technical-details
pane, and a saved session log. Ripping runs as an auto-looping session: insert a
disc, it copies and ejects, then waits for the next. The finished archive is
copied to the USB with a **verified, resumable copy** (per-file retry + size/
optional-SHA-256 verification) — robust on slow, flaky USB media without
depending on rsync. All UI strings are `gettext`-wrapped (English ships today;
see `mia/i18n/locale/README.md` to add Spanish).

## License and reuse

Use freely for personal medical record management. No warranty, no liability — if a critical study fails to import on the receiving end, that's between you and the radiologist's IT team.