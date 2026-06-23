---
title: Les meilleures visionneuses DICOM gratuites et portables pour Windows et Mac
slug: free-portable-dicom-viewers
date: 2026-06-30
summary: Comparatif des visionneuses DICOM gratuites pour Windows et Mac — et une astuce simple pour placer une visionneuse portable sur la même clé USB, afin que n'importe qui puisse ouvrir vos images sans aucune installation.
languages: [en, es, zh, ms, ta, de, fr]
status: published
tags: [guides, dicom, viewers]
translation: machine
---

Si vous avez rassemblé vos images médicales sur une clé USB, vous vous demandez peut-être comment quiconque est censé les ouvrir. Les images d'hôpital ne sont pas comme les photos de votre téléphone. Elles sont dans un format particulier appelé DICOM, et votre ordinateur ne peut généralement pas les afficher d'un simple double-clic. Pour les voir, il vous faut un petit programme appelé une visionneuse DICOM.

La bonne nouvelle, c'est qu'il existe des visionneuses gratuites pour Windows comme pour Mac. Certaines sont même « portables », ce qui signifie qu'elles peuvent voyager directement sur la même clé USB que vos images. Ainsi, lorsque vous remettez la clé à un médecin, à un proche ou à une clinique, ils peuvent tout ouvrir sans rien installer.

Ce guide compare quelques visionneuses fiables et vous montre une astuce simple : placer une visionneuse sur la clé USB, à côté de votre archive, pour que la personne qui la reçoit puisse l'ouvrir sans aucune installation.

## Ce qu'il faut rechercher dans une visionneuse

Vous n'avez besoin de rien de sophistiqué. En tant que patient ou aidant, trois choses comptent avant tout.

D'abord, elle doit être **gratuite**. Il n'y a aucune raison de payer pour regarder vos propres images.

Ensuite, elle doit **ouvrir un DICOMDIR**. Un DICOMDIR est ce petit fichier « table des matières » qui relie entre eux tous les éléments d'un examen d'imagerie. Lorsque votre archive en contient un, une bonne visionneuse peut lire l'examen complet dans l'ordre, au lieu de vous laisser chercher parmi des fichiers épars.

Enfin, si possible, elle doit être **portable**. Une visionneuse portable fonctionne directement depuis la clé USB, sans être installée sur l'ordinateur. C'est l'ingrédient magique. Si la visionneuse voyage sur la même clé que vos images, toute personne à qui vous la remettez peut ouvrir les images, même si elle n'a jamais vu de fichier DICOM et ne peut rien installer sur son ordinateur.

Une remarque honnête et rapide : les licences des logiciels, les liens de téléchargement et les fonctionnalités évoluent avec le temps. Les détails ci-dessous étaient exacts au moment de la rédaction de ce guide, mais vérifiez vous-même la licence et la page de téléchargement avant d'installer quoi que ce soit. Nous ne recommandons aucun éditeur en particulier. Il s'agit simplement d'options qu'il est utile de connaître.

## Un comparatif de visionneuses gratuites et peu coûteuses

Voici un aperçu côte à côte de cinq visionneuses bien connues, classées selon le système sur lequel elles fonctionnent et selon leur capacité à voyager sur une clé USB.

