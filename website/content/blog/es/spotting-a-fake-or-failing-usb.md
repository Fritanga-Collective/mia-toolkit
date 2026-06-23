---
title: ¿Tu memoria USB es falsa o está fallando? Cómo probarla antes de confiarle tus estudios
slug: spotting-a-fake-or-failing-usb
date: 2026-07-21
summary: Las memorias USB baratas y falsificadas fallan en silencio — aquí te decimos cómo probar una memoria, su velocidad y su capacidad real en minutos, antes de confiarle tus estudios médicos.
languages: [en, es]
status: published
tags: [guides, usb]
---

Conectas una memoria USB para copiarle tus estudios médicos, empiezas la copia y… va lentísima. Pasan minutos. Y más minutos. Una transferencia que debería tardar un par de minutos sigue corriendo una hora después, y no tienes idea de si está trabajando o atorada. O peor: termina, le entregas la memoria a tu doctor, y la mitad de los archivos no abren.

Si esto te ha pasado, el problema casi nunca es tu computadora ni el programa. Es la memoria. Las memorias USB baratas, falsificadas y gastadas son mucho más comunes de lo que la gente cree, sobre todo las gratuitas de promoción que regalan en congresos, las ofertas de "256 GB por 150 pesos" y las memorias sin marca que vienen incluidas con algún aparato. Esta guía te enseña a distinguir una memoria buena de una mala en unos dos minutos, para que nunca le confíes algo tan importante como tus imágenes médicas a una memoria que está calladamente descompuesta.

## Las tres formas en que una memoria USB se echa a perder

**Va lenta — patológicamente lenta.** Una memoria USB 2.0 sana escribe datos a más o menos 10 a 30 megabytes por segundo; una USB 3, mucho más rápido. Una mala puede caer a una fracción de megabyte por segundo — tan lenta que copiar un solo gigabyte tarda horas en vez de un minuto. Hemos visto una memoria de regalo escribir a unos 0.2 MB/s, como cien veces más lento que la memoria barata pero honesta que estaba a su lado. A esa velocidad no se ve descompuesta de forma obvia; simplemente nunca termina, y uno supone que la culpa es del programa.

**Miente sobre su tamaño (la memoria "falsificada" o de "capacidad falsa").** Esta es la fea. Un estafador toma un chip pequeñito — digamos 8 GB de almacenamiento real — y lo reprograma para que *se reporte* como 256 GB o 1 TB ante tu computadora. Todo se ve bien cuando la compras. El problema empieza cuando escribes más datos de los que el chip de verdad puede guardar: la memoria acepta los archivos, dice que los guardó, pero los bytes que pasan de la capacidad real desaparecen o sobrescriben archivos anteriores. No te enteras hasta que tratas de abrirlos después — lo cual, en el caso de estudios médicos, podría ser en el consultorio de un doctor, meses después de que el disco original ya no está. Estas memorias se venden por millones en los grandes sitios de compras.

**Simplemente está gastada o muriéndose.** La memoria flash se desgasta con el uso, y los chips más baratos se desgastan más rápido. Una memoria que se está muriendo muestra errores de escritura, corrompe archivos al azar, se niega a expulsarse, o cuelga toda la copia tan feo que ni siquiera puedes cancelar. Si una memoria alguna vez se niega a soltar una copia que ya cancelaste, tómalo como una señal de alarma seria.

## Prueba 1 — ¿Es lo bastante rápida? (dos minutos)

La revisión más rápida es una prueba de velocidad cruda: escribe un solo archivo grande y mide cuánto tarda. Esto evita el peso de copiar muchos archivos chiquitos, que hace que cualquier copia a USB vaya un poco más lenta, y te dice el ancho de banda real de la memoria.

**En una Mac**, abre Terminal y corre estos comandos uno por uno (reemplaza `MYUSB` con el nombre de tu memoria, que puedes ver en Finder o corriendo `ls /Volumes`):

```
dd if=/dev/zero of=/Volumes/MYUSB/speedtest.bin bs=1m count=200
rm /Volumes/MYUSB/speedtest.bin
```

El primer comando escribe un archivo de prueba de 200 MB e imprime una línea como `209715200 bytes transferred in 11.6 secs (18068546 bytes/sec)`. Divide ese último número entre un millón para sacar los megabytes por segundo — aquí, unos 18 MB/s, que es un buen resultado. Si ves algo por debajo de unos pocos MB/s, o el comando parece colgarse y no responde a Ctrl-C, el problema es la memoria (o el puerto donde la conectaste).

