# Plan vial, fase C: riesgo y mejora de la estimación (Tareas 12 a 16)

Rama `inc/vial-agregados` (worktree `.worktrees/s2madm`). La fase B se cerró en 625ee9de. Las decisiones tomadas en
ausencia de Eugenio están en `docs/bitacora/2026-10-30-preguntas-para-eugenio.md`, de la fila 73 en adelante.

| Tarea | Commits | Árbitro |
|---|---|---|
| 12 Series viales y su mapa a insumos | 0effc269, a139bd28 | aprobada r1 |
| 13 Proyección del riesgo | 841e59f3, 0e2ca161 | aprobada r1 |
| 14 Comprobación hacia atrás | fa954b78, 03151cdf | aprobada r1 |
| 15 Informe de mejora de la estimación | d3895216, d2fac136 | aprobada r1 |

## Menores y avisos para las tareas siguientes

- T12 → T13: `historia_mensual` con `hasta` a mitad de mes da un último mes parcial (fila 75). La proyección pasa
  `hasta` a fin de mes.
- T12 → T13: el PPI de asfalto (unidad `indice`) se usa solo por su variación mensual, nunca como precio. Solo lo
  protegen el nombre y la unidad.
- T12 → T13: la muestra no trae la tasa BCV de esos 36 meses. Las pruebas de la proyección siembran una tasa ficticia.
- T13 → T16 (fila 79): falta una función en `aplicacion/` (no en la ruta) que saque del cálculo publicado de la
  Tarea 4 la receta, el costo de planta por tonelada y `precio_de_componente` en la moneda del presupuesto. El cálculo
  guarda sus cifras en su moneda, con la tasa del cierre.
- T13 → T16: `proyectar` compara exacto contra el total del presupuesto. Hay que pasarle un `Presupuesto` recalculado
  con el motor, nunca un total guardado ya redondeado.

- T14 → T16: la comprobación tarda unos 95 s con 2.000 trayectorias por corte (19 cortes, 18 renglones) y unos
  20 s con 500. Medido por el árbitro de la T14. La ruta `…/riesgo/comprobacion` lleva su propio parámetro
  `trayectorias_por_corte`, 500 por defecto. Si pasa de unos 30 s, la pantalla muestra un aviso de espera o la
  calcula en segundo plano. El tiempo medido se anota en la bitácora de la T16.
- Para la tesis: los plazos de los cortes se solapan. La cobertura es un indicador y no una probabilidad con
  intervalo.

- T15 → T16: la pantalla nueva suma su ruta en `shell/rutas.ts` y su fila en `scripts/recorrido_funcional.toml`, con la
  acción `ver_riesgo`. La API de riesgo recibe cifras con punto: el front convierte la coma es-VE (fila 90).
- T16, tiempo medido de la comprobación con 500 trayectorias por corte (el valor por omisión de
  `trayectorias_por_corte`): **14,3 s** con 18 renglones, 43 insumos y 19 cortes, en el proceso, sin la API; 1,0 s
  en la vía ficticia de las pruebas (3 renglones, 7 cortes). Queda por debajo de 30 s: la pantalla avisa de la
  espera y no se calcula en segundo plano (fila 95).

## Menores para el cierre de la fase C

**Menores del cierre hechos** (2026-10-31; lo hecho de cada uno, en «Lo que se hizo», al final).

- Línea del CHANGELOG de las Tareas 12 a 16.
- Fila 81. **Decisión del orquestador** sobre la recomendación del árbitro de la T13: un insumo con el mismo nombre y
  dos precios ya no niega la proyección. Se desdobla en variantes locales («Flete [2]»), sin tocar `core/`, cada una con
  el factor de su serie. Se declara en los supuestos y la contribución se agrupa por el nombre original.
- `proyeccion.py:370`: los meses completos se cuentan solo con las series de insumos y componentes presentes en el
  presupuesto. Hoy, una entrada vieja del mapa baja los meses o niega la proyección.
- Anotados sin cambio:
  - Dos pruebas de la tasa de la T13 entraron con el feat, sin rojo propio. El árbitro las verificó por mutación y
    las dos discriminan.
  - El asunto del commit verde no es el del plan.
  - Rendimiento medido por el árbitro: 18 renglones, 43 insumos y 2.000 trayectorias tardan unos 4 s. Escala lineal.
- T14: en el comentario de `test_un_choque_queda_fuera` hay un salto de línea indebido.
- T14: `tests/fixtures/riesgo_proyeccion.py` expone nombres con guion bajo (`_mes`, `_obra`, `_historia_variable`,
  `_meses`). Hay que exponerlos sin guion bajo.
- T15: `api/rutas/riesgo.py` devuelve `str(Decimal)`; conviene `format(x, "f")` para que nunca salga notación
  exponencial.

## Lo que se hizo de los menores del cierre (2026-10-31)

Cada uno con su prueba en rojo antes del arreglo (o, si la prueba entra en verde, verificada por mutación). Decisiones en
las filas 100 a 105 de las preguntas para Eugenio. `core/` intacto (`git diff --stat c1f436b2 -- core/` vacío).

