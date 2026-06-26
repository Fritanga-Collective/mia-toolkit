---
title: How to Share Your Scans on One USB With Your Doctor or Radiologist
slug: share-scans-one-usb
date: 2026-07-02
summary: A plain-language walkthrough of putting all your imaging on a single USB a doctor can open — what belongs on it, how a radiologist reads it, and what to say.
languages: [en, es, zh, ms, ta, de, fr]
status: published
tags: [guides, usb, sharing]
---

If you have an appointment or a second opinion coming up, you may be wondering how to bring all your imaging with you. Maybe you have a stack of CDs from different hospitals. Maybe some are scratched, mislabeled, or you are not even sure what is on them. The good news: you can put everything on a single USB drive that a doctor or radiologist can open and review.

This guide walks you through exactly what to do, what belongs on that USB, and what to say when you hand it over. It is written for real people, not computer experts. Take it one step at a time.

## Why One USB Is Better Than a Pile of CDs

Most newer computers no longer have CD drives. Even when they do, loading several discs one at a time is slow, and discs scratch or stop working. A single USB drive solves all of that. Everything lives in one place, it is easy to carry, and a doctor can plug it in and get started in seconds.

But there is a catch. You cannot just drag files onto a USB and expect a hospital system to understand them. Medical images use a special format called DICOM, and hospital viewing systems (often called PACS) expect those images to be organized in a specific, standard way. If the organization is wrong, the system may not see your studies at all. (If those terms are new to you, our explainer on [DICOM, DICOMDIR, and PACS](/blog/dicom-dicomdir-pacs-explained/) breaks them down in plain language.)

That is the problem MIA Toolkit was built to solve.

## What Belongs on the USB

A well-prepared USB has a few clear pieces. Here is what each one is and why it matters.

**1. A standards-compliant DICOMDIR archive.** Think of DICOMDIR as a table of contents that lists every image and study on the drive, in the exact format medical systems expect. When a radiologist plugs in your USB, their software looks for this file first. If it is built correctly, the system can find and load all your studies. This is the single most important item, and getting it right by hand is genuinely hard. MIA Toolkit builds it for you.

**2. A plain-language inventory of every study.** This is a simple spreadsheet or list, in everyday words, of what is on the drive: the type of scan (for example, a CT of the chest or an MRI of the knee), the date, and the body part. You and your doctor can read it at a glance, without any special software. It helps everyone confirm that nothing is missing.

**3. An optional one-page cover note.** A short note can save time. You might write your name and date of birth, the reason for the visit, and a line like "All imaging from 2022 to 2026, three hospitals." Keep it simple. This is for human eyes, not the computer.

**4. An optional free portable DICOM viewer.** Most radiologists will import your DICOMDIR directly into their own system. But sometimes you are handing the drive to a doctor who does not have a full PACS, or you want to be able to show the images yourself. In that case you can copy a free, portable viewer onto the USB so the recipient can open the images on almost any computer, with nothing to install.

Two free portable viewers that people often use are **Weasis** (available for Windows, macOS, and Linux) and **MicroDicom** (Windows). Both are free and run without installation. Always check the current download link and licensing terms yourself before you rely on them, and remember that adding a viewer is optional. We do not endorse any particular product. (We compare them in our guide to [free, portable DICOM viewers](/blog/free-portable-dicom-viewers/).)

## How MIA Toolkit Builds the USB for You

You do not have to assemble all of this by hand. MIA Toolkit is a free desktop app for macOS and Windows that does the heavy lifting:

- It copies your hospital imaging CDs, one after another, onto your computer.
- It builds a plain inventory of every study it finds, so you can see exactly what you have.
- It assembles a single, standards-compliant DICOMDIR archive on your USB drive.
- If you have written **radiology reports or lab PDFs**, it can include those too — saved as files your doctor can open and embedded into the archive — so your scans and their reports travel together.
- It makes a **verified copy**, checking that what landed on the USB matches the original, so you are not left wondering whether the transfer worked. This also catches a counterfeit or failing USB stick that would otherwise corrupt your files silently (more on that in our guide to [spotting a fake or failing USB](/blog/spotting-a-fake-or-failing-usb/)).

The result is one tidy USB drive with all your studies, organized the way medical systems expect, plus the inventory you can read yourself and a short log of exactly what was copied. If you choose, you can also drop a portable viewer onto the drive in the same step.

## How a Radiologist Usually Opens Your USB

Here is what typically happens on the other end, so you know what to expect.

Most hospital PACS systems can import a DICOMDIR straight from a USB drive. The staff member plugs in the drive, tells their system to import, and the studies load into your record. Because the DICOMDIR follows the standard, the system knows how to read it.

If a recipient does not have a PACS, or just wants a quick look, they can open the images in a DICOM viewer instead, like the portable one you optionally copied onto the drive. Either way, the standard format is what makes your images openable.

## Practical Tips Before Your Appointment

A few small habits make the whole thing go smoothly:

- **Label the drive.** A piece of tape with your name and date of birth is enough. It avoids mix-ups at a busy front desk.
- **Keep a backup copy.** Make a second USB, or keep the copied files on your computer. Drives can be lost or fail. MIA Toolkit's verified copy gives you peace of mind, but a backup is still wise.
- **Hand it over in person.** Your images are private. Giving the USB directly to the staff or your doctor keeps you in control of where it goes. There is no need to upload anything anywhere.
- **Know what to say at the front desk.** Try something simple: "I have all my prior imaging on this USB drive. It is a DICOMDIR you can import into your system, and there is a printed list of the studies." If they have questions, that one sentence usually points them in the right direction.

## A Note on Privacy

MIA Toolkit works entirely offline. There is no account to create, nothing is uploaded to the cloud, and there is no tracking. Your images stay on your computer and your USB drive, under your control. When you are ready to share, you simply hand the drive to your doctor in person. That is the most private way to do it.

## Free, and Always Will Be

MIA Toolkit is free and open-source, and it will always be free to use. There is no upgrade to buy and no hidden cost.

## A Quick, Important Note

MIA Toolkit helps you organize and deliver your own medical images. It is not a medical device, and it does not interpret or diagnose anything in your images. It is not a substitute for a qualified radiologist or doctor, who is the right person to read your scans and answer medical questions. The software is provided without any warranty. For anything about your health, always rely on your care team.

## Get Started

When you are ready, you can [download MIA Toolkit for free](/?utm_campaign=bsh) and prepare your USB before your next visit. For a full step-by-step walkthrough with a screenshot of each screen, see the [step-by-step guide](/help.html). If you have a question about using the app, you can reach us at [support@miatools.tech](mailto:support@miatools.tech).

## FAQ

**Will the hospital be able to open it?**
In most cases, yes. MIA Toolkit builds a standards-compliant DICOMDIR archive, which is the format hospital PACS systems are designed to import. Most systems load it directly from the USB. If a particular recipient does not use a PACS, they can open the images in a free DICOM viewer instead. Because the format follows the standard, it works across many systems.

**Do I need to be good with computers?**
No. The app guides you through copying your CDs and building the USB, and it creates a plain-language list of your studies so you can see what you have. If you can plug in a CD and a USB drive, you can do this.

**What if some of my discs are old or hard to read?**
MIA Toolkit copies each disc and then makes a verified copy, checking that the files transferred correctly. If a disc is damaged and some images cannot be read, the inventory will help you see what made it onto the drive and what may be missing, so you can follow up with the hospital that has the originals.

**Is my information sent anywhere?**
No. The app runs offline with no account, no cloud, and no tracking. Your images stay on your computer and your USB drive. You share them by handing the drive to your doctor in person.
