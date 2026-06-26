---
title: Comment ouvrir un CD d'imagerie d'hôpital quand il n'y a pas de visionneuse (ou qu'il refuse de s'ouvrir sur un Mac)
slug: open-hospital-cd-no-viewer-mac
date: 2026-07-07
summary: Votre CD d'hôpital ne s'ouvre pas ? Les images sont presque certainement intactes — voici comment passer outre la visionneuse défaillante et ouvrir vos examens sur un Mac ou un PC Windows.
languages: [en, es, zh, ms, ta, de, fr]
status: published
tags: [guides, dicom, mac]
translation: machine
---

Vous êtes rentré de l'hôpital avec un CD de votre examen. Vous l'insérez dans votre ordinateur, et... rien. Peut-être qu'une fenêtre apparaît puis se fige. Peut-être qu'on vous demande d'installer quelque chose qui ne fonctionne jamais. Peut-être que vous êtes sur un Mac et que le disque semble ne rien faire du tout.

Respirez. C'est l'une des frustrations les plus courantes que rencontrent les gens, et la bonne nouvelle, c'est que vos images réelles sont presque certainement intactes. Le problème vient généralement du petit programme de visualisation fourni sur le disque, pas des images elles-mêmes. Voyons ensemble comment accéder à vos images, calmement et étape par étape.

## Le disque contient deux choses différentes

Voici ce que personne n'explique à l'hôpital. Un CD d'imagerie contient presque toujours deux choses distinctes :

