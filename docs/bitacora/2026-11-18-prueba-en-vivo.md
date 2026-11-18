# Prueba en vivo de todas las ventanas (2026-11-18)

Eugenio pidió «probar en vivo simulando completamente el uso de todas las herramientas y ventanas de la app». Se hizo
sobre `main` recién fusionado (`e3419e40`, PR #110 a #122), con datos **ficticios** de demostración en una carpeta de
datos aparte (`SILICE_DATOS`, `SILICE_USUARIO` y `SILICE_RESPALDOS` fuera del repositorio; NORMAS §1). Ningún libro de
la empresa intervino: los archivos subidos salieron de `tests/fixtures/` o se construyeron para la prueba.

## 1. Cómo

- `start.py --puerto 8611` sembró los cinco casos didácticos (`demo`, `of001`, `ti001`, `s1`, `obra_control`).
- **Primer arranque:** el orquestador creó el primer administrador desde la pantalla de bienvenida, con el código de
  instalación, como en una instalación nueva. Entró sin tropiezos.
- **Recorrido:** cuatro agentes lo hicieron en paralelo con Playwright (Chromium), cada uno con su sesión. Rellenaron
  formularios con datos verosímiles, probaron entradas inválidas («1.2.3», negativos, vacíos), guardaron, volvieron a
  abrir y miraron las capturas:

| Frente | Qué cubrió |
|---|---|
| A, el marco | Inicio (Vista general y Pendientes), barra lateral, paleta Ctrl+K, Cuenta completa (cuentas y permisos con una segunda cuenta, empresa, carpetas, sistema, claves de API, respaldos, ayuda y recorrido guiado), Nueva obra, salir y entrar, ventanas estrechas, direcciones inexistentes |
| B, el presupuesto | Resumen, Tablero, la Hoja (partidas, APU, autocompletado, versiones con fuente, Excel y PDF en USD y en Bs), **A.6**, Componer, Archivos y planos (DXF y cómputo CSV), Tramos, Versiones, Aprobaciones (devolver y aprobar), Entregar |
| C, la obra en ejecución | Control (valuaciones, costos, importar, procura, valor ganado, alertas, recuperación), Mercado, Cotizaciones, Actualizar precios, Reajuste, Escenarios, Riesgo |
| D, los espacios | Auditoría (subir un libro construido con errores sembrados, libro de la empresa, **P7**, historial), Precios (listas, catálogo, índices, **C9**), Producción (existencias, receta, mezcla, costos y costo por tonelada, y su propagación a Inicio) |

Después del login no hubo ningún 5xx que se repitiera ni errores de página. Hubo un 503 transitorio en Producir mezcla
que no se reprodujo.

## 2. Lo nuevo de la pila funciona

| Tarea | Resultado en vivo |
|---|---|
| A.6 | Solo el desglose: «Guardar el desglose», sin fuente y sin versión nueva. Desglose más rendimiento: crea la versión. El mismo desglose otra vez: no se ofrece. Dos sesiones: la segunda recibe «Ese desglose ya está guardado.» |
| C9 | Dos insumos con la misma descripción y distinta unidad salen en dos filas, cada una con su unidad, también en el CSV |
| P7 | Cambiar de perfil reinicia las hojas marcadas; el informe nombra las hojas del perfil nuevo |

## 3. Hallazgos que se arreglan (ramas `feature/vivo-*`)

| Frente | Gravedad | Hallazgo | Rama |
|---|---|---|---|
| A | MAYOR | Tras cambiar de carpeta, «Nueva obra» y la barra lateral siguen en la carpeta anterior hasta recargar (cada `useObras()` tenía su propio estado) | `feature/vivo-marco` |
| A | MAYOR | «Ver el catálogo» de un pendiente de otra carpeta abre el catálogo de la carpeta activa | `feature/vivo-marco` |
| A | MAYOR | Nadie puede cambiar su contraseña cuando quiere: el formulario solo aparecía con una clave temporal | `feature/vivo-marco` |
| A | MENOR | Una sección inexistente de una obra que sí existe decía «Esa obra ya no existe»; el error viejo del tope de la IA seguía a la vista; la pista del usuario no decía la regla del servidor | `feature/vivo-marco` |
| D | MAYOR | Una receta aceptaba su propio producto como componente y dejaba el mes sin poder calcular el costo por tonelada | `feature/vivo-produccion` |
| D | MAYOR | En el diálogo de receta, «Código» y «Cantidad por t» se quedaban sin ancho | `feature/vivo-produccion` |
| D | MAYOR | Un movimiento con fecha anterior a un conteo físico cambiaba la existencia posterior al conteo | `feature/vivo-produccion` |
| D | MENOR | El registro de un fallo de la base no traía la traza; jerga interna en el Excel del costo de producción | `feature/vivo-produccion` |
| C | MAYOR | Se aceptaban valuaciones con fecha futura y el «Plan» se medía a esa fecha | `feature/vivo-control` |
| C | MAYOR | Los hallazgos de una valuación no se veían, y con errores el aviso salía en verde | `feature/vivo-control` |
| C | MAYOR | Un costo anotado no se podía ver ni anular | `feature/vivo-control` |
| C | MAYOR | Riesgo no corría en la demo y no decía qué serie faltaba | `feature/vivo-control` |
| C | MENOR | Mensajes con nombres internos o sin tildes; CSV de Escenarios con punto decimal; «Declararlo precio del corte» sin línea base | `feature/vivo-control` |
| B | MAYOR | Una partida compuesta en Componer no tiene precio en una versión que ya existe: sus precios van a la lista de hoy | `feature/vivo-presupuesto` |
| B | MAYOR | Llevar un cómputo CSV a la Hoja perdía el origen y la unidad | `feature/vivo-presupuesto` |
| B | MENOR | Tras «Ese desglose ya está guardado.» el contador seguía en «1 cambio»; el mensaje del desperdicio decía «entre 0 y 100», cuando 100 no vale; fusionar un plano sin filas decía «Se fusionó» | `feature/vivo-presupuesto` |

## 4. Hallazgos que esperan una decisión o que no se arreglan aquí

- **Actualizar los precios de una obra cambia la lista para armar de toda la carpeta y, si la carpeta no tiene moneda
  declarada, también su moneda** (`aplicacion/listas_para_armar.py:204`). La lista importada pasa a ser la vigente de la
  carpeta. Hay que decidir si es lo que se quiere o si la lista de una revaloración debe ser solo de esa obra.
- **No hay PDF de hallazgos en Auditoría:** las rutas `POST /v1/libros/devolucion` y `POST /v1/libros/pdf` no tienen
  botón, aunque el Historial ofrece el filtro «PDF». Hace falta una pantalla nueva.
- **Fechas de Versiones:** la columna «Fecha» muestra la fecha del presupuesto y no cuándo se guardó
  (`aplicacion/hoja.py:2550`). El archivo está congelado: va al próximo recongelado.
- **Cifras con punto decimal que nacen en `core/`:**
  - el estado de una fila en Partidas («(1.89 m3)», `core/verification/reglas.py`);
  - la hoja «Trazabilidad» del Excel (`core/budget/excel.py`);
  - «curva de inversion», sin tilde.

  Las tres necesitan un expediente de `core/`.
- **Inventario sin edición por fila:** Precios de la empresa no edita un precio suelto (se sube otra lista) y Procura solo
  admite «Pedida hoy». Son conductas de diseño; quedan como mejora.
- **Contradicción de dominio en Control:** la reproyección y la recuperación se contradicen en la obra generada
  (termina antes que el plan base y da un costo indirecto negativo). Debe revisarlo alguien del dominio.
- **Segregación de funciones:** quien arma una versión puede también aprobarla. Está permitido por diseño; se anota para
  el tutor.
- **Cosmético:** fechas ISO sueltas, «1 bases», Pareto ordenado al revés, tablas que no caben a 1440 px y claves internas
  («material|1») a la vista. La lista completa está en los informes de cada frente.

## 5. Estado

Los arreglos de §3 se construyen con TDD, uno por frente; cada rama abre su PR. La columna «Rama» dice dónde está cada
uno, y el resultado final queda en [ESTADO](../ESTADO.md).
