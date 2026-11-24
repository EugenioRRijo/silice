# Auditoría de la ola 1121 (Neon) y veredicto del orquestador

**Fecha:** 2026-11-21 (trabajo de Neon) y 2026-11-22 (veredicto de Claude).
**Base:** `origin/main` `df91d176`. **Rama del PR:** `union/ola-1121-depuracion` (subida como
`feature/ola-1121-depuracion`).

Neon (Antigravity) trabajó por bloques y dejó su informe en `docs/bitacora/auditoria-para-claude-2026-11-21.txt` de la
rama `feature/ui-aistudio`. Este PR trae los bloques 1 a 3 (operación, lógica y front). El bloque 4 (portada y acceso) y
el rediseño van en el PR del front, apilado sobre este.

| # | Bloque y commits de Neon | Qué hace | Veredicto de Claude |
|---|---|---|---|
| O1 | `d27d2811` / `d8abff8a` | Restaurar un respaldo no deja eventos perdidos ni bases a medias | **Confirmado con un defecto (SEG-12):** si no se podía reponer la instalación sobrescrita, no quedaba el aviso de eventos perdidos. Corregido con TDD: `53e22955` (rojo) y `17120691` (verde) |
| O2 | `ec435499` / `5be95700` | Respaldos de la instalación: 503 con la base ocupada y 404 con un zip ilegible | Confirmado |
| O3 | `84004fcc` / `87b520fc` | Cuentas: `BaseOcupada` y 503 | Confirmado |
| O4 | `f76d0155` / `e2d83097` | Argon2 fuera del bloqueo al autenticar; `BEGIN IMMEDIATE` solo al escribir | Confirmado. No enumera cuentas |
| L1 | `11db2738` / `12032651` | Recibir un paquete de revisión de forma atómica; referencias de lista filtradas en SQL | Confirmado. `aplicacion/revision.py` queda en 992 líneas (tope 1000) |
| L2 | `756c60f3` / `6003974b` / `205dbc76` | Montos de 27 o más cifras sin `InvalidOperation` | **Confirmado con un defecto bloqueante:** `mercado.margen` también ampliaba la precisión y una prueba de `main` daba un margen de 47 cifras. Corregido con TDD: `6286ae3b` (rojo) y `e6b55035` (verde); el margen vuelve a 28 cifras y `aplicacion/cifras.py::precision_para` mira la magnitud con `adjusted()` |
| L3 | `fbd23df7` / `e5df9a3b` | JPEG con relleno `0xFF` y marcadores SOF `0xCE`/`0xCF` | Confirmado. Cierra el punto B5 que ESTADO §5 había declarado fuera de alcance |
| F1 | `70b27d9e` / `e203bc44` / `8524f9f4` | Salir de la obra de demostración vuelve a Inicio | Confirmado |
| F2 | `35f87c88` / `33ac1f3a` | La Hoja vacía las ediciones pendientes antes de guardar o poner frente | Confirmado |
| F3 | `18907f71` / `5c70cf04` | Control: EAC del sistema y punto de equilibrio en es-VE | Confirmado |
| F4 | `f26bbe0a` / `caae20a4` | Actualización: precio de un insumo desconocido en es-VE | Confirmado |
| F5 | `1392989c` / `5bf6f6bd` | Versiones refresca aprobaciones y cadena de sellos al crear o restaurar | Confirmado |
| F6 | `9149f30d` / `282da335` | Precios de la empresa avisan el cambio de carpeta al fijar la lista | Confirmado |
| F7 | `4e6133c9` / `c90f0227` | Formatos es-VE en Mercado, tilde en Simulador, avisos en Tramos y AuditarApuPorHoja, fecha del Visor | **Confirmado con una regresión:** cambiar la fecha mientras el libro cargaba dejaba el esqueleto para siempre. Corregido con TDD: `ffb02c22` (rojo) y `8c592a60` (verde) |

## Agregado en la misma unión

- **Guarda de cifras del asistente con punto de miles** (pedido de Eugenio, 2026-11-22: «en nuestro contexto español
  leemos el punto como mil y la coma como decimal, arreglemos eso y volvamos a sellar»). `asistente/validacion.py`
  quita el punto de miles (un dígito seguido de exactamente tres) antes de leer la coma decimal. TDD: `c32d85e0` (rojo)
  y `d3922dc3` (verde). El experimento se re-congeló con acta:
  [2026-11-22-recongelado-experimento-3.md](2026-11-22-recongelado-experimento-3.md) (`660101ea`, `6eb911c4`).

## Comprobación del cierre

- `core/` sin cambios (`scripts/guardia_nucleo.py --base origin/main`).
- Suite completa de Python con `-W error` en la punta de la unión; resultado en la descripción del PR.
