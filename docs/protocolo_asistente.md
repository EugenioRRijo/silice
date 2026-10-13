# Protocolo del experimento del asistente de IA (OE-H2)

Estado: **BORRADOR** hasta el congelado de la tarea 20 (S4 §9.1). Se versiona aquí; las huellas del
banco, del protocolo y del auditor quedan en `asistente/experimento/congelado.json` cuando se
congela.
Los datos son construidos y declarados (NORMAS §1): las tareas no representan obras reales.

## 1. Pregunta

¿Cuántos errores de las propuestas de cada modelo detecta el auditor, con cuántas falsas alarmas, y
cuántas propuestas son válidas? Misma tarea, mismas herramientas, mismas instrucciones y mismo
validador
para los dos modelos; solo cambia el proveedor.

## 2. Banco de tareas

- Fichas: `tests/fixtures/asistente/tareas/*.json` (4 de desarrollo, 12 de evaluación; 3 de las 12
  con
  errores sembrados). Las escribe `scripts/escribir_banco_asistente.py` y no se tocan después de la
  revisión de la segunda persona.
- **Huella del banco** (SHA-256 de nombres y bytes con saltos LF):
  `29446b12ebf646d89ef9ccae3b597989e8787757e7fdf9a66024ff098aa3a0b2`
- Segunda persona que revisó pedido y referencia: ______ (fecha ______).
- Respuestas preparadas: cada una lleva palabras clave; una pregunta del modelo (sin tildes ni
  mayúsculas) recibe la primera respuesta cuyas palabras aparecen todas; si ninguna, «no lo se». El
  experimentador no elige ni redacta durante las corridas.

## 3. Taxonomía y emparejamiento (reglas cerradas, S4 §9.5)

E1 partida equivocada · E2 unidad · E3 dimensión o posición fuera de 0,001 m · E4 punto en ambiente
equivocado o fuera de todo ambiente · E5 fuente o circuito equivocados · E6 elemento omitido · E7
elemento
sobrante o duplicado · E8 dato sembrado del pedido copiado sin objeción.

El comparador **nunca empareja por id**: clase, especialidad y tipo iguales; distancia (esquinas
para
ambientes, 3D para fuentes y puntos); vecino más cercano con tolerancia de 0,10 m (empates por
coordenadas, nunca por id); tareas de posición libre se trasladan por la esquina de su primer
ambiente.
Un elemento desplazado más de 0,10 m cuenta como omitido más sobrante (E6 + E7). E8 es el valor
sembrado
que **queda en el borrador**; no se cuenta además como E3, ni su punto «fuera» como E4.

## 4. Qué regla debería detectar cada tipo (hipótesis, declarada antes de medir)

- **E1**. Regla que debería detectarlo: ninguna; Nota: «mentira consistente» con unidad compatible
  (horizonte H-D9): no detectable por diseño
- **E2**. Regla que debería detectarlo: R3; Nota: unidad incompatible con la del APU
- **E3**. Regla que debería detectarlo: R9, R10; Nota: solo si el desplazamiento rompe la geometría
- **E4**. Regla que debería detectarlo: R9; Nota: punto fuera de su ambiente
- **E5**. Regla que debería detectarlo: R10; Nota: circuito o fuente equivocados
- **E6**. Regla que debería detectarlo: ninguna; Nota: sin fila que citar: no detectable por diseño
- **E7**. Regla que debería detectarlo: R10, R15; Nota: duplicado que excede el límite del circuito
  (R10) o dos puntos a menos de 0,001 m (R15)
- **E8**. Regla que debería detectarlo: R9; Nota: valor imposible copiado del pedido


Las hipótesis se revisan **antes** del congelado y no después. Los tipos sin regla se informan
aparte,
con su número.

## 5. Condiciones y corridas

- A (principal): sin retroalimentación; `pedir_informe_auditoria` desactivada. B (secundaria):
  activada.
  Si el tiempo o el costo aprietan, B se cae primero.
- 12 tareas × 2 modelos × 2 condiciones × 3 repeticiones = 144 corridas (72 con Claude). Aceptación
  automática de toda propuesta válida (mide al modelo, no a la persona). Respaldo del servidor
  desactivado. Registro de modelo, esfuerzo, versión del SDK, de Ollama y del modelo local.
- Reglas del auditor: las de `protocolo.json::reglas_del_experimento`: R1-R10 y **R15** (maestro
  §3.3, columna «Experimento de S4»; S4 §9.1: las de R8-R16 que apliquen al borrador). Las 16
  referencias del banco dan cero hallazgos de R15. R12 (cuando exista) a la fecha **fija**
  `fecha_de_evaluacion_r12`. La reevaluación es en memoria. El congelado cubre los archivos de esas
  reglas, sus umbrales (`LIMITE_*`) y el instrumento de medición (banco, comparador, métricas,
  mutaciones y corrida).

## 6. Métricas y umbrales (se congelan con el protocolo)

Detección del auditor (errores detectables con un hallazgo no esperado que cite su fila ÷ errores
detectables, total y por tipo, con bootstrap agrupado por tarea: 10 000 réplicas, percentiles 2,5 y
97,5,
semilla fija); falsas alarmas; errores que escapan; propuestas válidas al primer intento; guardas
activadas; exhaustividad; costo y tiempo. Los hallazgos que da la propia referencia no cuentan.
Umbrales
propuestos: detección ≥ 80 %, falsas alarmas ≤ 10 %, 100 % de los números finales calculados por el
sistema. La comparación entre modelos es descriptiva (12 tareas no dan significancia).

## 7. Medición controlada con mutaciones

Sembrador determinista con semilla fija: `n = 24` mutantes por tipo, repartidos por turno entre las
tareas de evaluación donde el tipo aplica (RP9-7: E1 y E2 solo en las 2 mixtas; E8 solo donde la
ficha
declara un sembrado construible). Los mutantes repetidos se descartan (el auditor es determinista:
un duplicado no es un ensayo independiente) y se informa el **n efectivo** por tipo; Wilson se calcula
con ese n. Intervalo de Wilson al 95 % por tipo. Se corre **después** del congelado.

## 8. Costo y aprobación

Estimación por tarea con la tarifa de `asistente/precios_ia.json`. El piloto (solo tareas de
desarrollo,
≈ 20 USD) y la corrida de evaluación (≈ 87 USD de cota) necesitan la **aprobación escrita de
Eugenio**
con la cifra medida.

## 9. Orden

1. Banco congelado con huella (S4.0). 2. Piloto con tareas de desarrollo: fija el esfuerzo de
   Claude, mide
el costo y prueba el comparador. 3. **Congelado** del protocolo y de la huella del auditor, DESPUÉS
del
piloto y ANTES de la primera corrida de evaluación. 4. Corrida de evaluación y medición controlada.
5. `docs/resultados_asistente.md`, generado por el script.

## 10. Amenazas a la validez

Quien construye las tareas conoce el sistema; 12 tareas y 3 con errores sembrados dan intervalos
anchos;
la aceptación automática es distinta del uso real; los modelos no son deterministas (por eso 3
repeticiones); un hallazgo de R8 por un supuesto declarado cuenta como detección aunque el supuesto
sea
inocuo. Cada una se declara en la tesis.
