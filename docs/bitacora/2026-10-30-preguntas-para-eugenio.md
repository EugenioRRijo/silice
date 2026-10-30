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

## Rediseño del front, F4

| # | Pregunta | Lo que se hará | Cómo cambiarlo |
|---|---|---|---|
| 8 | ¿Aprueba el inventario de F4 y sus 25 bajas (4 dudosas)? | Pendiente: al terminar el plan vial se escribe el plan de F4 con las recomendaciones del inventario; ninguna baja borra código sin dejarlo reversible y anotado aquí | Responder sobre el inventario |
