# Retiro de Streamlit, F6: de la paridad contra `ui.hoja` a los literales

Fecha: 2026-10-21. Rama `inc/ruta-s2-mig-retiro-streamlit`. Alcance: que ninguna prueba use `ui.hoja`
como oraculo. Regla aplicada (PLAN_RETIRO_STREAMLIT §4 F6): si el literal ya estaba asertado en una
prueba que no importa `ui` se borra la mitad `clasica`; si no, se reescribe con el valor a mano de la
memoria de OF-001 (`tests/fixtures/memorias/of001.md`), de TI-001 (`caso_ti001`), de `control_ob_s2.md`
o de NORMAS.md §4.

Los siete archivos de paridad pasan a `test_aplicacion_hoja_{lectura,apu,espacio,guardado,planos,secciones,versiones}.py`
(commit `git mv` aparte, fc2fc425).

## Tabla de decisiones

| Archivo | Prueba (antes) | Decision | Literal que la sustituye |
|---|---|---|---|
| hoja_lectura | publicas de la copia == publicas de `ui/hoja.py` | BORRADA (comparacion pura) | `TABLA_5_7` (se conserva, cubre cada funcion publica) |
| hoja_lectura | «el Plan C no toca nada congelado» | BORRADA (orden de F6) | guardia de importacion de F1 |
| hoja_lectura | abrir OF-001 / TI-001 (`_borrador_plano` igual) | REESCRITA | total 2703,86; 6 ambientes, 6 fuentes, 21 puntos; FCAS 6,00, bono 5,81, 0,15, 0,10; 27 partidas de TI-001 |
| hoja_lectura | historial, elaborar, parametro cambiado, PE de TI-001 | mitad `clasica` borrada | 2703,86 / 2137,44 / 1530,49 / 56,60 % / Dia 23; 2821,42 / 1763,39 / 62,50 % (ya a mano) |
| hoja_lectura | estado de filas igual en las dos | REESCRITA | 33 filas = 6 + 6 + 21, claves `esp_*` |
| hoja_apu | todas (MODULOS) | mitad `clasica` borrada | CD 10,433785; PU 13,198738025; 18,182085; 13,11927; 37,254885; 13,16809; textos de error (ya a mano) |
| hoja_apu | «las dos dan el mismo APU en las 30 partidas» | REESCRITA | solo cambian cantidad y rendimiento; precios y textos intactos |
| hoja_apu | rendimiento 0 / -5 igual en las dos | REESCRITA | «rendimiento debe ser mayor que cero: N» |
| hoja_apu | candidatos iguales en las dos | REESCRITA | 38 materiales, 6 equipos, 5 oficios; pegamento MAT-002 34,5694 |
| hoja_espacio | tablas/errores/cantidades/completar (MODULOS) | mitad `clasica` borrada | 9,35; 10,8; 4,345 (memoria §2.2-§2.4); textos de error (ya a mano) |
| hoja_espacio | filas de OF-001 (origen: la clasica) | NUEVA prueba | COC-01 (0; 1,5; 2; 1,5; 2,5), FC1, PC1 de la memoria §1 |
| hoja_guardado | guardar/primera version: `volcado` clasica == copia | REESCRITA | 2821,4208; 2703,86; registros; +30 partidas, +6/+6/+2/+21 de espacio, +1 eslabon; TI-001 +27 y ningun `esp_*` |
| hoja_planos | `_iguales` (clasica == copia), fusion | REESCRITA | FILAS_OF001, 33 importados, 6 ambientes/fuentes/21 puntos, circuitos C1 y C2, alto 2,500 |
| hoja_secciones | todas (MODULOS) | mitad `clasica` borrada | 2703,86; 2821,42; 1763,39; 62,50 %; delta 26,3975; 19,798; fila 3 de AF-LLAVE (ya a mano) |
| hoja_versiones | sabor `clasica` | BORRADO (quedan `hoja` y `hoja_versiones`, ambas de aplicacion) | registros de la memoria; 002/003; textos de `core.budget`; cuentas por tabla |
| aplicacion_hoja_plano | informe == `clasica.filas_del_informe` | REESCRITA | 33 importados + 6 pendientes; 16 textos a mano (ya estaban) |
| aplicacion_hoja_vista | filas del espacio, estado, presupuesto, cierre/tablas de 30 APU, plan, curva, auditoria | REESCRITAS | 30 cantidades de of001.md §2.4/§3.4/§4.5; PU recalculado con NORMAS §4 (validado con 10,433785 / 13,198738025 / 2703,86); 33 R8 + R11 de 49 insumos |
| aplicacion_hoja_vista | equilibrio == clasica; `texto_equilibrio` en casos limite | BORRADAS | 1530,49 / 56,60 % / 2137,44 / 2821,42 / 1763,39 y las frases escritas a mano ya asertadas |
| api_hoja | R9 paridad | BORRADA | OF-001, v002 y TI-001 (Dia 6, 28586,7) ya asertados en `test_r9_*` |
| api_hoja | R10, R11, R12, R14 paridad | REESCRITAS | TI-001 50503,27 y parametros; 33 R8 + R11 (49 y 39 insumos); precios 14,3046 / 247,9457 / 34,5694 / 2,1877 / 1,7816 / 10,0000 y UPS 1575,8859; version unica de TI-001 |
| api_hoja | R13 (circular contra `aplicacion.atipicos`) | REESCRITA | texto `NADA_ATIPICO` en OF-001 y TI-001 |
| api_hoja | caracterizacion de R2 | mitad `clasica` borrada | cadena `(False, mensaje)` observada |
| api_hoja_exportar | libro celda por celda contra la clasica (5 casos) | REESCRITA | hojas, filas, totales 2703,86 / 2821,42 / 2703,86 / 50503,27; OB-S2: V-01/V-02, BAC 4000, EV 1200, AC 1280, SPI 0,8, CPI 0,9375, EAC 4266,67; fila de trazabilidad; 3010 dias |
| api_hoja_{conversion_cadena,guardado,edicion,plano,versiones} | `clasica` solo para sembrar o derivar | import a `aplicacion.hoja` | sin cambio de aserciones |

## Mutantes (sobre copia de `aplicacion/hoja.py` fuera del repo)

Resultados en el informe del implementador (16 mutantes; 2 sobrevivieron y se reforzaron en
`test_aplicacion_hoja_secciones.py`, 922b8a29).

## Hallazgos fuera de alcance

- `restaurar` no copia las tablas `esp_*` a la version nueva: es INTENCIONAL (UC-02, herencia por
  `version_origen`). `ui/hoja.py` de la base lo documenta («su espacio es el de la restaurada (no
  copia filas esp_*)»), lo fija la spec `docs/especificaciones/2026-10-19-hoja-react-design.md:359`
  y lo asierta `tests/integration/test_hoja_versiones.py` (lineas 415 y 431).
- Siguen importando `ui.hoja` / `ui.composicion` como SUJETO o para sembrar: pruebas de F7.
