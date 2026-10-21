---
translated_from: ee3799ea6e0851353a78d3216ea4dc99c71db380c8e815354b1c4639f0cd145b
note: Traducción es-MX (usted) de content/en/security.md. Edición México. Mantener la línea de finalidad de uso de México tal cual (INSTITUTIONS-LAUNCH-READINESS R5). Nunca escribir "no es un dispositivo médico", "aprobado por COFEPRIS", "exento de registro", "cumple NOM-024" ni "para diagnóstico".
---
<!-- lead -->
Para la revisión de cumplimiento y seguridad de la información. MIA Toolkit es una aplicación de escritorio gratuita, de código abierto (MIT) y **sin conexión** que reúne los medios de imagen de un paciente (CDs, carpetas USB, descargas ZIP) en un solo archivo DICOMDIR (el conjunto de archivos DICOM estándar para medios) en una memoria USB.

<!-- body -->
## Arquitectura

- **Procesamiento 100 % local.** Todo ocurre en la estación de trabajo. Los medios de imagen se leen del medio de origen, se procesan localmente y se escriben en el disco local y en una memoria USB de destino.
- **Sin componente de servidor.** MIA Toolkit no tiene backend, API ni servicio en la nube. El proveedor no opera servidores que reciban datos de la aplicación.
- **Los datos de pacientes no salen del equipo.** La información de salud de los pacientes nunca sale de la estación de trabajo ni de la memoria USB en la que escribe el usuario. El proveedor nunca ve, recibe ni almacena datos de pacientes.
- **Sin telemetría, sin analítica, sin cuenta.** La única conexión de red de la aplicación es **Buscar actualizaciones**, que inicia el usuario: una sola solicitud HTTPS GET a un archivo estático (`https://miatools.tech/version.json`), solo cuando un usuario hace clic, con un User-Agent genérico sin versión, sin parámetros de consulta y sin identificadores. Nunca se envía nada en segundo plano, y la aplicación nunca descarga ni instala nada por sí misma. Funciona por completo en un equipo aislado de la red (la búsqueda de actualizaciones solo indicará que no pudo verificar).

## Código abierto (auditable)

El software se distribuye bajo la **Licencia MIT** y todo el código fuente es público y revisable en **https://github.com/Fritanga-Collective/mia-toolkit** (enlazado desde https://miatools.tech). Su equipo de seguridad puede verificar exactamente qué hace la aplicación; la búsqueda de actualizaciones está en `mia/gui/updates.py`.

## Estado de la firma de código

- **macOS:** firmado con un certificado **Developer ID** de Apple y **notarizado** por Apple (con ticket adjunto) desde la v0.1.5. Verifíquelo con `spctl --assess --type execute -vv "MIA Toolkit.app"`.
- **Windows:** **el instalador aún no está firmado,** por lo que SmartScreen puede mostrar "Editor desconocido" (elija Más información → Ejecutar de todas formas). Está previsto un certificado de firma de código Authenticode (Certum Open Source Code Signing); actualizaremos esta línea cuando se publiquen instaladores firmados.
- **Sumas de verificación:** el SHA-256 de cada instalador de cada versión se publica en `https://miatools.tech/version.json`.

Verifique la firma y la suma de verificación antes del despliegue.

## Flujo de datos

{{FLOW}}

## Privacidad y marco regulatorio

- **Aviso de privacidad:** https://miatools.tech (Política de privacidad). La aplicación está diseñada para que el proveedor *no pueda* ver sus datos: sin conexión, sin cuenta, sin telemetría, sin cookies ni rastreo en la aplicación.
- **Procesamiento local bajo sus controles:** MIA Toolkit procesa los datos de pacientes **localmente, bajo los controles que su institución ya tiene** (seguridad de los equipos, control de acceso, política de USB, seguridad física). Como el proveedor nunca toca datos de pacientes y no opera servidores, no existe una relación de tratamiento de datos con un tercero que evaluar respecto al manejo de datos de la aplicación: la información permanece dentro del entorno de su institución. Este documento no constituye asesoría legal ni de cumplimiento; confírmelo con los requisitos aplicables en su jurisdicción.

{{MARKET}}

## Soporte y datos de pacientes

Nunca necesitamos datos de pacientes. Envíe solo capturas de pantalla o registros (logs) sin datos identificables; nunca estudios, archivos DICOM ni información de salud de pacientes. El soporte es de mejor esfuerzo, por correo a **support@miatools.tech**, con un objetivo de primera respuesta de **2 días hábiles**.

## Divulgación responsable

Reporte de forma privada cualquier posible problema de seguridad a **support@miatools.tech** (o mediante el reporte privado de vulnerabilidades de GitHub en el repositorio; política en `SECURITY.md`). Incluya la versión afectada, el sistema operativo y los pasos para reproducirlo, y nunca incluya datos reales de pacientes en sus reportes.

<!-- market -->
#### México

MIA Toolkit es una herramienta de gestión de archivos: copia, organiza y convierte estudios DICOM de CDs a un archivo DICOMDIR en USB. No interpreta, no mide y no sustituye a un sistema PACS ni a una estación de diagnóstico. No está destinado a fines de diagnóstico, prevención, monitoreo ni tratamiento.
