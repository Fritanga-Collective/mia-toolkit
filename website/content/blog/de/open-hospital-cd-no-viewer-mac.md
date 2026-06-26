---
title: So öffnen Sie eine Krankenhaus-CD, wenn es keinen Viewer gibt (oder sie sich auf einem Mac nicht öffnen lässt)
slug: open-hospital-cd-no-viewer-mac
date: 2026-07-07
summary: Ihre Krankenhaus-CD lässt sich nicht öffnen? Die Bilder sind mit ziemlicher Sicherheit in Ordnung — hier erfahren Sie, wie Sie am defekten Viewer vorbeischauen und Ihre Aufnahmen auf einem Mac oder Windows-PC öffnen.
languages: [en, es, zh, ms, ta, de, fr]
status: published
tags: [guides, dicom, mac]
translation: machine
---

Sie sind aus dem Krankenhaus mit einer CD Ihrer Aufnahme nach Hause gekommen. Sie schieben sie in Ihren Computer, und... nichts. Vielleicht öffnet sich ein Fenster und friert ein. Vielleicht werden Sie aufgefordert, etwas zu installieren, das nie funktioniert. Vielleicht sind Sie an einem Mac, und die Disc scheint absolut gar nichts zu tun.

Atmen Sie durch. Das ist eine der häufigsten Frustrationen, auf die Menschen stoßen, und die gute Nachricht ist, dass Ihre eigentlichen Bilder mit ziemlicher Sicherheit in Ordnung sind. Das Problem ist meist das kleine Viewer-Programm, das auf der Disc mitgeliefert wird, nicht die Bilder selbst. Gehen wir gemeinsam durch, wie Sie an Ihre Bilder kommen, in Ruhe und Schritt für Schritt.

## Auf der Disc sind zwei verschiedene Dinge

Hier ist der Teil, den im Krankenhaus niemand erklärt. Eine Bildgebungs-CD enthält fast immer zwei getrennte Dinge:

1. **Ein Viewer-Programm**, das die Disc automatisch zu starten versucht. Das ist die kleine App, die sich öffnet (oder es versucht), wenn Sie die Disc einlegen.
2. **Ihre eigentlichen medizinischen Bilder**, gespeichert als Standarddateien in einem Format namens DICOM.

Der Viewer und die Bilder sind getrennt. Wenn Ihre Disc sich "nicht öffnen lässt", ist es fast immer der *Viewer*, der das Problem ist, nicht Ihre Bilder. Vielleicht wurde der Viewer nur für Windows gebaut und Sie sind an einem Mac. Vielleicht ist er alt oder beschädigt, oder die Sicherheitseinstellungen Ihres Computers blockieren ihn.

Die Erleichterung hier ist einfach: Sie brauchen diesen Viewer überhaupt nicht. Ihre Bilder sind Standarddateien, und viele kostenlose, moderne Programme können sie direkt öffnen.

## Schritt 1: Schauen Sie sich an, was tatsächlich auf der Disc ist

Anstatt die Disc ihr eigenes Programm starten zu lassen, öffnen wir sie wie einen ganz normalen Ordner und schauen hinein.

- **Auf einem Mac:** Legen Sie die Disc ein. Ein Symbol dafür sollte auf Ihrem Schreibtisch oder in einem Finder-Fenster auf der linken Seite erscheinen. Doppelklicken Sie auf dieses Symbol, um die Dateien zu sehen, statt ein aufpoppendes Fenster auszuführen.
- **Auf Windows:** Legen Sie die Disc ein. Wenn ein Fenster fragt, was Sie tun möchten, wählen Sie "Ordner öffnen, um Dateien anzuzeigen". Wenn nichts erscheint, öffnen Sie den **Datei-Explorer** und klicken Sie dann auf der linken Seite auf das Disc-Laufwerk (oft mit D: oder E: beschriftet).

Schauen Sie sich nun die Dateinamen an. Sie suchen nach zwei Dingen:

- Eine Datei namens **DICOMDIR** (ohne Dateiendung). Das ist so etwas wie ein Inhaltsverzeichnis für all Ihre Bilder.
- Ein Ordner, oft **DICOM** oder **IMAGES** genannt, voller Dateien mit Namen wie `IM_0001` oder Zahlen ohne vertraute Endung.

Wenn Sie diese sehen, herzlichen Glückwunsch. Ihre Bilder sind da und unversehrt. Der defekte Viewer der Disc war nie das eigentliche Hindernis.

## Schritt 2: Öffnen Sie Ihre Bilder mit einem kostenlosen Viewer

Sie öffnen diese Dateien nicht per Doppelklick. Stattdessen installieren Sie einen kostenlosen Viewer und richten ihn dann auf die **DICOMDIR**-Datei oder den Bildordner. Hier sind kostenlose Optionen, nach Computer gruppiert. Bitte prüfen Sie die Website jedes Programms auf aktuelle Download-Links und Lizenzbedingungen, bevor Sie es installieren. (Für einen ausführlicheren Vergleich siehe unseren Leitfaden zu [kostenlosen, portablen DICOM-Viewern](/de/blog/free-portable-dicom-viewers/).)

**Wenn Sie einen Mac haben:**

- **Weasis** läuft auf Mac, Windows und Linux. Es ist kostenlos und quelloffen, öffnet DICOMDIR und hat sogar eine portable Version, die von einem USB-Stick laufen kann. Eine gute Allround-Wahl.
- **Horos** ist nur für Mac, kostenlos und quelloffen. Es wird auf Ihrem Computer installiert (keine portable Version) und öffnet DICOMDIR.
- **OsiriX Lite** ist nur für Mac und kostenlos mit gewissen Einschränkungen. Es wird auf Ihrem Computer installiert.

**Wenn Sie einen Windows-PC haben:**