- **Fila 81, insumos** (36761479 rojo, 00054456): un insumo con la misma descripción y dos precios ya no niega la
  proyección ni la comprobación. Se desdobla en «Flete [2]»… en una copia local de las composiciones, cada variante con
  la serie del original y su precio; se declara en los supuestos y la contribución se agrupa por el nombre original.
  Oráculos a mano: el flete a 20 y a 25 que siguen al gasoil (1.581,25 × F), una variante que no pisa un insumo que ya se
  llama «Flete [2]» y la comprobación con el asfalto a 600 y a 700 (39.468 × 5,1953125 en cada corte). Fila 100.
- **Fila 81, componentes de `mezclas_publicadas`** (22521689 rojo, f16ba0a6): tiene sentido y se hizo. El componente
  con otro precio en el cálculo de otra mezcla pasa a «CA-30 [2]» en esa receta; `mapa_con_variantes` le da la serie del
  original y `supuesto_de_componentes` lo declara en la proyección. Oráculo a mano con dos mezclas (MZ-1 46,75 y MZ-2
  48,2): 1.000 × (32,45 + 62,5 × F) × 1,265. Fila 101.
- **`proyeccion.py ~370`** (d583a916 rojo, 56d71600): `series_presentes` cuenta los meses completos y los cortes solo con
  las series de lo que está en el presupuesto. Pruebas: una entrada vieja del mapa no baja `meses_usados` (36) ni quita
  cortes (4). Fila 102.
- **T14** (7143cb97): el comentario de `test_un_choque_queda_fuera` en una pieza; las fixtures de
  `tests/fixtures/riesgo_proyeccion.py` que importan otras pruebas, sin guion bajo (`mes_desplazado`, `meses_hasta`,
  `obra_ficticia`, `historia_variable`, `apu_ficticio`, `serie_creciente`, `historia_uniforme`, `promedio_compuesto`).
- **T15 y T16, API** (a4520450 rojo, 9ec6c997): `/mejora` también con `format(x, "f")` (una prueba con `1E+1` lo fija) y
  `_RutaRiesgo(RutaSinCache, RutaSinEco)` como `_RutaVial`: el 422 de forma no repite lo enviado (`MENSAJE_FORMA` en la
  obra, `MENSAJE_MEJORA` en `/mejora`, cuya prueba se ajustó). `docs/api.json` regenerado sin cambios. Fila 104.
- **T16, corte de la historia** (02930926): con `hoy` = 2026-05-15 la comprobación da `n_cortes == 2` (octubre y
  noviembre de 2025). Entra en verde; con la mutación `hasta = hoy` da 3. Salto de línea de
  `tests/integration/test_api_riesgo.py:15-16` corregido en el mismo commit.
- **T16, cifras citables** (4a6d0995 rojo, 08dd68c2): salen solo de los valores de `explicar_riesgo`, no de los
  rótulos; cada valor se valida con `cifra_escrita`. «Cubre el 80 por ciento» con el rótulo «P80» se rechaza; nombrar
  «el P80» sigue valiendo y «Bs250,00» se sigue validando. Fila 103.
- **T16, ramas de `mezclas_publicadas`** (22521689): dos precios (ahora se desdobla), el mismo precio (no se desdobla) y
  un cálculo que no guarda la receta del producto (se niega con el n.º del cálculo), con instantáneas escritas a mano.
- **CHANGELOG** (5388a6c9): una línea por cada Tarea de la 12 a la 16.
- **Re-congelado del experimento** (acta 0b477eba, `congelado.json` 62c0b1cf): autorizado por Eugenio el 2026-10-31.
  Cambiaron `aplicacion/hoja.py` y `aplicacion/composicion.py`, fuera del camino del experimento; solo cambia la huella
  `auditor` (`bc34b17e…` → `63930d4b…`). `test_experimento_congelado_vigente` vuelve a verde. Fila 105 (cómo se cumplió
  el árbol limpio). Acta: `docs/bitacora/2026-10-31-recongelado-experimento.md`.

## Árbitro de cierre de la fase C (ronda 1, cabeza c15ceffc): APROBADA

- Integración T12 → T16 y avisos entre tareas: cumplidos. La fila 81 se comprobó con un oráculo propio: sin doble
  conteo y con un «Flete [2]» real separado. Re-congelado: las huellas se reproducen desde los objetos de git y el
  procedimiento es equivalente al de 9832db3a; no hace falta repetirlo.
- MENOR 1, pasado a la Tarea 16b: `aplicacion/riesgo/obra.py:185` (`_codigo_local`) solo mira los códigos ya vistos.
  Un componente real con código «CA-30 [2]» se fundiría con la variante. Hay que reservar antes todos los códigos,
  como hace `_desdoblar`.
- MENOR 2, hecho: el acta dice que `cambios_sin_commit` se sustituyó en tiempo de ejecución y añade la comprobación
  de huellas desde git.

**Fase C cerrada.**

## Suite completa del cierre (sobre c15ceffc, con T17 y T18 unidas)

- Pytest: solo las dos fallas conocidas ajenas a la rama (`test_r11…[TI-001]` por el reloj y `test_huellas_rnf04`); el experimento congelado vuelve a verde. Vitest completo y lint: verdes.
