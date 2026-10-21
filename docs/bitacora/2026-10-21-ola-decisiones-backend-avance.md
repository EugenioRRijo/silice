# Ola de decisiones (backend): D-5, topes del lector de planos, Excel y omitidas, avance

**Fecha:** 2026-10-21 · **Rama:** `inc/ruta-s2-mig-adm-empresa` · **Base:** `f2cd316d`. Sin push. `core/` y `seguridad/` no se tocaron
(los cambios de VB-1 en `core/budget/` de `3aa310d1` son de otro encargo). Venv común con los extras; `PYTHON_KEYRING_BACKEND` nulo.

## Parejas prueba → implementación (rojo visto primero)

| Tarea | Prueba | Implementación | Rojo visto |
|---|---|---|---|
| 1. D-5 afinada | `e37a3295` | `5178b6ce` | 3 de la API fallaban (vieja descartada, vieja no descartada, carrera con la vieja) |
| 2. Topes del lector | `69db26f8` | `30cabd65` | 13 errores de unidad (no existían los topes) y 500 en la API |
| 3. Excel | `f54abe2e` | `43745dc7` | corriendo la prueba contra la versión anterior de `hoja_exportar.py` fallaban todas las de sustitución (libro roto o 422) |
| 4. Sin `skip` | `7c090ba7` | — | rojo = `test_sin_omisiones` (único `skip` del repo, `test_api_control.py:538`) |

Ajustes de las pruebas tras verlas correr, declarados: (a) en el tope de bytes esperaba 422 en una consulta posterior y daba 200; lo que se quería
probar es que la importación anterior sigue vigente, ahora se afirma 200 y no 409 «sin importación»; (b) en el sanador conté 4 sustituciones donde
había 3 (error de aritmética de la prueba). Mutación: cambiar la regla de D-5 por «vigente == abierta» mata el caso `002-002-None`.

## 1. D-5 (guardar versión), regla afinada

`BorradorVivo.vigente_al_abrir` (código de la vigente leída en R2 **antes** de abrir la versión: si alguien guarda en medio, se pedirá
confirmar, que es lo seguro). Una sola regla, `hoja_vista.version_mas_nueva(vivo, vigente)`: la vigente de ahora es otra que la de cuando se abrió,
y el borrador en blanco nunca avisa. La usan el resumen (`version_mas_nueva`) y S1. Abrir a propósito una versión vieja o descartada ya no
pide confirmar si nadie guardó; si alguien guardó, sí, y el texto «Otra persona guardó la versión X después de que usted abrió la Y» es cierto.
El registro vive en la memoria del proceso: tras un reinicio el borrador no existe (404 con el texto de siempre) y no se «rehidrata» con la vigente
de ahora, que taparía un adelantamiento. Un borrador retomado (E10, R3) es el mismo objeto y conserva el código. Pruebas: la carrera de dos
personas que abrieron la vieja a la vez (una 200, la otra 409 con `version_mas_nueva`), la carrera existente, retomado y reinicio.
Contrato actualizado en `2026-10-20-hoja-3d1-contrato-rutas.md`. Sin cambio de esquema: `docs/api.json` no cambia.

## 2. Lector de planos (3e-2): topes

Medido antes: DXF de 13,6 MiB = 26,5 s (unos 2 s por MiB), 40 lecturas agotan el grupo de 40 hilos de las rutas síncronas (17 a 29 min), una caída
deja `silice_planos_*` en `%TEMP%`. Un hilo no se puede matar sin riesgo, así que **el tiempo se acota por tres vías, no con un temporizador**:

1. **Bytes** (`BYTES_MAXIMOS_DE_PLANO`): DXF 8 MiB (unos 15 s) e IFC 20 MiB (el tope de cuerpo de la API). Se juzga después de `rev` y del formato y
   **antes** de crear la carpeta o tomar un cupo: 413 con texto fijo, sin nombres.
2. **Lecturas a la vez** (`LECTURAS_SIMULTANEAS = 2`, semáforo): la de más no espera, 503 de texto fijo con `Retry-After: 10`. P1 y P2 (las que leen).
   El cupo se devuelve ocurra lo que ocurra; probado con el lector que revienta. Con esto el grupo de hilos nunca se agota.
3. **Barrido de `silice_planos_*`**: al arrancar (`on_startup` del router, plazo de 1 h por si hay un proceso hermano recién nacido) y cada 15 min
   desde `leer` (plazo de la vida de un borrador, 8 h). Solo carpetas reales con el prefijo, nunca enlaces ni la carpeta de una importación viva.
   Antes del arranque `leer` no barre (las pruebas no tocan el `%TEMP%` real). Al expirar un borrador ya borraba su carpeta (`al_quitar`).

