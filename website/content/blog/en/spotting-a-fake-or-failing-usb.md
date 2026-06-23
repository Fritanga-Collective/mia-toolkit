---
title: Is Your USB Drive Fake or Failing? How to Test It Before You Trust It With Your Scans
slug: spotting-a-fake-or-failing-usb
date: 2026-07-21
summary: Cheap and counterfeit USB sticks fail silently — here's how to test a drive for speed and real capacity in minutes, before you trust it with your medical scans.
languages: [en, es]
status: published
tags: [guides, usb]
---

You plug in a USB stick to copy your medical scans onto it, start the copy, and… it crawls. Minutes pass. Then more minutes. A transfer that should take a couple of minutes is still going an hour later, and you have no idea whether it is working or stuck. Or worse: it finishes, you hand the drive to your doctor, and half the files won't open.

If this has happened to you, the problem is almost never your computer or the software. It is the drive. Cheap, counterfeit, and worn-out USB sticks are far more common than people realize, especially the free promotional ones handed out at conferences, the bargain "256 GB for $8" listings, and the no-name sticks that come bundled with gadgets. This guide shows you how to tell a good drive from a bad one in about two minutes, so you never trust something as important as your medical images to a drive that is quietly broken.

## The three ways a USB drive goes bad

**It's slow — pathologically slow.** A healthy USB 2.0 stick writes data at roughly 10 to 30 megabytes per second; a USB 3 drive, much faster. A bad one can drop to a fraction of a megabyte per second — slow enough that a one-gigabyte copy takes hours instead of a minute. We have seen a giveaway stick write at around 0.2 MB/s, which is roughly a hundred times slower than the cheap-but-honest drive sitting next to it. At that speed it isn't broken in an obvious way; it just never finishes, and you assume the software is to blame.

**It lies about its size (the "counterfeit" or "fake-capacity" drive).** This is the nasty one. A scammer takes a tiny chip — say 8 GB of real storage — and reprograms it to *report* itself as 256 GB or 1 TB to your computer. Everything looks fine when you buy it. The trouble starts when you write more data than the chip can actually hold: the drive accepts the files, says it saved them, but the bytes beyond the real capacity vanish or overwrite earlier files. You don't find out until you try to open them later — which, for medical scans, might be in a doctor's office, months after the original CD is gone. These drives are sold by the millions on big marketplaces.

**It's simply worn out or dying.** Flash memory wears with use, and the cheapest chips wear fastest. A dying drive shows write errors, corrupts files at random, refuses to eject, or hangs the whole copy so hard you can't even cancel it. If a drive ever refuses to let go of a copy you've cancelled, treat that as a serious warning sign.

## Test 1 — Is it fast enough? (two minutes)

The quickest check is a raw speed test: write one large file and see how long it takes. This sidesteps the small-file overhead that makes any USB copy a bit slower, and tells you the drive's real bandwidth.

**On a Mac**, open Terminal and run these one at a time (replace `MYUSB` with your drive's name, which you can see in Finder or by running `ls /Volumes`):

```
dd if=/dev/zero of=/Volumes/MYUSB/speedtest.bin bs=1m count=200
rm /Volumes/MYUSB/speedtest.bin
```

The first command writes a 200 MB test file and prints a line like `209715200 bytes transferred in 11.6 secs (18068546 bytes/sec)`. Divide that last number by a million to get megabytes per second — here, about 18 MB/s, which is a healthy result. If you see something under a few MB/s, or the command seems to hang and won't respond to Ctrl-C, the drive (or the port it's plugged into) is the problem.

**On Windows**, the simplest version is to copy a single large file (a 200 MB–1 GB video works) onto the drive and watch the speed the copy dialog reports. A healthy stick holds steady in the tens of MB/s; a bad one sputters along in the hundreds of kilobytes.

If the big-file test is slow, before condemning the drive: try a different USB port (plug straight into the computer, not through a hub or dock), try a different cable, and make sure you're not in an old USB 1.1 port. A good drive in a bad port can look broken.

## Test 2 — Is the capacity real? (the counterfeit test)

A speed test won't catch a fake-capacity drive — those can be fast right up until you exceed the real chip. To catch those you have to *fill the drive with known data and read it back*, checking that every byte survived. Free, trustworthy tools do exactly this:

- **F3** ("Fight Flash Fraud") on Mac and Linux: `f3write` fills the drive with verifiable files, then `f3read` reads them back and reports any that came back wrong. Installable via Homebrew (`brew install f3`).
- **H2testw** on Windows: the long-standing standard; writes test data across the whole drive and verifies it.
- **ChkFlsh** / **ValiDrive** are other Windows options.

Run one of these on any new drive *before* you put anything important on it. If the verify step reports errors, the drive is fake or failing — return it, and never use it for data you can't afford to lose. It takes a while (it has to fill the entire drive), but you only do it once per drive, and it's the only way to know a "1 TB" stick is actually a 1 TB stick.

## How to not get burned

- **Buy from reputable brands and sellers.** SanDisk, Samsung, Kingston, and the like, sold directly or by the marketplace itself rather than a random third-party reseller. If a deal looks too good — a terabyte for the price of a coffee — it is a fake.
- **Test new drives before trusting them**, using the two tests above. Two minutes for speed; one slow afternoon (unattended) for the full capacity check.
- **Be wary of free promotional sticks** for anything that matters. They are the cheapest flash on earth, and they are exactly the ones we've watched fail.
- **Never make a USB the only copy of your scans.** Keep the original discs or the downloaded files until you've confirmed the drive reads back correctly on another computer.

## Where MIA Toolkit fits

We built MIA Toolkit to consolidate your imaging CDs and downloads into a single, organized USB archive — and because we knew drives fail, the app **checks every file it writes**. After copying, it confirms each file actually arrived and is the right size; if one didn't make it, the app tells you and copies it again, and it can resume an interrupted transfer instead of starting over. So a slow or failing drive shows up as visible errors and retries — an honest *something went wrong* — rather than a copy that quietly stops halfway and looks done.

One honest limit, and it's exactly why the tests above matter: a fake-capacity drive is the hard case, because it can report a file as the right size while the actual bytes were thrown away beyond the real chip. No copy tool can see through that by checking sizes — the only way to catch a counterfeit is to fill it and read it back (Test 2) *before* you trust it. So the safest routine is simple: test a new drive first, then let the app handle the copy and flag anything that fails along the way.

The tool is free, runs entirely on your own computer, and never sends your images anywhere. It is not a medical device, and it does not read or interpret your scans — it only organizes and delivers images that are already yours. If you're organizing a drawer of scans onto a USB to carry to an appointment, check the drive first with the steps above — then [download MIA Toolkit for free](/?utm_campaign=bfu) and let the app do the careful copying. Questions are welcome at [support@miatools.tech](mailto:support@miatools.tech).
