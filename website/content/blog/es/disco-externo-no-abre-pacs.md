---
title: Cuando un disco de estudios no abre en su PACS: rutina de recepción en 5 pasos
slug: disco-externo-no-abre-pacs
date: 2026-10-29
summary: ¿El disco de estudios no abre o no se importa a su PACS? Una rutina de recepción de discos externos en 5 pasos para centros de imagen, con pasos para macOS y Windows y una forma sencilla de medir cuánto tiempo le cuesta.
og_title: ¿El disco externo no abre en su PACS? 5 pasos
og_description: Una rutina de recepción de discos externos en 5 pasos, con pasos para macOS y Windows y una forma sencilla de medir cuánto tiempo le cuesta.
languages: [es, en]
status: published
tags: [institutions, intake, mexico]
image: /img/blog/disco-externo-no-abre-pacs.jpg
---

*Read in English: [When an outside disc won't import into your PACS](/blog/disco-externo-no-abre-pacs/).*

Es una escena diaria en recepción. Un paciente llega con el disco de estudios que le dieron en otro lugar, el radiólogo necesita compararlo y el disco no abre, o abre pero no se importa a su PACS. Alguien de su equipo lo intenta otra vez, cambia de computadora, llama a sistemas, y al final el paciente se va con la promesa de "se lo cargamos después".

No es un problema de su equipo. Estudios publicados reportan que **entre el 22 y el 30% de los discos externos no se logran importar** (Sodickson et al., *Radiology* 2011; Lichstein et al., *Orthopedics* 2018) y que el personal dedica una **mediana de 10 minutos por disco** (Woo et al., *J Trauma Inj* 2022). Lo que sí puede controlar su centro es la rutina. Esta es una que puede adoptar mañana, en cinco pasos.

## Paso 1: registre el disco antes de abrirlo

Antes de meterlo a la computadora, anote lo básico en una hoja o en su sistema:

- Nombre completo y fecha de nacimiento del paciente.
- Lugar de origen del disco y fecha aproximada del estudio.
- Número de discos que entrega (a veces son dos o tres).
- Hora de recepción.

Rotule el sobre con el folio. Parece burocracia, pero es lo que evita que un disco se pierda entre turnos y le da el dato para el paso 5.

## Paso 2: ábralo como carpeta, sin ejecutar el visor del disco

Muchos discos traen un visor que intenta arrancar solo. No lo necesita para importar, y ejecutar programas de origen desconocido en un equipo de su red no es buena práctica.

- **En macOS:** inserte el disco (con una unidad USB si el equipo no tiene lector). Aparece en el escritorio o en la barra lateral del Finder. Ábralo con doble clic como cualquier carpeta.
- **En Windows:** si aparece la ventana de reproducción automática, ciérrela o elija **Abrir carpeta para ver archivos**. Si no, abra el **Explorador de archivos** y entre a la unidad de disco (D:, E:).

Busque un archivo **DICOMDIR** en la raíz y una carpeta con los estudios (por ejemplo **DICOM** o **IMAGES**). Si no hay DICOMDIR, si los archivos están dentro de un ZIP, o si solo ve el visor y ninguna carpeta de imágenes, anótelo: son motivos habituales de que la importación falle.

## Paso 3: confirme la identidad antes de importar

Antes de que cualquier estudio entre a su PACS, compare lo que muestra su herramienta de importación (nombre, fecha de nacimiento, fecha y tipo de estudio) con la orden o el expediente del paciente. Si un disco trae estudios de otra persona, o de varias, deténgase y avise al responsable. Corregir un estudio mal asignado dentro del PACS cuesta mucho más que revisarlo en la puerta.

## Paso 4: importe una vez; si falla, no insista con el mismo disco

Intente la importación habitual desde el DICOMDIR. Si falla, repetirla con el mismo disco rara vez cambia el resultado. En lugar de eso:

1. **Copie el contenido del disco a una carpeta local** del equipo de recepción, para trabajar sobre una copia y no sobre el disco.
2. **Genere una copia ordenada con un DICOMDIR estándar** y pruebe la importación con esa copia. A veces la falla viene de la estructura del disco (un índice faltante o rutas no estándar), no de las imágenes.
3. **Si sigue fallando, escale con datos:** anote el mensaje de error y el origen del disco. Sistemas puede resolver mucho más rápido con esa nota que con "no abre".

Para el punto 2 existe **MIA Toolkit**: una aplicación de escritorio para macOS y Windows que lee los discos externos, organiza los estudios y escribe un DICOMDIR estándar en una USB o en una carpeta, lista para su flujo de importación actual. Funciona sin conexión en un solo equipo, es de código abierto (MIT) y no requiere cuenta: los estudios nunca salen de la estación de trabajo. ([Qué son DICOM, DICOMDIR y PACS](/es/blog/dicom-dicomdir-pacs-explained/), para capacitar a su personal nuevo.)

## Paso 5: cierre el registro

Al terminar, complete la línea del paso 1:

- **Minutos de trabajo activo del personal** dedicados a registrar, revisar e importar el disco, incluidos los reintentos y el seguimiento; excluya las esperas en cola y las copias sin intervención.
- **¿Se importó?** Sí o no.
- **Motivo**, si falló: sin DICOMDIR, disco dañado, ZIP, identidad no coincide, otro.

Devuelva el disco al paciente según su política. Con dos semanas de estas líneas sabrá cuántos discos recibe, cuánto tiempo le cuestan y cuántos fallan, con sus propios números y no con los de un artículo. Esa medición es exactamente el paso 3 de nuestro [piloto gratuito de 60 días](/es/institutions/mx/?utm_campaign=bnd#pilot).

## Cuando el problema ya no es un disco, sino la red

La rutina anterior resuelve la recepción en un equipo. En centros con varias sucursales, un PACS central y estudios que llegan en disco, USB o enlace, la brecha está entre esa infraestructura grande y los medios que traen los pacientes. **MIA Bridge** es nuestra respuesta para cerrarla: importa estudios externos directo a su PACS y lleva estudios del PACS a medios limpios para el paciente, en sus instalaciones y dentro de su red, como parte de la familia MIA Tools. MIA Bridge está en programa piloto. [Aplica para el programa piloto](https://bridge.miatools.tech/?utm_campaign=bnd).

## Para su centro

En la [página para centros de imagen y hospitales en México](/es/institutions/mx/?utm_campaign=bnd) encontrará las licencias, el [Kit de Cumplimiento para IT](/es/institutions/mx/?utm_campaign=bnd#kit) (ficha de seguridad, guía de instalación para TI, términos de licencia y ejemplo de certificado) y la solicitud del piloto gratuito de 60 días. Para dudas: [support@miatools.tech](mailto:support@miatools.tech).

MIA Toolkit es una herramienta de gestión de archivos: copia, organiza y convierte estudios. No interpreta imágenes ni está destinada a fines de diagnóstico, prevención, monitoreo ni tratamiento. No sustituye la revisión de un profesional de la radiología.

## Fuentes

- Sodickson et al. *Radiology*, 2011.
- Lichstein et al. *Orthopedics*, 2018.
- Woo et al. *J Trauma Inj*, 2022.

## Preguntas frecuentes

**¿Por qué un disco de estudios no abre o no se importa al PACS?**
Algunas causas habituales son de estructura: el disco no trae un DICOMDIR, los archivos están comprimidos en un ZIP o el disco solo trae un visor. Un disco rayado también puede fallar. Revisar el disco como carpeta antes de importar le dice en segundos cuál es el caso.

**¿Hay que usar el visor que viene en el disco?**
No para importar. El visor sirve para ver las imágenes en una computadora sin otro programa, pero su flujo de importación necesita los archivos DICOM y, de preferencia, un DICOMDIR. Evite ejecutar programas de origen desconocido en equipos de su red.

**¿Cuánto tiempo le cuesta a un centro cada disco externo?**
Un estudio publicado reporta una mediana de 10 minutos de personal por disco (Woo et al., 2022). Su cifra real puede ser distinta: dos semanas de registro con los cinco pasos de arriba se la dan.

**¿MIA Toolkit envía los estudios a algún servidor?**
No. Funciona sin conexión en un solo equipo y no envía nada. El único acceso a red que puede hacer es una revisión de actualizaciones que el usuario inicia a mano, sin identificadores.