Alternativas descartadas: temporizador con hilo aparte (el hilo sigue leyendo y conserva el cupo; hace falta bytes en memoria y limpiar si llega tarde);
proceso hijo con `timeout` (mata de verdad, pero rompe la paridad con la copia de la clásica y complica Windows). Límites declarados: el tope por cuenta
no existe (una cuenta puede ocupar los dos cupos); la memoria del lector sigue sin medirse; 8 MiB y 15 s son extrapolaciones de las medidas de arriba.
Textos: `El plano DXF pesa más de 8 MiB, el máximo que Sílice lee en un tiempo razonable…` y `Sílice está leyendo otros planos en este momento…`.
`aplicacion/hoja.py` (copia de la clásica) no cambia; la paridad de planos pasa.

## 3. Excel (E1/X1): U+FFFE, U+FFFF y compañía

Medido con openpyxl: no se pueden leer U+FFFE, U+FFFF ni los sustitutos sueltos U+D800 a U+DFFF (el libro se escribe pero es XML mal formado), y los
controles C0 salvo tabulador, salto y retorno ni se escriben (`IllegalCharacterError`). Sí se leen U+007F, U+0080 a U+009F, U+FDD0, U+FFFD, U+1FFFE,
U+10FFFF y los emoji. **Recomendación aplicada:** en el punto de salida (`hoja_exportar.sanear_para_xlsx`) se recorre una copia de lo que se exporta
(textos, dataclasses congeladas, tuplas, listas, diccionarios) y cada carácter prohibido pasa a **U+FFFD**: conserva la posición y deja a la vista que ahí
había algo. El borrador vivo, la base y la clásica no cambian (la paridad celda por celda con la clásica sigue verde; el saneado es identidad sobre un libro
limpio y devuelve el mismo objeto). Cambia un comportamiento: el control C0 ya no da 422, da 200 con el sustituto; el 422 de texto fijo queda como red
para lo que el recorrido no abra.

Alternativas: eliminar (silencioso, puede pegar palabras); seguir con 422 (el usuario no ve el carácter y no puede quitarlo); validar al escribir en E1
(la mejor higiene de datos, pero cambia la edición respecto de la clásica y bloquearía pegar texto de otros programas; recomendable además, con aval);
escapar a `_xHHHH_` (Excel lo hace, openpyxl no, y U+FFFE no se puede representar). **Decisión para Eugenio:** si además quiere el rechazo en E1.

## 4. Omitidas

El único `skip` del repo estaba en `test_api_control.py:538` y nunca se ejecutaba (en el corte de OB-S2 aplican cuadrillas, horas extra y aceptar; solo
`paralelo` no). La prueba se parametriza por las tres, **afirma** que aplican y otra fija el conjunto exacto. `test_sin_omisiones` pasa. No hay
`xfail` en `tests/` (solo una mención en un docstring).

## 5. Suite completa (venv común con extras, `-W error`, 8 procesos en paralelo)

| Tanda | Resultado |
|---|---|
| unit (3 tandas, sin `test_ui_*`) | 2241 + 2121 + 2562 verdes; 14 + 5 fallos |
| integration (2 tandas) | 807 + 777 verdes |
| `test_ui_*` (3 tandas) | 292 + 349 + 279 verdes; 1 fallo |

Total: 9428 verdes, 20 fallos, todos clasificados:

| Fallo | Clase |
|---|---|
| 5 en `test_deteccion_planos.py`, 9 en `test_planos_auditoria_s3.py`, 2 en `test_dependencias_silice.py`, 2 en `test_licencia_ifc.py` (por `xmlschema`) | entorno: faltan `ifctester` y `xmlschema` (extra `ifc`) en el venv común. No se instalaron (decisión de disco) |
| `test_experimento_congelado_vigente` | a propósito, hasta la ola del descongelado (no se toca) |
| `test_ui_indices.py::test_leer_no_escribe_y_confirmar_es_idempotente` | preexistente que antes no aparecía: con `xlrd` instalado el lector de BCV rechaza el `.xls` de la tasa (`tiene 64 hojas; supera el maximo de 50`, `adapters/bcv/libro.py`). Es un límite de seguridad del adaptador; subirlo o leer solo las hojas necesarias es decisión aparte |

Resueltos respecto de la corrida de 3e-3: los 7 de `test_api_libros` (extra `pdf`), `test_sin_omisiones`, y los que pedían `ezdxf`/`anthropic`.
`ruff check` y `ruff format --check` limpios en lo que toqué; `app.openapi() == docs/api.json`.
