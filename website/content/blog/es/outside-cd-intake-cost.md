---
title: El costo oculto de los discos externos: cómo medir su flujo de importación de estudios en 2 semanas
slug: outside-cd-intake-cost
date: 2026-11-05
summary: Importar los discos de estudios externos que traen los pacientes cuesta tiempo de personal que nunca aparece en el presupuesto. Dónde se esconde ese costo, qué reportan los estudios publicados y un método de 2 semanas para medirlo con sus propias cifras.
og_title: El costo oculto de los discos de imagen externos
og_description: Importar discos externos cuesta tiempo de personal que no aparece en el presupuesto. Dónde se esconde y cómo medirlo en 2 semanas.
languages: [en, es]
status: published
tags: [institutions, intake, united-states]
image: /img/blog/outside-cd-intake-cost.jpg
---

*Read in English: [Outside imaging CD import workflow: the hidden staff cost](/blog/outside-cd-intake-cost/).*

Pregunte en un hospital cuánto le cuestan los discos de estudios externos y casi siempre oirá "nada, los traen los pacientes". No hay factura ni partida en el presupuesto. Pero alguien en el archivo de imagen, en recepción o en el área de expedientes dedica parte de cada día a cargar discos, y cuando un disco falla, varias personas dedican más.

Este texto es para quienes coordinan un servicio de imagen y sospechan que ese costo es real. Explica dónde se esconde, qué reportan los estudios publicados y un método de dos semanas para medir su propio flujo de importación de discos externos.

## Dónde se esconde el costo

El trabajo con discos externos se reparte entre varios puestos, y por eso nadie ve el total:

- **Tiempo de manejo.** Registrar el disco, cargarlo, asignarlo al paciente correcto, importarlo y devolverlo. Un estudio midió una **mediana de 10 minutos de personal por disco** (Woo et al., *J Trauma Inj* 2022).
- **Fallas.** Estudios publicados reportan que **entre el 22 y el 30% de los discos externos no se logran importar** (Sodickson et al., *Radiology* 2011; Lichstein et al., *Orthopedics* 2018). Cada falla significa reintentos, otra computadora, una llamada a sistemas o al lugar de origen.
- **Nuevas solicitudes.** Si un disco no se puede leer, alguien pide al otro lugar que lo vuelva a enviar, y alguien le da seguimiento.
- **Demora.** Mientras falta el estudio previo, la interpretación que lo necesitaba espera, o se hace sin la comparación.
- **Interrupciones.** El trabajo con discos cae en personas que tienen otras tareas.

Nada de esto aparece en un reporte. Eso es lo que resuelve una medición.

## Un método de 2 semanas para medirlo

No necesita software nuevo para medir. Necesita una hoja, un punto de recepción y dos semanas normales.

### 1. Defina el alcance

Elija **un punto de recepción** (archivo de imagen, recepción, programa de segundas opiniones) y **dos semanas típicas**. Evite semanas de vacaciones o de arranque de otros sistemas.

### 2. Use una hoja de una página

Un renglón por disco, con estas columnas:

| Columna | Qué anotar |
|---|---|
| Folio | Un número que se ligue a su propio sistema. No anote nombres de pacientes en la hoja. |
| Fecha y hora de recepción | Cuándo llegó el disco. |
| Minutos de trabajo | Tiempo que alguien trabajó en él, desde el registro hasta la importación o hasta darlo por perdido. |
| ¿Se importó? | Sí o no. |
| Motivo de falla | Sin DICOMDIR, disco dañado, ZIP o formato poco común, identidad no coincide, otro. |
| Minutos de retrabajo | Tiempo extra en las fallas: llamadas, nuevas solicitudes, segundos intentos. |
| Puesto | Quién lo atendió (recepción, archivo, técnico, sistemas). |

Dos reglas hacen que los datos sean confiables: **registre todos los discos**, también los que cargaron al primer intento, y **cuente minutos de trabajo**, no el tiempo que el disco pasó en una charola.

### 3. Haga las cuentas

Al cabo de dos semanas, saque cuatro números de su hoja:

- **D:** discos por semana (total de discos ÷ 2).
- **M:** mediana de minutos de trabajo por disco.
- **F:** tasa de fallas (discos fallidos ÷ total de discos).
- **R:** promedio de minutos de retrabajo por disco fallido.

Y luego:

