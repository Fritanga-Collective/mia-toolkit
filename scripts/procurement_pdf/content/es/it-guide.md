---
translated_from: a2264b4b62439d8b4ef258c09e884d3a25292dece8b499a9d011460365f2ede1
note: Traducción es-MX (usted) de content/en/it-guide.md. Los comandos, rutas y claves de registro no se traducen; solo los comentarios.
---
<!-- lead -->
Para los equipos de TI de hospitales y clínicas que despliegan MIA Toolkit. MIA Toolkit es una aplicación de escritorio gratuita, de código abierto (MIT) y **sin conexión** que reúne los medios de imagen de un paciente (CDs, carpetas USB, descargas ZIP) en un solo archivo DICOMDIR (el conjunto de archivos DICOM estándar para medios) en una memoria USB. Su única conexión de red es la búsqueda de actualizaciones que inicia el usuario, descrita más abajo; fuera de ella **no hace ninguna conexión de red**.

<!-- body -->
## Requisitos del sistema

| | Mínimo |
|---|---|
| **macOS** | macOS 12 o posterior (`LSMinimumSystemVersion` 12.0) |
| **Windows** | Windows 10 u 11 de 64 bits (x64; también se instala en Windows 11 en ARM, con emulación x64) |
| Disco | Espacio libre suficiente para los medios de imagen que se van a reunir |
| Red | No se requiere (solo para la descarga) |

## Modelo de instalación

### Windows (instalador Inno Setup `MIA-Toolkit-Setup-<ver>.exe`)

El instalador está configurado con `PrivilegesRequired=lowest` y `PrivilegesRequiredOverridesAllowed=dialog`. Esto ofrece dos modos de instalación:

| Modo | Cómo se elige | Carpeta predeterminada | Acceso directo en Inicio | Registro de desinstalación |
|---|---|---|---|---|
| **Por usuario (predeterminado)** | predeterminado; o `/CURRENTUSER` | `%LOCALAPPDATA%\Programs\MIA Toolkit` | menú Inicio del usuario actual | `HKCU` |
| **Todos los usuarios (todo el equipo)** | "Instalar para todos los usuarios" en el diálogo de modo de instalación (requiere administrador / UAC); o `/ALLUSERS` | vea la advertencia abajo | menú Inicio de todos los usuarios | `HKLM` |

- El modo por usuario **no requiere derechos de administrador** y no hace cambios en todo el equipo.
- Según la documentación de Inno Setup, permitir `dialog` habilita automáticamente los parámetros de línea de comandos `/ALLUSERS` y `/CURRENTUSER`, y usar cualquiera de ellos omite el diálogo.<sup>†</sup>
- **Advertencia para instalaciones en todo el equipo:** la carpeta predeterminada se define con `{localappdata}`, que es una ubicación por usuario incluso en el modo para todos los usuarios. Por lo tanto, una instalación con `/ALLUSERS` se ubica por defecto en `%LOCALAPPDATA%\Programs` *del administrador que instala*, a menos que indique `/DIR`. Para una instalación en todo el equipo, indique siempre `/DIR="C:\Program Files\MIA Toolkit"`.<sup>†</sup>
- Las actualizaciones se instalan en el mismo lugar: el instalador tiene un `AppId` fijo, así que una versión nueva reemplaza a la anterior en la misma carpeta y el mismo modo.
- No hay MSI. Para Intune, empaquete el `.exe` como aplicación Win32 (`.intunewin`) y use las líneas de comandos de abajo; elija el contexto de instalación **User** para el modo por usuario o **System** para `/ALLUSERS`.<sup>†</sup>

### macOS (`MIA-Toolkit-<ver>.dmg`)

La aplicación se distribuye como un `.app` firmado y notarizado dentro de un `.dmg`. Copie `MIA Toolkit.app` a `/Applications` (todo el equipo) o a `~/Applications` (por usuario). No hay instalador, agente de licencias, registro en servidor ni paso de activación.

## Instalación silenciosa / desatendida

### Windows

```powershell
# Por usuario, totalmente silenciosa (ejecutar en el contexto del usuario):
MIA-Toolkit-Setup-<ver>.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER

# Todo el equipo, totalmente silenciosa (ejecutar con privilegios elevados / como SYSTEM):
MIA-Toolkit-Setup-<ver>.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /ALLUSERS /DIR="C:\Program Files\MIA Toolkit"

# Opciones útiles:
#   /SILENT              solo ventana de progreso, en lugar de /VERYSILENT
#   /LOG="C:\path.log"   escribe un registro de instalación
#   /TASKS="desktopicon" crea también un acceso directo en el escritorio (desactivado por defecto)
```