| Visionneuse | Plateforme | Coût | Portable (fonctionne depuis l'USB) | Ouvre un DICOMDIR | Idéale pour |
|---|---|---|---|---|---|
| Weasis | Windows, macOS, Linux | Gratuite et open source | Oui | Oui | Le choix multiplateforme par défaut ; peut fonctionner depuis l'USB |
| MicroDicom | Windows uniquement | Gratuite pour un usage personnel | Oui | Oui | Le choix Windows le plus simple à déposer sur l'USB |
| Horos | macOS uniquement | Gratuite et open source | Non (s'installe) | Oui | Utilisateurs Mac prêts à installer une visionneuse |
| OsiriX Lite | macOS uniquement | Gratuite avec limites | Non | Oui | Visualisation de base sur Mac |
| RadiAnt | Windows | Payante (essai gratuit) | Limitée | Oui | Utilisateurs avertis recherchant la rapidité (à noter : payante) |

Si vous voulez retenir une seule chose simple : **Weasis** est le choix le plus sûr et le plus polyvalent, car elle fonctionne sous Windows comme sous Mac et peut s'exécuter depuis l'USB. Si les personnes qui reçoivent votre clé n'utilisent que Windows, **MicroDicom** est un choix simple et léger qui voyage lui aussi sur la clé.

Les visionneuses pour Mac, Horos et OsiriX Lite, conviennent bien pour regarder des images sur votre propre Mac, mais elles doivent d'abord être installées, ce qui les rend moins pratiques pour une clé USB que vous comptez faire circuler. RadiAnt est rapide et appréciée, mais c'est un logiciel payant proposé avec un essai gratuit.

## Comment placer une visionneuse portable sur la même clé USB

C'est la partie qui facilite la vie de la personne qui ouvre votre clé. L'idée est simple : ranger la visionneuse et vos images ensemble, pour qu'ouvrir les images se fasse en une seule étape.

1. **Commencez par votre archive.** Vous devriez déjà disposer de votre clé USB regroupant toutes vos images dans une archive DICOMDIR bien organisée. Si vous avez utilisé MIA Toolkit pour la créer, vous êtes en bonne voie, car il assemble un DICOMDIR unique et conforme aux normes, que les visionneuses savent lire.

2. **Téléchargez une visionneuse portable.** Depuis votre propre ordinateur, récupérez la version portable de Weasis (fonctionne partout) ou de MicroDicom (Windows). Téléchargez toujours depuis le site officiel et vérifiez d'abord la licence.

3. **Copiez la visionneuse sur la clé USB.** Placez les fichiers de la visionneuse portable dans un dossier clairement nommé sur la même clé, par exemple un dossier intitulé « Visionneuse ». Gardez-le distinct des dossiers d'images afin que rien ne se mélange.

4. **Ajoutez une courte note.** Créez sur la clé un simple fichier texte nommé, par exemple, « À LIRE D'ABORD ». En mots simples, indiquez au lecteur : ouvrez le dossier Visionneuse, lancez le programme, puis ouvrez le fichier DICOMDIR situé dans le dossier des images. Deux ou trois phrases bienveillantes suffisent.

5. **Testez vous-même.** Avant de remettre la clé, branchez-la sur un ordinateur et essayez d'ouvrir les images à l'aide de la visionneuse présente sur la clé. Si cela fonctionne pour vous, cela fonctionnera pour eux.

Désormais, la personne qui reçoit votre clé — qu'il s'agisse d'un nouveau spécialiste, d'une clinique pour un deuxième avis ou d'un proche qui vous aide — peut ouvrir la visionneuse directement depuis l'USB et voir vos images. Pas de compte, pas d'installation, pas d'attente. (Pour en savoir plus sur la remise de cette clé aux bonnes personnes, consultez notre guide pour [partager vos examens sur une seule clé USB](/fr/blog/share-scans-one-usb/).)

## Où MIA Toolkit intervient

Une visionneuse affiche les images. Il faut encore quelque chose pour les rassembler et les organiser au préalable, et c'est précisément le rôle pour lequel MIA Toolkit a été conçu.

MIA Toolkit est une application de bureau gratuite pour macOS et Windows qui copie vos CD d'imagerie hospitalière, dresse un inventaire pour que vous puissiez voir ce que vous possédez, et assemble le tout dans une seule archive DICOMDIR conforme aux normes sur une clé USB. Cette archive unique et bien formée est exactement ce que les visionneuses ci-dessus sont conçues pour ouvrir. Associez-la à une copie portable de Weasis ou de MicroDicom sur la même clé, et vous obtenez un ensemble bien rangé que n'importe qui peut lire.

Votre vie privée vous appartient du début à la fin. MIA Toolkit fonctionne entièrement hors ligne. Il n'y a aucun compte à créer, rien n'est envoyé vers le cloud et il n'y a aucun suivi. Vos images ne quittent jamais vos mains.

Et c'est gratuit. MIA Toolkit est gratuit, et le restera toujours.

Un avertissement en langage clair : MIA Toolkit vous aide à organiser et à transmettre vos *propres* images médicales. Ce n'est pas un dispositif médical. Il n'interprète pas et ne lit pas vos images, et il ne peut pas vous dire ce qu'elles signifient. Il ne remplace ni un radiologue, ni aucun autre médecin. Les visionneuses mentionnées ici sont conçues par d'autres entreprises et ne sont citées qu'à titre d'options ; vérifiez vous-même leurs licences et leurs téléchargements. Tout ce qui est présenté ici l'est sans aucune garantie.

Si vous souhaitez l'essayer, vous pouvez [télécharger MIA Toolkit gratuitement](/fr/?utm_campaign=bpv) — il existe un [guide pas à pas](/fr/help.html). Vos questions sont les bienvenues à [support@miatools.tech](mailto:support@miatools.tech).

## FAQ

**Ai-je besoin d'une visionneuse DICOM pour utiliser MIA Toolkit ?**
Non. MIA Toolkit construit l'archive organisée sur votre clé USB. La visionneuse est le programme distinct qui ouvre et affiche les images. Vous n'avez besoin d'une visionneuse que lorsque vous, ou quelqu'un d'autre, souhaitez réellement regarder les images.

**Quelle visionneuse choisir si je ne suis pas sûr ?**
Weasis est le point de départ le plus souple. Elle est gratuite, ouvre un DICOMDIR et peut fonctionner directement depuis l'USB, sous Windows comme sous Mac. Si toutes les personnes qui ouvriront la clé utilisent Windows, MicroDicom est une option plus simple qui voyage elle aussi sur la clé.

**Que veut vraiment dire « portable » ?**
Une visionneuse portable n'a pas besoin d'être installée sur un ordinateur. Elle fonctionne directement depuis le dossier où elle se trouve, y compris un dossier sur votre clé USB. Cela permet à la personne qui reçoit votre clé d'ouvrir vos images sans rien modifier sur son ordinateur.

**Le cabinet de mon médecin pourra-t-il ouvrir la clé ?**
La plupart des cliniques disposent de leurs propres systèmes de visualisation professionnels, capables de lire une archive DICOMDIR standard ; la clé devrait donc s'ouvrir directement chez eux. Ajouter une visionneuse portable est une sécurité bienveillante pour quiconque ne dispose pas d'un tel système à portée de main, comme un proche ou un petit cabinet.