- **Horas de personal al año** ≈ total de minutos de trabajo efectivo del personal durante las dos semanas × 26 ÷ 60. Incluya el manejo inicial y el retrabajo, contando cada minuto una sola vez.
- **Costo de personal al año** ≈ horas al año × su costo por hora (con prestaciones) de los puestos involucrados

Use su propio costo por hora. Compare su M y su F con las cifras publicadas de arriba: si está cerca de una mediana de 10 minutos y de una tasa de fallas de entre 22 y 30%, está en el rango que describe la literatura. Si está lejos, también vale la pena saberlo.

### 4. Revise la columna de motivos

Los motivos de falla suelen señalar la solución. Los discos sin DICOMDIR o con una estructura poco estándar necesitan un paso que ordene los archivos antes de importar. Las identidades que no coinciden necesitan una revisión en la puerta. Los discos dañados necesitan una política para pedir de nuevo el estudio. Nuestra [rutina de recepción en 5 pasos](/es/blog/disco-externo-no-abre-pacs/) cubre cada caso.

## Qué hacer con la cifra

Un costo medido le permite decidir con calma: mantener el proceso, ajustar la rutina o sumar una herramienta. Si suma una, vuelva a medir dos semanas con la misma hoja y compare.

Así funciona nuestro **piloto gratuito de 60 días**. Instala **MIA Toolkit** en un equipo de recepción (unos 15 minutos, sin servidor y sin cuenta), anota cada disco durante dos semanas en una hoja de una página y luego compara con sus propias cifras y decide, sin compromiso. MIA Toolkit es una aplicación de escritorio para macOS y Windows que lee discos externos, organiza los estudios y escribe un DICOMDIR estándar en una USB o en una carpeta, listo para su flujo de importación actual. Funciona sin conexión, es de código abierto (MIT) y los estudios nunca salen del equipo.

## Cuando la brecha es más grande que un equipo

Las redes con varias sedes enfrentan el mismo problema a mayor escala: de un lado, un PACS y una red grandes; del otro, los discos, las USB y los enlaces que de verdad traen los pacientes. **MIA Bridge** es la forma en que la familia MIA Tools cierra esa brecha: importa estudios externos directo a su PACS y lleva estudios del PACS a medios limpios para el paciente, en sus instalaciones y dentro de su red. MIA Bridge está en programa piloto. [Aplica para el programa piloto](https://bridge.miatools.tech/?utm_campaign=buc).

## Siguiente paso

Si su institución está en Estados Unidos, en la [página de MIA Tools para hospitales y centros de imagen en EE. UU.](/institutions/us/?utm_campaign=buc) (en inglés) encontrará las licencias, el kit de documentos para compras y TI, una calculadora de estimación y la [solicitud del piloto](/institutions/us/?utm_campaign=buc#pilot). Si está en México, la [página para México](/es/institutions/mx/?utm_campaign=buc) tiene lo mismo en español, con el [Kit de Cumplimiento para IT](/es/institutions/mx/?utm_campaign=buc#kit). Dudas: [support@miatools.tech](mailto:support@miatools.tech).

MIA Toolkit es una herramienta de gestión de archivos: copia, organiza y convierte estudios. No interpreta imágenes ni está destinada a fines de diagnóstico, prevención, monitoreo ni tratamiento. No sustituye la revisión de un profesional de la radiología.

## Fuentes

- Sodickson et al. *Radiology*, 2011.
- Lichstein et al. *Orthopedics*, 2018.
- Woo et al. *J Trauma Inj*, 2022.

## Preguntas frecuentes

**¿Cuánto tiempo de personal cuesta un disco de estudios externo?**
Un estudio publicado midió una mediana de 10 minutos de personal por disco (Woo et al., 2022). Su cifra depende de su flujo de trabajo; dos semanas de registro le dan la suya.

**¿Qué tan seguido fallan los discos externos al importarse?**
Estudios publicados reportan que entre el 22 y el 30% de los discos externos no se logran importar (Sodickson et al., 2011; Lichstein et al., 2018). Registrar los motivos de falla dos semanas le muestra qué tan seguido pasa en su centro, y por qué.

**¿Hace falta anotar nombres de pacientes en la hoja de medición?**
No. Use un folio que se ligue a su sistema y deje fuera los datos del paciente. La medición solo necesita tiempos, resultados y motivos.

**¿El piloto envía datos a MIA?**
No. MIA Toolkit funciona sin conexión en un solo equipo y no envía nada. La hoja de medición se queda con usted; solo comparte las cifras que usted decida.