- Una instalación silenciosa **no** abre la aplicación al terminar (el inicio posterior a la instalación se omite en modo silencioso).
- `/CURRENTUSER` + `/VERYSILENT` + `/DIR=` es exactamente lo que ejecuta nuestro proceso de publicación en una máquina de compilación Windows antes de publicar cada versión (vea "Verificación posterior a la instalación"). La línea `/ALLUSERS` aún no la hemos probado en Windows<sup>†</sup>.

### macOS

```bash
# Montar, copiar a /Applications, expulsar:
hdiutil attach MIA-Toolkit-<ver>.dmg -nobrowse -readonly -mountpoint /tmp/mia-dmg
ditto "/tmp/mia-dmg/MIA Toolkit.app" "/Applications/MIA Toolkit.app"
hdiutil detach /tmp/mia-dmg
```

**MDM (Jamf, Intune, Kandji, Mosyle):**

- Despliegue el `.dmg` con el flujo DMG/aplicación de su MDM, o genere un paquete de componente a partir de la aplicación notarizada y distribúyalo: `pkgbuild --component "/tmp/mia-dmg/MIA Toolkit.app" --install-location /Applications MIA-Toolkit-<ver>.pkg`
- Ese `.pkg` **no está firmado** por nosotros (no tenemos un certificado Developer ID *Installer*). Algunos flujos de MDM exigen un paquete firmado (por ejemplo, el tipo de aplicación LOB para macOS de Intune). Fírmelo con el certificado de instalador de su organización, o use la vía DMG / PKG no administrado de su MDM. *(verifíquelo con su MDM)*
- El paquete de la aplicación sigue firmado con nuestro Developer ID y notarizado por Apple, sin importar cómo lo empaquete.
- **Macs sin conexión a internet:** el ticket de notarización está adjunto al `.dmg`, no al `.app` que contiene (comprobado en la v0.1.13 con `xcrun stapler validate`). En una Mac con acceso a internet, Gatekeeper confirma la notarización en línea. Las aplicaciones instaladas por un MDM normalmente no llevan el atributo de cuarentena, así que Gatekeeper no las evalúa al abrirlas por primera vez. Si una Mac totalmente sin conexión muestra un aviso de Gatekeeper para una aplicación copiada a mano desde el DMG, despliéguela mediante el MDM o contáctenos.

## Verificación posterior a la instalación (sin interfaz)

Las versiones posteriores a la v0.1.13 incluyen opciones sin interfaz (en la v0.1.13, `--selftest` solo comprueba la importación de módulos) que no abren ninguna ventana ni hacen conexiones de red:

- `--version` muestra la versión instalada.
- `--selftest` importa todo el paquete, genera un DICOMDIR a partir de un pequeño estudio DICOM sintético en una carpeta temporal, lo elimina, imprime una línea de resultado y termina con `0` (correcto) o `1` (error).

```bash
# macOS
"/Applications/MIA Toolkit.app/Contents/MacOS/mia" --selftest
```

```powershell
# Windows (aplicación con ventana: lea el resultado en el archivo de reporte + el código de salida)
$env:MIA_SELFTEST_REPORT = "$env:TEMP\mia-selftest.txt"
(Start-Process "$env:LOCALAPPDATA\Programs\MIA Toolkit\MIA Toolkit.exe" -ArgumentList --selftest -Wait -PassThru).ExitCode
Get-Content "$env:TEMP\mia-selftest.txt"
```

## Red, proxy y firewall

MIA Toolkit **no hace conexiones de red en segundo plano**. No hay telemetría, analítica, cuenta, sincronización en la nube ni búsqueda automática de actualizaciones. La única conexión de red de la aplicación es **"Buscar actualizaciones", que inicia el usuario** (una sola solicitud HTTPS GET a `https://miatools.tech/version.json`; vea Política de actualizaciones). Cualquier otra conexión saliente corresponde a **enlaces normales en los que el usuario hace clic** (por ejemplo, el sitio web o el correo de soporte), que se abren en el navegador o el cliente de correo predeterminado del usuario, no desde la aplicación.

- **Nada que agregar a listas de permitidos.** No es necesario abrir dominios, puertos ni endpoints para que la aplicación funcione. Permita `miatools.tech` (HTTPS/443) solo si desea que los usuarios puedan buscar actualizaciones.
- La aplicación funciona por completo en una estación de trabajo **aislada / sin conexión a la red**.

## Ubicación de los datos

