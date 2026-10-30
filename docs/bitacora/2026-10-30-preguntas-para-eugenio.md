# Preguntas para Eugenio (desde el 2026-10-30)

Eugenio está ausente y pidió no detener el trabajo: cada decisión que le tocaba se tomó con criterio de ingeniería,
la opción más prudente y reversible, y queda aquí con lo que se hizo y cómo cambiarlo. Basta con responder «sí» o
corregir la que no le guste.

Hay otra lista, de la sesión que escribió el diseño vial, **solo en local** porque cita datos de la empresa:
`Escritorio/Preguntas para Eugenio (2026-10-30).md` (temas: FCAS por defecto, aporte de pensiones, tipo de riesgo del
IVSS, orden de trabajo, norma de carreteras).

## Plan vial y de agregados (`docs/planes/PLAN_VIAL_AGREGADOS.md`)

| # | Tarea | Pregunta | Lo que se hizo | Cómo cambiarlo |
|---|---|---|---|---|
| 1 | T1 | ¿Se acepta un costo del período con monto 0? | Sí: registrarlo no publica nada; el costo por tonelada (T4) se niega si el total del mes es 0 o todo está anulado | Rechazar el 0 en `CostoDelPeriodo` (una línea y su prueba) |
| 2 | T1 | ¿Quien solo revisa puede ver los costos de producción? | No (lo prudente; todo `/v1/produccion` es de quien arma y del administrador) | Dar a «revisa» lectura con una ruta en un router propio |
| 3 | T1 | ¿De quién es la hora de registro de un costo? | Del servidor, nunca de la pantalla (así nadie fecha un costo a su gusto). Vale para todo registro nuevo del plan | — |
| 4 | T17 | La fuente dice que los aportes patronales se «llevan a días trabajados». ¿Cómo? | `fcas = (días pagados ÷ días trabajados) × (1 + aportes) − 1`: el aporte se paga sobre todo el salario pagado y se reparte en los días trabajados. Caso de Dodi y Salas: 0,7863 sin aportes; 0,8220 con 2 % | Sumar los aportes sin llevarlos a días (daría 0,8063) |
| 5 | T17 | IVSS: ¿qué porcentaje por defecto? | 11 % (el más alto de 9-11 %: subestimar el costo es peor que sobrestimarlo), «a cotejar» según el riesgo de la empresa | Cambiar el valor por defecto en `aplicacion/fcas.py` |
| 6 | T9 | VR3 mide el ligante residual (g/m²), pero la obra declara la dosis en l/m². | Se convierte con densidad 1,0 kg/l y fracción residual 0,60 de la emulsión, ambos «supuesto declarado» y a cotejar con la ficha del producto | Pedir el residual directamente en la capa |
| 7 | T12 | No hay serie pública venezolana del cemento asfáltico. | Se usa el índice de precios de asfalto de EE. UU. (FRED `WPU05810212`) solo por su variación mensual, declarado proxy internacional | Cargar una serie propia cuando la empresa la tenga |
| 9 | T2 | ¿Centro y concepto del costo parten de un valor por defecto? | El centro y la moneda son obligatorios (un centro mal puesto sesga el costo por tonelada: la cantera va a los agregados y la planta a la mezcla); el concepto parte del primero de la lista | Poner un valor por defecto en `FormularioDeCosto.tsx` |
| 10 | T2 | ¿Dónde se entra a «Costos del período»? | En tres sitios: Existencias (lo que abre Empresa › Producción), Inicio de producción y el buscador (Ctrl+K) | Quitar los enlaces que sobren; la pantalla no cambia |
| 11 | T3 | ¿El gasoil propio de la receta descuenta del inventario? | No: la receta lo declara en litros y cuenta en el costo de la mezcla (T4), pero el inventario de agregados es en toneladas | Añadir el combustible como material con inventario propio |
| 12 | T3 | ¿Cuánto pueden desviarse los componentes de la receta de 1 t por t de mezcla? | ±0,02 t (supuesto declarado) hasta que la empresa confirme su dosificación | Cambiar `TOLERANCIA_MASA` en `produccion/fuentes.py` |
| 13 | T4 | ¿Qué producto es «mezcla» al repartir los costos? | El que tiene receta registrada al cierre del mes; lo demás producido es agregado y recibe la cantera. La planta va a las mezclas por tonelada | Marcar el tipo en el material |
| 14 | T4 | Si la lista de precios de la carpeta está en otra moneda que el cálculo, ¿con qué tasa se convierte el cemento asfáltico o el gasoil de la mezcla? | Se toma la lista vigente el último día del mes y se convierte con la tasa BCV del día en que empezó a regir esa lista (la fecha del precio). Efecto con una lista vieja: cálculo en Bs con una lista en USD de cuando la tasa era 50 Bs/USD: 600 USD/t × 50 = 30.000 Bs/t, aunque en el mes del cálculo la tasa sea 200 Bs/USD (600 × 200 = 120.000 Bs/t); el costo de la mezcla sale muy por debajo | Convertir con la tasa del último día del período, o con la de la fecha de cada producción |
| 15 | T4 | La mezcla usa un agregado propio que ese mes no se produjo (salió del inventario). ¿Qué costo lleva? | Ninguno: el cálculo se niega y lo nombra (no se toma el costo de otro mes sin que alguien lo decida) | Tomar el último costo calculado de ese agregado |
| 16 | T4 | Hay costos de cantera pero solo se produjo mezcla, o costos de planta sin mezcla. ¿Qué se hace? | Se niega el cálculo con un mensaje claro; ningún costo queda sin dueño ni se publica un costo cero | Acumular el costo al mes siguiente |
| 17 | T4 | La lista tiene el cemento asfáltico por «ton» (o el gasoil por «lt» o «litro») y la receta por «t» (o «l»). | Se rechaza con un mensaje que nombra las dos unidades: la tabla de alias del núcleo no trata «ton» como «t» ni «lt» o «litro» como «l» | Añadir los alias en `core/contracts/unidades.py` (toca el núcleo), o una tabla de alias propia en `produccion/fuentes.py` con su fuente (duplica un saber que ya es del núcleo) |
| 18 | T5 | ¿El precio publicado al catálogo es el exacto o el redondeado a 2 decimales? | Exacto: se publica el valor del cálculo con todas sus cifras (p. ej. 5,005, no 5,01), trazable al cálculo n.º N por la fuente del precio; el redondeo a dos decimales es solo al presentar. | Redondear con `presentar` (`produccion/costo.py`) al armar el `PrecioPropio` en `publicar_calculo` (`aplicacion/costo_propio.py`) y cambiar `test_se_publica_el_valor_exacto_y_no_el_redondeado` |

## Rediseño del front, F4

| # | Pregunta | Lo que se hará | Cómo cambiarlo |
|---|---|---|---|
| 8 | ¿Aprueba el inventario de F4 y sus 25 bajas (4 dudosas)? | Pendiente: al terminar el plan vial se escribe el plan de F4 con las recomendaciones del inventario; ninguna baja borra código sin dejarlo reversible y anotado aquí | Responder sobre el inventario |
