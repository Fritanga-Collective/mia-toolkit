---
title: How to Put a Drawer of Hospital Imaging CDs Onto One USB for Your Doctor
slug: how-to-use-mia-toolkit-guide
date: 2026-07-23
summary: A start-to-finish walkthrough of turning a drawer of hospital imaging CDs into one organized USB any radiologist can open — copy, review, add reports, deliver.
languages: [en, es]
status: published
tags: [guides]
---

If you've ever helped a family member through a serious illness, you know the drawer. The one that fills up with CDs and DVDs from every scan — an MRI here, a CT there, an X-ray from the hospital across town. Each disc is its own little island: its own clunky viewer, its own folder structure, slowly degrading in a drawer. And every time you see a new doctor, you carry the whole stack and hope the one disc that matters actually opens in the room.

We lived that. So we built the tool we wished we'd had — **MIA Toolkit**, a free, open-source desktop app that takes all of those discs and turns them into one organized archive on a single USB drive that any radiologist can open. No account, no cloud, nothing uploaded. Here's how it works, start to finish.

## The idea in one sentence

Copy every disc onto your computer, let the app make a plain-language inventory of what's there, then build one standards-compliant archive on a USB drive — so your doctor loads everything at once instead of juggling twenty viewers.

## Step 1 — Add your studies

Open the app, choose **Guided Setup**, and start adding. You can insert a CD and the app copies and ejects it for you — even if the disc's own viewer software won't run on your computer. No disc? Import a folder from a USB drive, or a ZIP you downloaded from a hospital patient portal. Repeat for every disc; the app keeps a running count.

## Step 2 — Review what it found

The app scans everything and lists every study — and opens a clean spreadsheet inventory in plain language: patient, study, date, and type of scan. If discs from more than one person got mixed into the pile (it happens), it warns you, so each person's history stays separate.

## Step 3 — Add the reports (optional)

Written reports matter as much as the images. Add report or lab PDFs and they travel with the scans — the app even finds PDFs already sitting on the discs you imported.

## Step 4 — Build and deliver

Now the payoff. The app combines everything into one standards-compliant **DICOMDIR** archive and copies it to your USB drive — verifying every single file by checksum as it goes. That last part matters more than it sounds: a failing or counterfeit USB stick can *look* like it copied fine and quietly corrupt your scans. MIA Toolkit catches that instead of letting you find out in the doctor's office. (If you want to vet the drive first, here's how to [spot a fake or failing USB](/blog/spotting-a-fake-or-failing-usb/).)

## Step 5 — Done

Hand over one USB drive. It opens in any hospital PACS or DICOM viewer, so your doctor can compare years of imaging side by side — which is exactly what good longitudinal care and second opinions need. (For what to say when you hand it over, see [sharing your scans on one USB](/blog/share-scans-one-usb/).)

## Why we give it away

Your medical images are a record of your own body. You should be able to hold them in one place, on any computer, and hand them to any doctor — without a subscription standing in the way. MIA Toolkit is free for patients and families, forever. It works completely offline, and your data never leaves your computer.

It is **not** a diagnostic tool and doesn't replace a radiologist — it organizes and delivers what's already yours.

**→ Read the full step-by-step guide, with screenshots of every screen: [the help walkthrough](/help.html)**

**→ [Download MIA Toolkit (free)](/?utm_campaign=bhg)**

Questions are welcome at [support@miatools.tech](mailto:support@miatools.tech).