**En Windows**, la versión más sencilla es copiar un solo archivo grande (un video de 200 MB a 1 GB sirve) a la memoria y mirar la velocidad que reporta la ventana de copiado. Una memoria sana se mantiene firme en las decenas de MB/s; una mala avanza a tropezones en los cientos de kilobytes.

Si la prueba del archivo grande va lenta, antes de condenar la memoria: prueba otro puerto USB (conéctala directo a la computadora, no a través de un hub o una base), prueba otro cable, y asegúrate de no estar en un puerto USB 1.1 viejo. Una buena memoria en un mal puerto puede parecer descompuesta.

## Prueba 2 — ¿La capacidad es real? (la prueba de falsificación)

Una prueba de velocidad no atrapa a una memoria de capacidad falsa — esas pueden ir rápidas justo hasta que rebasas el chip real. Para atraparlas tienes que *llenar la memoria con datos conocidos y volverlos a leer*, comprobando que cada byte sobrevivió. Hay herramientas gratuitas y confiables que hacen exactamente esto:

- **F3** ("Fight Flash Fraud") en Mac y Linux: `f3write` llena la memoria con archivos verificables, y luego `f3read` los vuelve a leer y reporta cualquiera que haya regresado mal. Se instala con Homebrew (`brew install f3`).
- **H2testw** en Windows: el estándar de toda la vida; escribe datos de prueba por toda la memoria y los verifica.
- **ChkFlsh** / **ValiDrive** son otras opciones para Windows.

Corre una de estas en cualquier memoria nueva *antes* de ponerle algo importante. Si el paso de verificación reporta errores, la memoria es falsa o está fallando — devuélvela, y nunca la uses para datos que no te puedas dar el lujo de perder. Tarda un rato (tiene que llenar toda la memoria), pero solo lo haces una vez por memoria, y es la única forma de saber que una memoria de "1 TB" de verdad es de 1 TB.

## Cómo no salir quemado

- **Compra de marcas y vendedores con buena reputación.** SanDisk, Samsung, Kingston y similares, vendidos directamente o por el propio sitio de compras y no por un revendedor cualquiera. Si una oferta se ve demasiado buena — un terabyte al precio de un café — es falsa.
- **Prueba las memorias nuevas antes de confiar en ellas**, con las dos pruebas de arriba. Dos minutos para la velocidad; una tarde lenta (sin que la tengas que cuidar) para la revisión completa de capacidad.
- **Desconfía de las memorias gratuitas de promoción** para cualquier cosa que importe. Son la memoria flash más barata del mundo, y son justo las que hemos visto fallar.
- **Nunca dejes que una USB sea la única copia de tus estudios.** Conserva los discos originales o los archivos descargados hasta que confirmes que la memoria se lee bien en otra computadora.

## Dónde entra MIA Toolkit

Hicimos MIA Toolkit para juntar tus discos de imágenes y tus descargas en una sola USB ordenada — y como sabíamos que las memorias fallan, la app **revisa cada archivo que escribe**. Después de copiar, confirma que cada archivo de verdad llegó y tiene el tamaño correcto; si alguno no pasó, la app te avisa y lo vuelve a copiar, y puede retomar una transferencia interrumpida en lugar de empezar de cero. Así, una memoria lenta o que está fallando aparece como errores visibles y reintentos — un honesto *algo salió mal* — en vez de una copia que se detiene calladamente a la mitad y se ve terminada.

Un límite honesto, y es justo por eso que importan las pruebas de arriba: una memoria de capacidad falsa es el caso difícil, porque puede reportar un archivo con el tamaño correcto mientras los bytes reales se tiraron más allá del chip real. Ninguna herramienta de copiado puede ver a través de eso revisando tamaños — la única forma de atrapar una falsificación es llenarla y volverla a leer (Prueba 2) *antes* de confiar en ella. Así que la rutina más segura es sencilla: prueba primero una memoria nueva, luego deja que la app haga la copia y marque cualquier cosa que falle en el camino.

La herramienta es gratuita, corre completamente en tu propia computadora y nunca manda tus imágenes a ningún lado. No es un dispositivo médico, y no lee ni interpreta tus estudios — solo organiza y entrega imágenes que ya son tuyas. Si estás organizando un cajón de estudios en una USB para llevarla a una consulta, revisa primero la memoria con los pasos de arriba — luego [descarga MIA Toolkit gratis](/es/?utm_campaign=bfu) y deja que la app haga el copiado cuidadoso. Las dudas son bienvenidas en [support@miatools.tech](mailto:support@miatools.tech).
