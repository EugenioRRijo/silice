# Migración final, bloque B (T4 a T8): registro de ciclos

Rama `inc/ruta-s2-mig-final-b`, árbol `.worktrees/s2m4`, desde `inc/ruta-s2-mig` (b2d1c2d). Orquesta `tesis-b9`; el
árbitro de cada entrega es un subagente nuevo que juzga con `docs/planes/MANUAL_ARBITRO.md`. Manual de los
implementadores: `docs/planes/MANUAL_SUBAGENTES_FINAL_B.md`. Sin push ni PR; la integra `tesis-8d`.

## Ciclos

| Tarea | Implementador | Ronda | Veredicto | SHA de la cabeza |
|---|---|---|---|---|
| T8 Reajuste y Control | Sonnet | 1 | APROBADO | f177106 (rojo ebf17b0) |
| T4 variaciones atípicas | Opus | 1 | DEVUELTO (MAYOR: el porcentaje exacto no estaba a la vista) | 14eb075 |
| T4 | Opus | 2 | APROBADO | 62ac906 (rojo b05b4e3) |
| T5 Empresas registradas | Opus | 1 | APROBADO | 6586683 |
| T6 Asistente de IA | Opus | 1 | APROBADO | edfb357 |
| T7 Revisar un paquete | Opus | 1 | DEVUELTO (2 MAYOR: 500 al dictaminar un alterado; desvíos sin es-VE) | 378f0ba |
| T7 | Opus | 2 | APROBADO | b2e97cb (rojo a46a815) |

Compartidos aplicados por el orquestador: `30819c7` (routers, tabla de acceso, CHANGELOG, api.json) y `b49ccf0`
(api.json tras la ronda 1 de T7). Verificación tras `30819c7`: 268 pruebas verdes de acceso, OpenAPI, rutas del front y
arquitectura.

## Incidente

El implementador de T8 ejecutó `git checkout -q HEAD -- .` en el árbol compartido y descartó cambios sin commitear de
archivos versionados. Los implementadores de T4, T5, T6 y T7 comprobaron sus archivos y ninguno perdió trabajo (sus
cambios ya estaban en commits o en archivos sin seguimiento). Regla recordada: nada de `checkout`, `reset`, `stash`
ni `clean` en el árbol compartido.

## Decisiones tomadas por el orquestador (ratificables por Eugenio)

1. Un paquete «alterado» no admite dictamen (`SIN_DICTAMEN`): es lo conservador y reversible.
2. En la tabla de variaciones atípicas, el ícono de «Advertencia» usa el token `--silice-atipico` (morado), con texto
   e ícono: DESIGN.md asigna ese color a los atípicos (RF-100).

## Decisiones para Eugenio

- ¿Se pone freno de intentos a reactivar la clave de IA? Hoy no lo tiene, igual que en la clásica; su respaldo usa
  Argon2, que ya es lento.
- `seguridad/json_estricto.py` repite el nombre completo de una clave duplicada en su mensaje, sin tope de longitud
  (módulo compartido, fuera de T5).
- El Excel externo de «Revisar un paquete» pasa ahora por la guardia de `.xlsx`; la clásica no lo hacía.
- La clásica sigue ofreciendo el formulario de dictamen para un paquete alterado y responde con `st.error` al enviarlo.

## Deuda anotada (MENOR de los árbitros)

- `fechaDeHoy` está copiada seis veces en el front (`administracion`, `actualizacion`, `indices`, `precios_empresa`,
  `elaborar`, `componer`): unificar en `src/comun`.
- `_contenido` (T5) y `_leer` (T7) hacen casi lo mismo: helper común de subida con tope.
- T7: un `IntegrityError` distinto de la carrera deja el archivo escrito en `datos/paquetes/` sin fila; conviene
  `ruta.unlink(missing_ok=True)` antes de relanzar.
- T6: el 403 por rol de ana y rita solo se prueba en el GET, no en los tres POST de la clave.
- Resto de la ranura de cabecera en `src/visor` y `libros` (sin alimentar); «Periodo» sin tilde en `elaborar` y
  `tablero`; textos sin tilde en módulos previos («clave publica», «contrasena», «Agregar linea»).
- Alertas del núcleo sin tilde: salen de `core/budget/valor_ganado.py` (líneas 774 a 860) y llegan por
  `aplicacion/control.py`; la corrección, sin tocar `core/`, va en esa capa. Sin dueño todavía.
- Una cifra con `%` pegado («15.00%») no pasa a es-VE en `formatoEsVe`.

## Pendiente

T9 (calidad de pruebas) espera el aviso de `tesis-8d` de que su T1 (arenera) está integrada.
