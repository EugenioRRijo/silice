# F6 · T6 · Flash (2026-11-05): APROBADO, sin hallazgos (Gemini 3.8 Flash High)

> Encargo acotado a 5 puntos de riesgo (permisos del contrato §3, redirecciones, salir sin 401, pruebas cambiadas en el
> verde, rojo real). Solo git. Respuesta literal; guardada por Claude.

**VEREDICTO: APROBADO**

**Verificado por mí:**
- `git diff d30af3d2 dbff51ac -- frontend-desktop/src/marco/EspacioDeCuenta.tsx frontend-desktop/src/marco/espacios.ts frontend-desktop/src/marco/oferta.ts`
- `git show d30af3d2:frontend-desktop/src/marco/ZonaEmpresa.tsx` vs `git show dbff51ac:frontend-desktop/src/marco/ZonaDeCostos.tsx` y `frontend-desktop/src/marco/EspacioDeCuenta.tsx`
- `git diff d30af3d2 dbff51ac -- frontend-desktop/src/marco/Marco.tsx`
- `git diff d30af3d2 dbff51ac -- frontend-desktop/src/sesion frontend-desktop/src/paginas/hoja`
- `git diff e5779b9b dbff51ac -- '*.test.ts' '*.test.tsx'`
- `git diff --stat d30af3d2 e5779b9b` y análisis de fallos en el rojo

---

### Evaluación de los 5 puntos de riesgo

1. **Permisos (contrato §3):**
   - En [`espacios.ts`](file:///frontend-desktop/src/marco/espacios.ts), `SECCIONES_DE_CUENTA` define cada sección con su pantalla base y `ademas: "cambiar_caso"` exclusivamente en `carpetas`. La función [`cuentaUsable`](file:///frontend-desktop/src/marco/espacios.ts#L170-L175) exige tanto la acción adicional como el permiso de la pantalla (`administrar_cuentas`).
   - En [`EspacioDeCuenta.tsx`](file:///frontend-desktop/src/marco/EspacioDeCuenta.tsx), la barra de pestañas solo lista `oferta.cuenta`. Si se introduce una URL manual no autorizada, `puede` es falso y monta `<AvisoSinPermiso />`, sin cargar la pantalla ni exponer datos. Además, [`PaginaAdministracion`](file:///frontend-desktop/src/paginas/administracion/index.tsx#L63-L84) revalida la condición internamente.
   - Comparando con la antigua `ZonaEmpresa.tsx`, el administrador no pierde ninguna pantalla: las de «Costos y producción» pasaron a [`ZonaDeCostos.tsx`](file:///frontend-desktop/src/marco/ZonaDeCostos.tsx); los 7 bloques de Administración más Especialidades (si tiene `activar_modulos`) y Carpetas están repartidos en `cuentas`, `empresa`, `carpetas` y `sistema`; y Ayuda/Acerca de vive en `ayuda`.

2. **Redirecciones:**
   - En [`Marco.tsx`](file:///frontend-desktop/src/marco/Marco.tsx), `ENTRADAS_MOVIDAS` redirige `/empresa/personas` a `/cuenta/cuentas` y `/empresa/ayuda` a `/cuenta/ayuda`, conservando `${search}` y usando `replace`.
   - `RutaVieja` intercepta `/administracion` y `/acerca` asociándolas a su sección de la Cuenta correspondiente, conservando la consulta `${search}`.
   - `/cuenta` redirige con `replace` y `${search}` a `/cuenta/preferencias`.
   - No hay posibilidad de bucle ni de pantalla en blanco: secciones inexistentes redirigen a `/cuenta/preferencias`, y secciones sin permiso renderizan `<AvisoSinPermiso />` encapsulado bajo `<LimiteDeError>` y `<Suspense>`.

3. **Salir sin 401:**
   - En [`useSesion.ts`](file:///frontend-desktop/src/sesion/useSesion.ts), `terminada = true` se activa sincrónicamente antes de fijar el estado en `sin_sesion`.
   - En [`useBorrador.ts`](file:///frontend-desktop/src/paginas/hoja/useBorrador.ts), `descartar()` evalúa `sesionTerminada()` y omite la petición `DELETE /v1/hoja/borradores/{id}` cuando la sesión ya cerró o venció, eliminando el 401 espurio.
   - No hay pérdida de trabajo desatendida: los borradores con cambios pendientes (`cambios > 0`) se preservan en servidor. Cualquier salida o navegación desde el marco hacia otra sección o carpeta sigue interceptada por `alClicAntes` / `irSeguro`, disparando `confirmarSalida` ante formularios o borradores sucios.

4. **Pruebas en el verde:**
   - [`estilosLetra.test.ts`](file:///frontend-desktop/src/estilos/estilosLetra.test.ts): Valida que la barra superior no contiene clases de tamaño de letra y que el enlace de cuenta activo porta el subrayado de acento.
   - [`busqueda.test.ts`](file:///frontend-desktop/src/marco/busqueda.test.ts): Se fortalece agregando prueba explícita de que `Carpetas` no se ofrece sin `cambiar_caso`.
   - [`Administracion.test.tsx`](file:///frontend-desktop/src/paginas/administracion/Administracion.test.tsx): Acota la búsqueda de botones de escritura al bloque `Accesos`, dado que ahora convive apilado con `Cuentas`.
   - [`EspacioDeCuenta.test.tsx`](file:///frontend-desktop/src/marco/EspacioDeCuenta.test.tsx): Parametriza `noOfrecida` en lugar de una cadena fija, asegurando que cada sección no autorizada quede fuera de la barra.
   - [`Marco.test.tsx`](file:///frontend-desktop/src/marco/Marco.test.tsx), [`App.test.tsx`](file:///frontend-desktop/src/App.test.tsx), [`Carpetas.test.tsx`](file:///frontend-desktop/src/shell/carpetas/Carpetas.test.tsx) y [`titulos.test.tsx`](file:///frontend-desktop/src/shell/titulos.test.tsx): Adaptan selectores al retiro de migas, preservando y precisando las aserciones de rol y accesibilidad.
   - Ninguna prueba fue debilitada ni se eliminaron casos sin su debido reemplazo.

5. **Rojo real en e5779b9b:**
   - El commit rojo contiene exclusivamente 17 archivos de pruebas.
   - Las pruebas fallaron genuinamente por ausencia de la implementación (rutas `/cuenta/*` inexistentes en el router, presencia remanente de migas/tamaño en la barra superior, llamada extra a `DELETE` tras salir de sesión), sin fallos por sintaxis rota ni dependencias ajenas.

---

**HALLAZGOS:**
ninguno
