# Entregar: aviso de versiones selladas antes de VB-1 (front)

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · Sin push. Solo `frontend-desktop/` y esta nota.

Contrato: `ResumenRespuesta.entregable: boolean` (ver `2026-10-21-ola-decisiones-backend-menores.md`, seccion H).

## Cambio (`frontend-desktop/src/paginas/entregar/index.tsx`)
- El tipo local `ResumenEntrega` gana `entregable: boolean` (el cliente no tiene tipos generados de la API; `src/api/tipos.ts` no declara este resumen).
- Con `cadena_integra` y `entregable === false` se muestra `mensaje_de_cadena` tal cual como `InlineNotification` de aviso (`kind="warning"`, `role="status"`) dentro de `#entregar-motivo`, y «Generar paquete» queda deshabilitado con `aria-describedby="entregar-motivo"`.
- Cadena rota: sin cambios (error con `role="alert"`, boton deshabilitado).
- Un 409 al entregar sigue pasando por `AvisoError`, que muestra el `detalle` tal cual.

## Pruebas (`Entregar.test.tsx`, fetch simulado con la forma real del resumen)
Rojo visto: la prueba de version legada fallaba antes del cambio; las otras tres (entregable verdadero, cadena rota, 409) guardan el comportamiento que no debe cambiar y ya pasaban.
