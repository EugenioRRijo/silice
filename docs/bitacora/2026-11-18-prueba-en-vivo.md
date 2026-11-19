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

## 3. Hallazgos que se arreglaron (PR #123 a #126)

| Frente | Gravedad | Hallazgo | Rama |
|---|---|---|---|
| A | MAYOR | Tras cambiar de carpeta, «Nueva obra» y la barra lateral siguen en la carpeta anterior hasta recargar (cada `useObras()` tenía su propio estado) | #123 `feature/vivo-marco` |
| A | MAYOR | «Ver el catálogo» de un pendiente de otra carpeta abre el catálogo de la carpeta activa | #123 `feature/vivo-marco` |
| A | MAYOR | Nadie puede cambiar su contraseña cuando quiere: el formulario solo aparecía con una clave temporal | #123 `feature/vivo-marco` |
| A | MENOR | Una sección inexistente de una obra que sí existe decía «Esa obra ya no existe»; el error viejo del tope de la IA seguía a la vista; la pista del usuario no decía la regla del servidor | #123 `feature/vivo-marco` |
| D | MAYOR | Una receta aceptaba su propio producto como componente y dejaba el mes sin poder calcular el costo por tonelada | #124 `feature/vivo-produccion` |
| D | MAYOR | En el diálogo de receta, «Código» y «Cantidad por t» se quedaban sin ancho | #124 `feature/vivo-produccion` |
| D | MAYOR | Un movimiento con fecha anterior a un conteo físico cambiaba la existencia posterior al conteo | #124 `feature/vivo-produccion` |
| D | MENOR | El registro de un fallo de la base no traía la traza; jerga interna en el Excel del costo de producción | #124 `feature/vivo-produccion` |
| C | MAYOR | Se aceptaban valuaciones con fecha futura y el «Plan» se medía a esa fecha | #126 `feature/vivo-control` |
| C | MAYOR | Los hallazgos de una valuación no se veían, y con errores el aviso salía en verde | #126 `feature/vivo-control` |
| C | MAYOR | Un costo anotado no se podía ver ni anular | #126 `feature/vivo-control` |
| C | MAYOR | Riesgo no corría en la demo y no decía qué serie faltaba | #126 `feature/vivo-control` |
| C | MENOR | Mensajes con nombres internos o sin tildes; CSV de Escenarios con punto decimal; «Declararlo precio del corte» sin línea base | #126 `feature/vivo-control` |
| B | MAYOR | Una partida compuesta en Componer no tiene precio en una versión que ya existe: sus precios van a la lista de hoy | #125 `feature/vivo-presupuesto` |
| B | MAYOR | Llevar un cómputo CSV a la Hoja perdía el origen y la unidad | #125 `feature/vivo-presupuesto` |
| B | MENOR | Tras «Ese desglose ya está guardado.» el contador seguía en «1 cambio»; el mensaje del desperdicio decía «entre 0 y 100», cuando 100 no vale; fusionar un plano sin filas decía «Se fusionó» | #125 `feature/vivo-presupuesto` |

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

## 5. Cómo se cerró

- **Arreglos:** un constructor por frente, con TDD: cada defecto tiene su commit con la prueba en rojo antes del verde.
- **Revisión de cada rama:** una revisión de Claude (silice-rev-pruebas) y una segunda opinión de Hydrogen (Gemini, por
  `agy`, solo lectura), arbitradas por Claude. Cada hallazgo se verificó en el código antes de corregirlo.
  - Las dos revisiones encontraron defectos reales en los propios arreglos y se corrigieron en las mismas ramas:
    - un conteo que coincide con lo teórico no cerraba el pasado;
    - `calculo_de_regla` asociaba mal las potencias y podía agotar la memoria;
    - Control no tomaba «hoy» del reloj común;
    - la siembra de la demo no era atómica.
  - Las decisiones van en el acta, DS-59 a DS-66.
- **Re-verificación en vivo:** con el código unido de las cuatro ramas, dos agentes volvieron a reproducir cada hallazgo
  MAYOR en el navegador.
  - Quedaron arreglados todos los que se arreglaban en estas ramas: el corte de la Vista general ya se mide a hoy; solo
    la demo resembrada trajo otra vez valuaciones futuras, por el defecto del `-wal` (punto siguiente).
  - La re-verificación encontró además un defecto anterior: reiniciar la demo (`start.py --reiniciar-demo`) no la
    reiniciaba, porque el `-wal` de la corrida anterior se volvía a aplicar sobre la base nueva.
  - Ese defecto y los menores que salieron (los contadores de pendientes al cambiar de carpeta, el aviso de la receta
    fuera de la vista, la fusión sin filas anunciada como éxito y el diálogo tras «Ese desglose ya está guardado.»)
    también se corrigieron con TDD.

### Declarado, no entra en estos PR

- **Anular un costo incurrido:** necesita un expediente de `core/`, porque `instantanea_control` suma todas las filas y
  `registrar_costo` rechaza los negativos.
- **Pasar una versión a una lista nueva y revalorar una fila pendiente:** necesita `aplicacion/hoja.py`, que está
  congelado. Hoy el aviso dice que hay que quitar la fila y agregarla de nuevo.
- **La hoja «Trazabilidad» del Excel con punto decimal y la fila que dice «sin APU en el catálogo»:** el texto sale de
  `core/` o de `aplicacion/hoja.py`.
- **`BEGIN IMMEDIATE` en las escrituras de `instalacion.db`:** evitaría carreras entre leer el conteo y escribir. Es un
  cambio transversal y va al plan.
- **Producción:** la anulación auditable de conteos y la mezcla de mezclas del mismo mes en orden topológico.
- **Otras mejoras:** una página para cargar las series viales, y que Riesgo de la demo muestre algo (la tasa ficticia
  no mueve una obra en USD).
