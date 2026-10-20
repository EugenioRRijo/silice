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

| T8b alertas del núcleo con tilde | Sonnet | 1 | DEVUELTO (MAYOR: huecos `.+` encadenados, costo cúbico y recursión en el desglose «no aplica») | f5310e8 |
| T8b | Sonnet | 2 | APROBADO (MENOR: el tope de 2 000 caracteres dejaba sin corregir desgloses largos; cerrado y verificado por el orquestador) | d58e251; cierre 5a05957 (rojo 02d563e) |

| T9 calidad de pruebas | Sonnet | 1 | APROBADO (MENOR: piso de AppTest preventivo sin rojo real, declarado) | deec248 (a3b7d19, 680a3fe, cfd92b4) |

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

## Límite conocido de `con_tildes` (T8b, hallazgo 2 del árbitro)

El núcleo arma el desglose de partidas sin motivo con `"; ".join(f"{c}: {m}" ...)` (`core/budget/recuperacion.py`,
intocable). Un código de partida que contenga «; » y «: » es ambiguo con dos ítems; solo se corrige lo que calce con
un motivo del conjunto cerrado (sin composicion de APU, sin rendimiento, sin mano de obra a jornal) a la derecha del
último «: » de cada ítem, y todo lo demás queda intacto. El tope de 2 000 caracteres vale solo para el catálogo de
plantillas por regex; el desglose es lineal y no lo necesita. Sin corregir por ser texto propio de `aplicacion/` y de
la ruta, con claves que usan las pruebas y el front: «Desvio de precio», «Fin (dia habil)», «Retraso (dias)»,
«mas de 7 dias» en `api/rutas/control.py`. El cambio «Mas»→«Más» de dos pruebas quedó en el commit de implementación
`f5310e8` y no en uno de pruebas en rojo (reescribir historia sería peor).

## Deuda anotada (MENOR de los árbitros)

- `fechaDeHoy` está copiada seis veces en el front (`administracion`, `actualizacion`, `indices`, `precios_empresa`,
  `elaborar`, `componer`): unificar en `src/comun`.
- `_contenido` (T5) y `_leer` (T7) hacen casi lo mismo: helper común de subida con tope.
- T7: un `IntegrityError` distinto de la carrera deja el archivo escrito en `datos/paquetes/` sin fila; conviene
  `ruta.unlink(missing_ok=True)` antes de relanzar.
- T6: el 403 por rol de ana y rita solo se prueba en el GET, no en los tres POST de la clave.
- Resto de la ranura de cabecera en `src/visor` y `libros` (sin alimentar); «Periodo» sin tilde en `elaborar` y
  `tablero`; textos sin tilde en módulos previos («clave publica», «contrasena», «Agregar linea»).
- Una cifra con `%` pegado («15.00%») no pasa a es-VE en `formatoEsVe`.

## Pendiente

- Verificación manual pendiente (T9): correr en un equipo con `xlrd` (`uv sync --extra bcv`) las 3 pruebas con
  archivo `.xls` real del BCV: `tests/unit/adapters/test_bcv_libro.py::test_el_libro_real_abre_con_su_huella`,
  `tests/unit/adapters/test_bcv_tasa.py::test_el_archivo_real_da_n_hojas_y_coincide_con_la_transcripcion_a_mano` y
  `tests/unit/adapters/test_bcv_inpc.py::test_el_archivo_real_coincide_con_la_transcripcion_a_mano`. En este equipo no
  hay `xlrd` y fallan con `ModuleNotFoundError` (sin skip a propósito); la lógica del lector queda cubierta con el
  `xlrd` falso. La CI (`uv sync --locked --all-extras`, `ci.yml:105`) debe correrlas.
- Decisión para Eugenio: esas 3 pruebas dejan la suite roja en un equipo local sin el extra `bcv`, por la regla de
  cero omitidas (`scripts/verificar_omitidas.py` rechaza cualquier omisión). La alternativa de fondo es hacer
  obligatorio el extra `bcv` en el entorno de desarrollo.
- El piso de 60 s para `default_timeout` de AppTest es preventivo: en la sesión de T9 no se reprodujo el
  agotamiento de 3 s. Si reaparece, medir con la máquina cargada antes de subirlo más.
- Formato: `ruff format --check .` seguirá listando 41 archivos (5 de `tests/fixtures`, que no se formatearon por
  precaución ante huellas, y 36 ajenos de producción) hasta que alguien decida formatearlos.