| Datos | Ubicación |
|---|---|
| Proyecto de trabajo (contenido copiado de los discos, inventario, armado del archivo, registros de sesión) | `~/Documents/MedicalArchive` de forma predeterminada (Windows: `%USERPROFILE%\Documents\MedicalArchive`); el usuario puede elegir otra carpeta |
| Archivo entregado | la memoria USB o carpeta que el usuario elige al final |
| Configuración de la aplicación (solo el idioma de la interfaz) | **Windows:** `%APPDATA%\mia-toolkit\config.json` · **macOS:** `~/Library/Application Support/mia-toolkit/config.json` |
| Archivos del programa | Windows: la carpeta de instalación indicada arriba · macOS: el paquete `.app` |

- La aplicación no escribe en el registro de Windows más allá de la entrada de desinstalación del propio instalador, y no tiene configuración ni archivo de políticas a nivel de equipo.
- La ruta predeterminada del proyecto se construye a partir de la carpeta personal del usuario (`~/Documents`), no de la API de carpetas conocidas "Documentos" de Windows. Si su política redirige Documentos (por ejemplo, con OneDrive Known Folder Move), es posible que la ruta predeterminada no siga la redirección. Los usuarios pueden elegir otra carpeta.<sup>†</sup>
- Los medios de imagen (datos de pacientes) se leen de los discos o carpetas de origen y se escriben solo en el disco local y en la memoria USB de destino. Nunca salen de la estación de trabajo.

## Política de actualizaciones

- **Sin actualización automática.** La aplicación nunca busca ni descarga actualizaciones por sí misma.
- **TI controla las versiones.** Las versiones nuevas se publican en GitHub Releases. TI decide cuándo probar y desplegar una versión, con los mismos comandos de instalación silenciosa de arriba (actualización en el mismo lugar). Puede mantener una versión validada de forma indefinida.

> **Búsqueda de actualizaciones (solo cuando la inicia el usuario):** la opción "Buscar actualizaciones" del menú Ayuda/aplicación hace una sola solicitud HTTPS GET a un archivo de versión estático (`https://miatools.tech/version.json`) **solo cuando un usuario hace clic**. Usa un User-Agent genérico, sin versión, sin parámetros de consulta, sin identificadores y nunca en segundo plano. Solo informa si existe una versión más reciente; nunca descarga ni instala nada. Bloquear ese dominio desactiva la búsqueda sin ningún otro efecto en la aplicación.

## Firma de código y verificación

- **macOS:** firmado (Apple Developer ID) y notarizado desde la v0.1.5. Verifíquelo con `spctl --assess --type execute -vv "/Applications/MIA Toolkit.app"` (resultado esperado: `source=Notarized Developer ID`).
- **Windows:** el instalador **aún no tiene firma de código**. SmartScreen puede mostrar "Editor desconocido": elija Más información → Ejecutar de todas formas, o permítalo mediante la política de sus equipos (por ejemplo, por hash del archivo). Está previsto un certificado Authenticode; actualizaremos esta sección cuando se publiquen instaladores firmados.
- **Sumas de verificación:** el SHA-256 de cada instalador se publica en `https://miatools.tech/version.json`. Las versiones posteriores a la v0.1.13 también incluyen un archivo `SHA256SUMS` (`shasum -a 256 -c SHA256SUMS --ignore-missing`, o `Get-FileHash <file> -Algorithm SHA256` en Windows).
- **Procedencia + SBOM (versiones posteriores a la v0.1.13):** atestaciones de procedencia de compilación de GitHub (`gh attestation verify <file> --repo Fritanga-Collective/mia-toolkit`) y un SBOM CycloneDX por plataforma (`*.cdx.json`).

## Desinstalación

- **Windows:** Configuración → Aplicaciones → MIA Toolkit → Desinstalar, o ejecute en modo silencioso el desinstalador de la carpeta de instalación: `"<install folder>\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART` (ubicación predeterminada por usuario: `%LOCALAPPDATA%\Programs\MIA Toolkit\unins000.exe`). La entrada de desinstalación está en `HKCU\...\Uninstall` (por usuario) o en `HKLM\...\Uninstall` (todos los usuarios), clave `{8F3A1C2E-7B4D-4E9A-9C1F-2D5E6A7B8C90}_is1`.<sup>†</sup>
- **macOS:** elimine `MIA Toolkit.app` de `/Applications` (o de `~/Applications`).
- **Datos residuales:** el desinstalador elimina solo los archivos del programa. El archivo de configuración y cualquier proyecto en `~/Documents/MedicalArchive` permanecen hasta que se borren manualmente. Elimínelos si se requiere un borrado completo (la carpeta del proyecto puede contener imágenes de pacientes).

## Soporte

Nunca necesitamos datos de pacientes. Envíe solo capturas de pantalla o registros (logs) sin datos identificables; nunca estudios, archivos DICOM ni información de salud de pacientes. El soporte es de mejor esfuerzo, por correo a **support@miatools.tech**, con un objetivo de primera respuesta de **2 días hábiles**.