1. **Un programme de visualisation** que le disque essaie de lancer automatiquement. C'est la petite application qui s'ouvre (ou tente de s'ouvrir) lorsque vous insérez le disque.
2. **Vos images médicales réelles**, stockées sous forme de fichiers standard dans un format appelé DICOM.

La visionneuse et les images sont séparées. Lorsque votre disque « ne s'ouvre pas », c'est presque toujours la *visionneuse* qui pose problème, pas vos images. Peut-être que la visionneuse a été conçue uniquement pour Windows et que vous êtes sur un Mac. Peut-être qu'elle est ancienne, ou endommagée, ou que les paramètres de sécurité de votre ordinateur la bloquent.

Le soulagement est simple : vous n'avez pas du tout besoin de cette visionneuse. Vos images sont des fichiers standard, et de nombreux programmes gratuits et modernes peuvent les ouvrir directement.

## Étape 1 : Regardez ce qui se trouve réellement sur le disque

Plutôt que de laisser le disque exécuter son propre programme, ouvrons-le comme un dossier ordinaire et regardons à l'intérieur.

- **Sur un Mac :** Insérez le disque. Une icône le représentant devrait apparaître sur votre bureau ou dans une fenêtre du Finder, sur le côté gauche. Double-cliquez sur cette icône pour voir les fichiers, plutôt que de lancer une fenêtre contextuelle qui apparaîtrait.
- **Sur Windows :** Insérez le disque. Si une fenêtre vous demande ce que vous souhaitez faire, choisissez « Ouvrir le dossier pour afficher les fichiers ». Si rien n'apparaît, ouvrez l'**Explorateur de fichiers**, puis cliquez sur le lecteur de disque (souvent désigné par D: ou E:) sur la gauche.

Regardez maintenant les noms de fichiers. Vous cherchez deux choses :

- Un fichier nommé **DICOMDIR** (sans extension). C'est comme une table des matières de toutes vos images.
- Un dossier, souvent appelé **DICOM** ou **IMAGES**, rempli de fichiers portant des noms comme `IM_0001` ou des nombres sans extension familière.

Si vous voyez cela, félicitations. Vos images sont là et intactes. La visionneuse défaillante du disque n'a jamais été le véritable obstacle.

## Étape 2 : Ouvrez vos images avec une visionneuse gratuite

Vous n'ouvrez pas ces fichiers en double-cliquant dessus. Vous installez plutôt une visionneuse gratuite, puis vous la dirigez vers le fichier **DICOMDIR** ou vers le dossier d'images. Voici des options gratuites, regroupées par type d'ordinateur. Veuillez vérifier sur le site web de chaque programme les liens de téléchargement et les licences en vigueur avant d'installer. (Pour un comparatif plus complet, consultez notre guide des [visionneuses DICOM gratuites et portables](/fr/blog/free-portable-dicom-viewers/).)

**Si vous avez un Mac :**

- **Weasis** fonctionne sur Mac, Windows et Linux. Elle est gratuite et open source, ouvre un DICOMDIR et propose même une version portable qui peut fonctionner depuis une clé USB. Un bon choix polyvalent.
- **Horos** est réservée au Mac, gratuite et open source. Elle s'installe sur votre ordinateur (pas de version portable) et ouvre un DICOMDIR.
- **OsiriX Lite** est réservée au Mac et gratuite avec quelques limites. Elle s'installe sur votre ordinateur.

**Si vous avez un PC Windows :**

- **MicroDicom** est réservée à Windows et gratuite pour un usage personnel. C'est à peu près l'option la plus simple, elle dispose d'une version portable et ouvre un DICOMDIR.
- **Weasis** (mentionnée ci-dessus) fonctionne aussi sous Windows et peut s'exécuter depuis une clé USB.
- **RadiAnt** est un programme Windows qui ouvre un DICOMDIR. Elle est payante, avec un essai gratuit disponible.

Une fois une visionneuse installée, ouvrez-la, cherchez une option de menu comme « Ouvrir » ou « Importer », et choisissez le fichier **DICOMDIR** de votre disque. Vos images devraient se charger. C'est tout. La visionneuse fournie sur le disque n'a jamais eu d'importance.

## Quand vous avez une pile de disques, le combat lasse vite

Si c'est votre seul disque, les étapes ci-dessus suffiront peut-être pour toujours. Mais beaucoup de gens, surtout ceux qui gèrent des soins sur des mois ou des années, finissent avec un tiroir plein de disques provenant de différents hôpitaux. Chacun peut avoir une visionneuse défaillante différente, une organisation des dossiers légèrement différente, et la même galère à chaque fois. Et un nouveau radiologue peut vous demander d'apporter « toutes vos images antérieures ».

C'est exactement le casse-tête pour lequel **MIA Toolkit** a été conçu. C'est une application de bureau gratuite pour Mac et Windows qui copie vos disques d'imagerie sur votre ordinateur, dresse un inventaire simple pour que vous voyiez ce que vous possédez, et assemble le tout dans **une seule** archive propre et conforme aux normes sur une clé USB. Le résultat est une clé USB unique que le système d'un radiologue ou n'importe quelle visionneuse standard peut ouvrir, au lieu d'une pile de disques et d'un combat différent à chaque fois. (Voici comment [partager cette unique clé USB avec votre médecin](/fr/blog/share-scans-one-usb/).)

Comme tout est regroupé dans une seule archive DICOMDIR en bonne et due forme, vous évitez entièrement le problème de la visionneuse défaillante à l'avenir.

## Votre vie privée passe avant tout

MIA Toolkit fonctionne entièrement **hors ligne**. Il n'y a aucun compte à créer, aucun cloud et aucun suivi. Vos images et vos informations ne quittent jamais votre ordinateur. L'application vous aide simplement à organiser et à transporter vos propres examens. Elle est gratuite, et le restera toujours.

## Quelques mots honnêtes sur ce que c'est

MIA Toolkit vous aide à **organiser et à transporter vos propres images médicales**. Ce n'est pas un dispositif médical. Il ne lit pas, n'interprète pas et ne diagnostique pas vos images, et il ne remplace ni un radiologue ni votre médecin. Il est fourni sans aucune garantie. La lecture et les réponses viennent de professionnels de santé qualifiés, à chaque fois.

Si vous souhaitez l'essayer, vous pouvez [le télécharger gratuitement](/fr/?utm_campaign=bnv) — et il existe un [guide pas à pas](/fr/help.html) avec captures d'écran. Vos questions sont les bienvenues à [support@miatools.tech](mailto:support@miatools.tech).

## FAQ

**Est-il sans risque d'ouvrir ces fichiers ?**
Oui. Les fichiers d'images de votre disque sont des fichiers d'images médicales standard. Les ouvrir dans une visionneuse gratuite ne fait qu'afficher les images, les mêmes que celles que voit votre médecin. Ce qui pose souvent problème, c'est le petit programme fourni sur le disque, pas les images. Utiliser une visionneuse gratuite et fiable pour ouvrir les fichiers directement est une approche sûre et courante. Comme toujours, téléchargez toute visionneuse depuis son site web officiel.

**Pourquoi mon CD d'hôpital ne s'ouvre-t-il pas sur mon Mac ?**
Généralement parce que la visionneuse intégrée au disque a été conçue uniquement pour Windows, et qu'un Mac ne peut donc pas l'exécuter. Vos images sont toujours là, dans un format standard. Ouvrez simplement le disque comme un dossier et utilisez une visionneuse compatible Mac, comme Weasis ou Horos, pour les ouvrir directement.

**Qu'est-ce que le DICOM et qu'est-ce qu'un fichier DICOMDIR ?**
Le DICOM est le format standard utilisé dans le monde entier pour les images médicales. Un fichier DICOMDIR est une sorte de table des matières qui répertorie toutes les images de votre disque, afin qu'une visionneuse puisse les charger dans l'ordre. Diriger votre visionneuse vers le DICOMDIR est souvent le moyen le plus simple de tout ouvrir d'un coup.

**Dois-je payer pour tout cela ?**
Non. Les visionneuses gratuites listées ci-dessus sont gratuites à utiliser (deux d'entre elles sont payantes avec un essai gratuit, ce que nous avons signalé). MIA Toolkit est également gratuit, sans compte ni cloud. Vérifiez toujours la licence en vigueur de chaque programme sur son propre site web avant d'installer.
