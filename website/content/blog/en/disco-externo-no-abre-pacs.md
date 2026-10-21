---
title: Outside CD Won't Import into PACS? A 5-Step Intake Routine
slug: disco-externo-no-abre-pacs
date: 2026-10-29
summary: Outside CD won't import into PACS? A 5-step intake routine for imaging centers and hospitals, with macOS and Windows steps, an identity check before import, and a simple way to measure what outside discs cost you.
og_title: Outside CD won't import into PACS? A 5-step routine
og_description: A 5-step intake routine for outside discs: macOS and Windows steps, an identity check before import, and a simple way to measure the cost.
languages: [es, en]
status: published
tags: [institutions, intake]
image: /img/blog/disco-externo-no-abre-pacs.jpg
---

*Leer en español: [Cuando un disco de estudios no abre en su PACS](/es/blog/disco-externo-no-abre-pacs/).*

It happens at the front desk every day. A patient arrives with a CD from another facility, the radiologist needs it for comparison, and the disc won't open, or opens but won't import into your PACS. Someone tries again, moves to another workstation, calls IT, and the patient leaves with a promise that "we'll load it later".

It is not your team's fault. Published studies report that **22–30% of outside CDs fail to import** (Sodickson et al., *Radiology* 2011; Lichstein et al., *Orthopedics* 2018), and that staff spend a **median of 10 minutes per disc** (Woo et al., *J Trauma Inj* 2022). What your department does control is the routine. Here is one you can adopt tomorrow, in five steps.

## Step 1: Log the disc before you open it

Before the disc goes into a computer, write down the basics on a sheet or in your system:

- The patient's full name and date of birth.
- Where the disc came from and the approximate study date.
- How many discs were handed over (sometimes it is two or three).
- The time it was received.

Label the sleeve with the log number. It looks like paperwork, but it is what stops a disc from getting lost between shifts, and it gives you the data for step 5.

## Step 2: Open it as a folder; don't run the disc's viewer

Many discs carry a viewer that tries to start on its own. You don't need it to import, and running software of unknown origin on a networked workstation is poor practice.

- **On macOS:** insert the disc (with a USB drive if the machine has no reader). It appears on the desktop or in the Finder sidebar. Double-click to open it like any folder.
- **On Windows:** if the AutoPlay window appears, close it or choose **Open folder to view files**. Otherwise open **File Explorer** and go to the disc drive (D:, E:).

Look for a **DICOMDIR** file at the root and a folder holding the studies (for example **DICOM** or **IMAGES**). If there is no DICOMDIR, if the files are inside a ZIP, or if you only see the viewer and no image folder, note it: these are common reasons an import fails.

## Step 3: Confirm identity before import

Before any study enters your PACS, compare what your import tool shows (name, date of birth, study date and type) with the patient's order or record. If a disc contains another person's studies, or several people's, stop and tell the person in charge. Fixing a misfiled study inside the PACS costs far more than checking it at the door.

## Step 4: Import once; if it fails, don't keep retrying the same disc

Run your usual import from the DICOMDIR. If it fails, retrying the same disc rarely changes the result. Instead:

1. **Copy the disc's contents to a local folder** on the intake workstation, so you work from a copy rather than the disc.
2. **Make an organized copy with a standard DICOMDIR**, and try the import from that copy. Sometimes the failure comes from the disc's structure (a missing index or non-standard paths), not the images.
3. **If it still fails, escalate with data:** note the error message and where the disc came from. IT can act much faster on that note than on "it won't open".

Step 2 is what **MIA Toolkit** does: a desktop app for macOS and Windows that reads outside discs, organizes the studies and writes a standard DICOMDIR to USB or a folder, ready for your existing import workflow. It runs offline on one workstation, is open source (MIT) and needs no account; studies never leave the workstation. ([DICOM, DICOMDIR and PACS explained](/blog/dicom-dicomdir-pacs-explained/), for training new staff.)

## Step 5: Close the log entry

When you are done, finish the line you started in step 1:

- **Hands-on staff minutes** actually spent logging, checking and importing the disc, including retries and follow-up; exclude time waiting in a queue or copying unattended.
- **Imported?** Yes or no.
- **Reason**, if it failed: no DICOMDIR, damaged disc, ZIP, identity mismatch, other.

Return the disc to the patient per your policy. Two weeks of these lines tell you how many discs you receive, how much time they cost and how many fail, in your own numbers rather than a journal's. That measurement is step 3 of our [free 60-day pilot](/institutions/?utm_campaign=bnd), and our post on [the hidden cost of outside CDs](/blog/outside-cd-intake-cost/) shows how to turn it into a yearly figure.

## When the problem is the network, not one disc

The routine above fixes intake at one workstation. In organizations with several sites, a central PACS and studies arriving on discs, USB drives or links, the gap sits between that large infrastructure and the media patients actually carry. **MIA Bridge** is how the MIA Tools family closes it: it imports outside studies straight into your PACS and pulls PACS studies onto clean patient media, on-premise and inside your network. MIA Bridge is a pilot program. [Apply to our Pilot Program](https://bridge.miatools.tech/en/?utm_campaign=bnd).

## For your department

The [MIA Tools page for clinics and hospitals](/institutions/?utm_campaign=bnd) has a page for each region with licenses, the procurement kit (security one-pager, IT deployment guide, license terms and a sample certificate) and the free 60-day pilot request. Questions: [support@miatools.tech](mailto:support@miatools.tech).

MIA Toolkit is a file-management tool: it copies, organizes and converts imaging studies. It does not interpret images and does not replace professional radiological review.

## Sources

- Sodickson et al. *Radiology*, 2011.
- Lichstein et al. *Orthopedics*, 2018.
- Woo et al. *J Trauma Inj*, 2022.

## FAQ

**Why won't an outside CD import into PACS?**
Common causes are structural: the disc has no DICOMDIR, the files are zipped, or the disc only carries a viewer. A scratched disc can also fail. Opening the disc as a folder before import tells you in seconds which case you have.

**Do we need the viewer that comes on the disc?**
Not to import. The viewer lets someone see the images on a computer with no other software, but your import workflow needs the DICOM files and, ideally, a DICOMDIR. Avoid running software of unknown origin on networked workstations.

**How much staff time does an outside CD cost?**
One published study reports a median of 10 minutes of staff time per disc (Woo et al., 2022). Your number may differ: two weeks of logging with the five steps above will give it to you.

**Does MIA Toolkit send studies to a server?**
No. It runs offline on one workstation and sends nothing. The only network request it can make is an update check that a user starts by hand, with no identifiers.
