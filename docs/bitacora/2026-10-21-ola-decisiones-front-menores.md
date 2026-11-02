# Ola de decisiones, frente: hallazgos MENOR del árbitro (2026-10-21)

Rama `inc/ruta-s2-mig-adm-empresa`. Solo `frontend-desktop/`, `PRODUCT.md`, `.claude/agents/silice-frontend.md` y esta bitácora. Datos ficticios.

| MENOR | Qué se hizo |
|---|---|
| 1 | Con letra Grande o Muy grande el nombre de la persona no cabe en la cabecera. El botón «Salir» ahora se llama «Salir (Nombre)» (`aria-label` y `title`; el texto visible sigue siendo «Salir»). El menú en capa trae al pie «Sesión de Nombre» (oculto en menú fijo, visible solo en capa: `.silice-menu__sesion` en `shell.scss`). El selector de proyecto lleva `title` con el nombre completo del elegido (Carbon fija el título solo al montar y al elegir, no cuando el proyecto cambia desde fuera). |
| 3 | Gancho `useSinRegionVacia(selector, conContador)` en `src/comun/`; `CampoTexto` y `AreaTexto` lo usan (antes duplicaban el efecto). |
| 4 | La prueba estática ya no compara por nombre de archivo: permite solo las rutas exactas `src/comun/CampoTexto.tsx` y `src/comun/AreaTexto.tsx`, mira `.ts` y `.tsx`, y el detector `usaCamposDeCarbon` ve alias (`TextArea as Area`), importación del paquete entero o por defecto, rutas profundas, `require` / `import()` y `createElement` / JSX con prefijo. El detector tiene su propia prueba con casos malos y buenos. |
| 5 | Código muerto retirado: token `--silice-ibcs-favorable` (nadie lo leía; se usa `-texto`), regla `.silice-oculto-en-linea` (cero usos en TSX/SCSS) y la línea en blanco inicial de `CampoDeCelda.tsx`. |
| 6 | Sin cambio de conducta. Queda anotado en el comentario del efecto de `DescargaArchivo`: si durante la descarga se hace clic en el cuerpo de la página, el foco ya está en `body` y también se devuelve al botón. |
| 7 | `TamanoLetra` arranca con `tamanoAplicado()`: lo que `aplicarTamanoLetra` dejó en `document.documentElement.dataset.siliceLetra` y, si no hay nada, lo guardado. Con el almacenamiento bloqueado, la instancia del shell (montada al entrar) marca lo que se ve y no vuelve a «Normal». |
| 8 | Excepción a RT-9 anotada en `PRODUCT.md` y `.claude/agents/silice-frontend.md`: «salvo la preferencia de tamaño de letra, que no es un secreto». |

Las pruebas que buscaban el botón por `name: "Salir"` exacto (App, Shell, Cabecera) ahora usan `/^Salir/`.
