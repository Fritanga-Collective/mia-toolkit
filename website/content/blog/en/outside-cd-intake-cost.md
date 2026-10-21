---
title: Outside Imaging CD Import Workflow: The Hidden Staff Cost, and a 2-Week Way to Measure It
slug: outside-cd-intake-cost
date: 2026-11-05
summary: Your outside imaging CD import workflow costs staff time that never shows up as a line item. Here is where that cost hides, what published studies report, and a 2-week method to measure it with your own numbers.
og_title: The hidden staff cost of outside imaging CDs
og_description: Outside-CD import costs staff time that never shows up as a line item. Where it hides, what studies report, and a 2-week way to measure it.
languages: [en, es]
status: published
tags: [institutions, intake, united-states]
image: /img/blog/outside-cd-intake-cost.jpg
---

*Leer en español: [El costo oculto de los discos externos](/es/blog/outside-cd-intake-cost/).*

Ask a hospital what outside imaging CDs cost and you will usually hear "nothing, patients bring them". There is no invoice and no budget line. But somebody at the film library, the medical-records desk or the imaging front desk spends part of every day loading discs, and when a disc fails, several people spend more.

This post is for the managers who suspect that cost is real and want a number. It covers where the cost hides, what published studies report, and a two-week method to measure your own outside imaging CD import workflow.

## Where the cost hides

Outside-CD work is spread thin across roles, which is why nobody sees the total:

- **Handling time.** Logging the disc, loading it, matching it to the patient, importing it and returning it. One study measured a **median of 10 minutes of staff time per disc** (Woo et al., *J Trauma Inj* 2022).
- **Failures.** Published studies report that **22–30% of outside CDs fail to import** (Sodickson et al., *Radiology* 2011; Lichstein et al., *Orthopedics* 2018). Each failure means retries, a second workstation, a call to IT or a call to the sending facility.
- **Re-requests.** When a disc can't be read, someone asks the other facility to send the study again, and someone follows up.
- **Delay.** While the prior study is missing, the read that needed it waits, or goes ahead without the comparison.
- **Interruptions.** Disc work lands on people who have other jobs. The switching cost is real even when each task is short.

None of this appears on a report. That is what a measurement fixes.

## A 2-week way to measure it

You don't need new software to measure. You need one sheet, one intake point and two ordinary weeks.

### 1. Choose the scope

Pick **one intake point** (the film library, a front desk, a second-opinion program) and **two typical weeks**. Avoid holiday weeks and go-live weeks for other systems.

### 2. Use a one-page log

One row per disc, with these columns:

| Column | What to write |
|---|---|
| Log # | A number that links to your own system. Keep patient names off the sheet. |
| Date and time received | When the disc reached the desk. |
| Hands-on minutes | Time someone actually worked on it, from logging to import or to giving up. |
| Imported? | Yes or no. |
| Failure reason | No DICOMDIR, damaged disc, ZIP or unusual format, identity mismatch, other. |
| Rework minutes | Extra time on failures: calls, re-requests, second attempts. |
| Role | Who handled it (front desk, film library, technologist, IT). |

Two rules make the data honest: **log every disc**, including the ones that loaded on the first try, and **count hands-on minutes**, not the time the disc sat in a tray.

### 3. Do the arithmetic

At the end of two weeks, work out four numbers from your sheet:

- **D:** discs per week (total discs ÷ 2).
- **M:** median hands-on minutes per disc.
- **F:** failure rate (failed discs ÷ total discs).
- **R:** average rework minutes per failed disc.

Then:

- **Staff hours per year** ≈ total hands-on staff minutes over the two weeks × 26 ÷ 60. Include initial handling and rework, counting each minute only once.
- **Staff cost per year** ≈ staff hours per year × your loaded hourly cost for the roles involved

Use your own hourly cost; finance can give you a loaded figure. Compare your M and F with the published benchmarks above: if you are close to a median of 10 minutes and a failure rate in the 22–30% range, you are in the range the literature describes. If you are far off, that is worth knowing too.

### 4. Look at the reasons column

The failure reasons usually point to the fix. Discs without a DICOMDIR or with non-standard structure need a step that organizes the files before import. Identity mismatches need a check at the door. Damaged discs need a policy for re-requests. Our [5-step intake routine](/blog/disco-externo-no-abre-pacs/) covers each of these.

## What to do with the number

A measured cost lets you decide calmly: keep the current process, tighten the routine, or add a tool. If you add one, measure again for two weeks with the same sheet and compare.

That is exactly how our **free 60-day pilot** works. You install **MIA Toolkit** on one intake workstation (about 15 minutes, no server and no account), log each disc for two weeks on a one-page sheet, then compare with your own numbers and decide, with no commitment. MIA Toolkit is a desktop app for macOS and Windows that reads outside discs, organizes the studies and writes a standard DICOMDIR to USB or a folder, ready for your existing import workflow. It runs offline, is open source (MIT), and studies never leave the workstation. The [US page](/institutions/us/?utm_campaign=buc#roi) has an estimate calculator with its assumptions spelled out.

## When the gap is bigger than one workstation

Multi-site systems face the same problem at scale: a large PACS and network on one side, and on the other the discs, USB drives and links patients actually carry. **MIA Bridge** is how the MIA Tools family closes that gap: it imports outside studies straight into your PACS and pulls PACS studies onto clean patient media, on-premise and inside your network. MIA Bridge is a pilot program. [Apply to our Pilot Program](https://bridge.miatools.tech/en/?utm_campaign=buc).

## Next step

On the [MIA Tools page for US hospitals and imaging centers](/institutions/us/?utm_campaign=buc) you will find licenses, the [procurement kit](/institutions/us/?utm_campaign=buc#kit) (security one-pager, IT deployment guide, license terms and a sample certificate) and the [pilot request](/institutions/us/?utm_campaign=buc#pilot). Questions: [support@miatools.tech](mailto:support@miatools.tech).

MIA Toolkit is a file-management tool: it copies, organizes and converts imaging studies. It does not interpret images and does not replace professional radiological review.

## Sources

- Sodickson et al. *Radiology*, 2011.
- Lichstein et al. *Orthopedics*, 2018.
- Woo et al. *J Trauma Inj*, 2022.

## FAQ

**How much staff time does an outside imaging CD take?**
One published study measured a median of 10 minutes of staff time per disc (Woo et al., 2022). Your number depends on your workflow; a two-week log gives you your own.

**How often do outside CDs fail to import?**
Published studies report that 22–30% of outside CDs fail to import (Sodickson et al., 2011; Lichstein et al., 2018). Logging failure reasons for two weeks shows how often it happens at your site, and why.

**Do we need patient names on the measurement sheet?**
No. Use a log number that links to your own system and keep patient identifiers off the sheet. The measurement only needs times, outcomes and reasons.

**Does the pilot send any data to MIA?**
No. MIA Toolkit runs offline on one workstation and sends nothing. The measurement sheet stays with you; you share only the numbers you choose to.