- **MicroDicom** ist nur für Windows und kostenlos für den privaten Gebrauch. Es ist ungefähr die einfachste Option, hat eine portable Version und öffnet DICOMDIR.
- **Weasis** (oben erwähnt) läuft ebenfalls auf Windows und kann von einem USB-Stick laufen.
- **RadiAnt** ist ein Windows-Programm, das DICOMDIR öffnet. Es ist kostenpflichtig, mit einer verfügbaren kostenlosen Testversion.

Sobald ein Viewer installiert ist, öffnen Sie ihn, suchen Sie nach einer Menüoption wie "Öffnen" oder "Importieren" und wählen Sie die **DICOMDIR**-Datei von Ihrer Disc. Ihre Bilder sollten geladen werden. Das war's. Der Viewer, der auf der Disc mitkam, spielte nie eine Rolle.

## Wenn Sie einen Stapel Discs haben, wird der Kampf schnell zermürbend

Wenn dies Ihre einzige Disc ist, reichen die obigen Schritte vielleicht völlig aus. Aber viele Menschen, besonders jene, die ihre Versorgung über Monate oder Jahre managen, enden mit einer Schublade voller Discs von verschiedenen Krankenhäusern. Jede einzelne hat vielleicht einen anderen defekten Viewer, eine etwas andere Ordnerstruktur und jedes Mal denselben Kampf. Und ein neuer Radiologe bittet Sie womöglich, "all Ihre früheren Aufnahmen" mitzubringen.

Genau für diesen Ärger wurde **MIA Toolkit** gemacht. Es ist eine kostenlose Desktop-App für Mac und Windows, die Ihre Bildgebungs-Discs auf Ihren Computer kopiert, eine einfache Übersicht erstellt, damit Sie sehen, was Sie haben, und alles in **ein** sauberes, standardkonformes Archiv auf einem USB-Stick zusammenfügt. Das Ergebnis ist ein einziger USB-Stick, den das System eines Radiologen oder jeder Standard-Viewer öffnen kann, statt eines Stapels Discs und jedes Mal eines anderen Kampfes. (Hier erfahren Sie, wie Sie [diesen einen USB-Stick mit Ihrem Arzt teilen](/de/blog/share-scans-one-usb/).)

Weil alles in einem ordentlichen DICOMDIR-Archiv zusammengeführt wird, umgehen Sie das Problem mit dem defekten Viewer von nun an vollständig.

## Ihre Privatsphäre hat Vorrang

MIA Toolkit läuft vollständig **offline**. Es gibt kein Konto anzulegen, keine Cloud und kein Tracking. Ihre Bilder und Ihre Informationen verlassen niemals Ihren Computer. Die App hilft Ihnen einfach, Ihre eigenen Aufnahmen zu organisieren und mitzunehmen. Sie ist kostenlos nutzbar, und das wird immer so bleiben.

## Ein paar ehrliche Worte dazu, was das ist

MIA Toolkit hilft Ihnen, **Ihre eigenen medizinischen Bilder zu organisieren und mitzunehmen**. Es ist kein Medizinprodukt. Es liest, interpretiert oder diagnostiziert Ihre Bilder nicht und ist kein Ersatz für eine Radiologin oder Ihren Arzt. Es kommt ohne Gewährleistung. Das Befunden und die Antworten kommen von qualifizierten medizinischen Fachkräften, jedes Mal.

Wenn Sie es ausprobieren möchten, können Sie [es kostenlos herunterladen](/de/?utm_campaign=bnv) — und es gibt eine [Schritt-für-Schritt-Anleitung](/de/help.html) mit Screenshots. Fragen sind willkommen unter [support@miatools.tech](mailto:support@miatools.tech).

## FAQ

**Ist es sicher, diese Dateien zu öffnen?**
Ja. Die Bilddateien auf Ihrer Disc sind medizinische Standard-Bilddateien. Sie in einem kostenlosen Viewer zu öffnen zeigt einfach die Bilder an, dieselben, die Ihr Arzt sieht. Was oft Ärger verursacht, ist das kleine Programm, das auf der Disc mitgeliefert wird, nicht die Bilder. Einen vertrauenswürdigen, kostenlosen Viewer zu nutzen, um die Dateien direkt zu öffnen, ist ein sicheres und gängiges Vorgehen. Laden Sie wie immer jeden Viewer von dessen offizieller Website herunter.

**Warum lässt sich meine Krankenhaus-CD auf meinem Mac nicht öffnen?**
Meist, weil der in die Disc eingebaute Viewer nur für Windows gemacht wurde, sodass ein Mac ihn nicht ausführen kann. Ihre Bilder sind trotzdem da, in einem Standardformat. Öffnen Sie die Disc einfach als Ordner und nutzen Sie einen Mac-tauglichen Viewer wie Weasis oder Horos, um sie direkt zu öffnen.

**Was ist DICOM und was ist eine DICOMDIR-Datei?**
DICOM ist das weltweit verwendete Standardformat für medizinische Bilder. Eine DICOMDIR-Datei ist eine Art Inhaltsverzeichnis, das alle Bilder auf Ihrer Disc auflistet, damit ein Viewer sie der Reihe nach laden kann. Ihren Viewer auf das DICOMDIR zu richten, ist oft der einfachste Weg, alles auf einmal zu öffnen.

**Muss ich für irgendetwas davon bezahlen?**
Nein. Die oben aufgeführten kostenlosen Viewer sind kostenlos nutzbar (ein paar sind kostenpflichtig mit kostenlosen Testversionen, was wir angemerkt haben). MIA Toolkit ist ebenfalls kostenlos, ohne Konto und ohne Cloud. Überprüfen Sie immer die aktuelle Lizenz jedes Programms auf dessen eigener Website, bevor Sie es installieren.
