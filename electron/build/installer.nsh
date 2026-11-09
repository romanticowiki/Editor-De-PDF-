!include "WordFunc.nsh"

; Política manual de actualización para el instalador asistido de EPDF.
; electron-builder conserva sus protecciones y su flujo probado: este include solo añade
; controles de identidad/versión antes de que se modifique la instalación existente.
!macro customInit
  ; Desde 0.3.1 EPDF se instala siempre por equipo. Si queda una instalación antigua por usuario,
  ; no la eliminamos ni creamos otra copia: el usuario debe desinstalarla explícitamente primero.
  ReadRegStr $R2 HKCU "${INSTALL_REGISTRY_KEY}" "InstallLocation"
  ${If} $R2 != ""
    ${IfNot} ${Silent}
      MessageBox mb_IconExclamation|mb_TopMost|mb_SetForeground "Ya existe una instalación de EPDF solo para este usuario en:$\r$\n$R2$\r$\n$\r$\nDesinstálala desde Aplicaciones instaladas y vuelve a ejecutar este instalador. Tus datos de AppData no se borrarán."
    ${EndIf}
    SetErrorLevel 12
    Quit
  ${EndIf}

  ; El GUID y el appId son los mismos que en 0.3.0, por lo que esta clave identifica la instalación
  ; real en Program Files y permite actualizarla en el mismo directorio y la misma entrada.
  ReadRegStr $R0 HKLM "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion"
  ${If} $R0 != ""
    ${VersionCompare} "${VERSION}" "$R0" $R1

    ; 0 = iguales. No reextraemos cientos de MB ni tocamos accesos directos innecesariamente.
    ${If} $R1 == 0
      ${IfNot} ${Silent}
        MessageBox mb_IconInformation|mb_TopMost|mb_SetForeground "La misma versión de EPDF ($R0) ya está instalada. No es necesario reinstalarla."
      ${EndIf}
      SetErrorLevel 10
      Quit
    ${EndIf}

    ; 2 = la segunda versión (instalada) es más nueva. La recuperación requiere desinstalar primero
    ; desde Windows; así el downgrade nunca ocurre por accidente y AppData se conserva.
    ${If} $R1 == 2
      ${IfNot} ${Silent}
        MessageBox mb_IconStop|mb_TopMost|mb_SetForeground "Tienes EPDF $R0 instalada. Este instalador contiene una versión anterior (${VERSION}) y no puede reemplazarla automáticamente.$\r$\n$\r$\nPara una recuperación manual, desinstala primero la versión actual desde Aplicaciones instaladas y después ejecuta este instalador."
      ${EndIf}
      SetErrorLevel 11
      Quit
    ${EndIf}
  ${EndIf}
!macroend
