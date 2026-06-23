---
title: DICOM, DICOMDIR, and PACS — Explained for Patients
slug: dicom-dicomdir-pacs-explained
date: 2026-07-09
summary: DICOM, DICOMDIR, and PACS explained in plain language — so you'll see why a well-built USB just works at the radiologist's, and why a messy one sometimes doesn't.
languages: [en, es]
status: published
tags: [explainer, dicom]
---

If you've ever picked up a CD or DVD of your medical images, you may have seen some strange words on the disc: DICOM, DICOMDIR, PACS. They look like secret codes, but they're just the everyday words hospitals use for how medical pictures are saved, organized, and viewed. This post explains each one in plain language, so you'll see why a well-built USB drive "just works" when you hand it to a radiologist, and why a messy one sometimes doesn't.

## DICOM: the file format for medical images

Think about documents on your computer. A letter might be a PDF; a photo might be a JPG. Each is a *file format* — an agreed-upon way of saving information so any program can open it.

DICOM is the file format for medical images. When you have an X-ray, CT scan, MRI, or ultrasound, the machine saves each image as a DICOM file. It's a worldwide standard, which is the whole point: a scan taken on one hospital's machine can be opened on another's computer, even in a different country.

A DICOM file holds more than just the picture. Tucked inside is information about the study — the body part scanned, the date, the type of exam — like a PDF that carries both the page and a label describing it. One scan often produces many DICOM files; a single CT study can hold hundreds or even thousands of image "slices." That's normal, and it explains the next piece of the puzzle.

## DICOMDIR: the table of contents

Imagine a thick book with a thousand pages and no table of contents or page numbers — the words are all there, but finding anything is a nightmare. A folder of loose DICOM files can feel the same way: the images are present, but nothing tells a viewer how they fit together — which slices belong to which scan, which scan to which patient, and in what order to show them.

A DICOMDIR fixes that. The name comes from "DICOM Directory," and *directory* here means an index. It's a single small file at the top level of a disc or USB drive that points to every image, grouped by patient, study, and series.

When a DICOMDIR is built correctly, the whole drive opens as **one organized set** instead of a pile of files.

## PACS: the hospital's filing room and viewer

PACS stands for Picture Archiving and Communication System. The simple version: PACS is the hospital's system for storing medical images and pulling them up on a screen.

Picture a vast filing room combined with a big light box on the wall. The filing room keeps every patient's scans safe and findable; the light box lets a radiologist call up any study in seconds, zoom in, and compare it with an older scan. When your doctor says they'll "load your images into the system," PACS is usually what they mean.

## How they fit together

Here's the chain: each image is a DICOM file, a folder of those files is organized by a DICOMDIR, and the hospital reads the whole thing into PACS. So when you bring in a USB drive, the radiologist's PACS (or a viewer on a laptop) looks for that DICOMDIR table of contents. If it finds a proper one, it instantly understands the whole set — this patient, this study, these images, in this order — and loads it cleanly. If the DICOMDIR is missing or built sloppily, the viewer may stumble: showing only part of a scan, mixing up studies, or refusing to open. The images might be fine, but without a good table of contents, the system can't make sense of them.

## Why MIA Toolkit builds a proper DICOMDIR

This is where MIA Toolkit helps. Many people end up with a stack of discs from different visits and hospitals, each organized differently. MIA Toolkit copies those discs, makes a simple inventory of what's on them, and assembles everything into **one** standards-compliant DICOMDIR archive on a single USB drive. Because that archive follows the DICOM standard carefully, it's designed to open in any radiologist's PACS or any standard viewer — one tidy drive instead of a shoebox of mismatched discs. It can also include your written reports — radiology or lab PDFs — alongside the images, so the scans and their reports travel together. (When you're ready to bring it in, see how to [share your scans on one USB](/blog/share-scans-one-usb/).)

A few things worth knowing: MIA Toolkit works fully **offline**. There's no account, nothing goes to the cloud, and there's no tracking — your images stay on your own computer and USB drive. And it's **free and open-source, and always will be.**

A quick, honest note: MIA Toolkit organizes and delivers *your own* images. It is not a medical device, it does not interpret or read your images, and it is not a substitute for a radiologist or doctor. It only copies, inventories, and packages what you already have, with no warranty.

If this sounds useful, [download it free](/?utm_campaign=bdx) — there's a [step-by-step guide](/help.html). Questions? Email [support@miatools.tech](mailto:support@miatools.tech).

## FAQ

**Do I need to understand DICOM or DICOMDIR to use my images?**
No. These are behind-the-scenes terms. You mainly need a drive that opens cleanly for your care team, and building a proper DICOMDIR is the part MIA Toolkit handles for you.

**My old CD opens on the hospital computer but not on mine. Why?**
Hospitals have DICOM viewers built to read these discs; a home computer usually doesn't. The images may be fine — your computer just doesn't speak DICOM.

**Will a USB drive really work everywhere?**
A drive with a correctly built, standards-compliant DICOMDIR is designed to open in any radiologist's PACS or standard viewer. Equipment varies, so it's wise to confirm with your provider, but following the standard gives you the best chance of a smooth result.
