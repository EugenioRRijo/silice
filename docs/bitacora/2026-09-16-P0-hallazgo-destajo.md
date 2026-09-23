# Bitácora — Hallazgo: la modalidad de mano de obra a destajo no cabe en el contrato (Sesión P0.1)

**Fecha:** 2026‑09‑16 · **Rama:** `inc/PLAN-prototipo` (worktree `.claude/worktrees/prototipo`) ·
**Compuerta:** GP0, meta P3 de `scripts/meta_prototipo.py` (exige la decisión **D9** en
`docs/dossier_g0.md`) · **Origen:** RF‑34 (`docs/ERS.md`), que UC‑10 y UC‑11 ya declaran como
requisito esencial · **Spec de diseño:**
`docs/superpowers/specs/2026-09-16-prototipo-composicion-apu-design.md` §3.1 y §5, que adelantó este
mismo análisis; esta bitácora lo verifica contra las fuentes primarias y lo eleva formalmente.

## Objetivo

Determinar si `core/contracts/apu.py` y `core/costing/motor.py` (contratos declarados **estables**
por CLAUDE.md §5) pueden expresar hoy una línea de mano de obra que cobra por unidad de obra
ejecutada — «a destajo» — en vez de por jornal diario. RF‑34 exige que la modalidad se declare por
línea; si el contrato no lo permite, CLAUDE.md §9 ordena **detenerse y documentar el hallazgo**, no
parchear en silencio.

**Resultado:** no se puede. Es un hallazgo real, con respaldo normativo, y no compromete la
hipótesis central. Se eleva como decisión **D9** en `docs/dossier_g0.md`.

## 1. Qué se intentó

Expresar en `ComposicionAPU` una mano de obra que cobra por unidad instalada: por ejemplo, un
obrero de tubería a quien se le paga un precio fijo por cada pieza colocada, en vez de un jornal
diario repartido entre el rendimiento de la partida.

## 2. Por qué no se puede

`LineaManoObra` (`core/contracts/apu.py`, líneas 69‑83) solo modela `descripcion`, `cantidad`
(número de obreros) y `sueldo` (jornal diario); no existe ningún campo que distinga una línea a
destajo de una línea a jornal.

`calcular_apu` (`core/costing/motor.py`) trata **toda** línea de `composicion.mano_obra` por igual,
sin bandera por línea:

```python
# core/costing/motor.py, líneas 35‑39
sueldos_con_fcas = sum(
    (linea.total * (1 + parametros.fcas) for linea in composicion.mano_obra), Decimal(0)
)
bono_total = parametros.bono_alimentacion * composicion.total_obreros
mano_obra = (sueldos_con_fcas + bono_total) / composicion.rendimiento
```

A cada línea se le aplica `(1 + fcas)` (línea 36), se le suma un bono por obrero
(`composicion.total_obreros`, definido en `core/contracts/apu.py` línea 110‑111, que sí es la
suma de `cantidad` de **todas** las líneas de mano de obra) y el bloque completo se divide entre
`composicion.rendimiento` (línea 39). Un destajo de, por ejemplo, 6 USD por metro instalado
recibiría el mismo tratamiento que un jornal: se le multiplicaría por `(1 + FCAS)`, se le sumaría
el bono y se dividiría entre el rendimiento — una cifra que no tiene el significado de un jornal
diario y que el destajo, por definición, no usa como medida (ver la cita del artículo 114 más
abajo).

Tampoco ayuda resolverlo por fuera con otro juego de `ParametrosCosto`: ese contrato
(`core/contracts/apu.py`, líneas 114‑130) se congela **por presupuesto completo**
(`fcas`, `bono_alimentacion`, `administracion`, `utilidad` son los mismos para todas las partidas
que comparten esa instancia), no por partida ni por línea. No hay forma de decirle al motor «a
esta línea de esta partida no le apliques FCAS ni bono ni la dividas entre el rendimiento» sin
tocar `LineaManoObra` o `calcular_apu`.

## 3. Por qué es un hallazgo y no un capricho

El destajo no es una preferencia de interfaz: es una modalidad salarial tipificada por la Ley
Orgánica del Trabajo, los Trabajadores y las Trabajadoras y regulada específicamente para el sector
construcción por su convención colectiva. Verificado en fuente primaria el 2026‑09‑16:

**LOTTT, artículo 114** (`docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt`, líneas 2276‑2283; Gaceta
Oficial N.º 6.076 Extraordinario, 7 de mayo de 2012):

> Salario por unidad de obra, por pieza o a destajo. Artículo 114. Se entenderá que el salario ha
> sido estipulado por unidad de obra, por pieza o a destajo, cuando se toma en cuenta la obra
> realizada por el trabajador o trabajadora, sin usar como medida el tiempo empleado para
> ejecutarla. Cuando el salario se hubiere estipulado por unidad de obra, por pieza o a destajo, la
> base del cálculo no podrá ser inferior a la que correspondería para remunerar por unidad de
> tiempo la misma labor.

El artículo 112 (líneas 2260‑2261 del mismo archivo) lo enumera entre las formas de estipular el
salario: *«El salario se podrá estipular por unidad de tiempo, por unidad de obra, por pieza o a
destajo, por tarea y por comisión»*.

**Cláusula 1 de la Convención Colectiva de Trabajo para la Rama de la Industria de la Construcción**
(`docs/fuentes/CCT_Construccion_GO_6752_Ext_2023-07-06.txt`, líneas 60‑65; Gaceta Oficial N.º 6.752
Extraordinario, 6 de julio de 2023):

> Trabajador o trabajadora por unidad de obra, por pieza o a destajo, por tarea o comisión: es
> aquel que ejecuta su trabajo por metro, por unidad de obra, por pieza o por tarea, cuyo salario o
> pago no podrá ser inferior al previsto en el Tabulador de Oficios y Salarios que forma parte de
> esta Convención. El Trabajador o Trabajadora tendrá derecho a todos los beneficios previstos en
> la presente Convención y en la LOTTT vigente.

El hallazgo, entonces, no es «un informante de campo mencionó el destajo»: es que **el contrato del
sistema no puede expresar una modalidad salarial que la ley tipifica y que la convención colectiva
del sector regula explícitamente**, en un sistema cuya misión declarada (CLAUDE.md §1) es costear
«con la estructura venezolana».

## 4. Por qué la hipótesis central no se ve afectada

CLAUDE.md §1 dice: «El núcleo (`core/`) no cambia **cuando se agrega un dominio**», y la prueba de
esa hipótesis es `git diff --stat core/` vacío al agregar los adaptadores telecom, industrial y
sistemas. Una modalidad salarial no es un dominio: sigue siendo el dominio civil, con la misma
`ComposicionAPU`, el mismo `ParametrosCosto` y la misma fórmula en cascada — solo se amplía qué
puede declarar una línea de mano de obra dentro de esa fórmula.

`scripts/guardia_nucleo.py` (que aplica `estado_nucleo_intacto` de `scripts/meta_alpha.py` al
rango `base..HEAD`) solo falla si un commit toca `core/` **junto con** `adapters/` o `ml/`, o si una
rama que incorpora un dominio nuevo modifica `core/`. El commit que implemente D9 toca únicamente
`core/contracts/apu.py` y `core/costing/motor.py` — ningún adaptador ni módulo de `ml/` en el mismo
commit — así que no dispara la guardia. La regla de CLAUDE.md §9 («si un adaptador parece necesitar
tocar `core/`, deténgase») tampoco aplica en sentido estricto: aquí no es un adaptador el que pide
tocar el núcleo, es el propio dominio civil el que necesita que el núcleo declare algo que hoy no
declara. Aun así, se sigue el mismo procedimiento — documentar antes de tocar un contrato
declarado estable — porque `LineaManoObra` y `calcular_apu` sí están en la lista de contratos
congelados de CLAUDE.md §5.

## 5. Las cuatro opciones evaluadas

1. **Modalidad por línea, dentro del contrato (elegida).** `core/contracts/apu.py` gana un
   `StrEnum ModalidadManoObra` (`JORNAL` / `DESTAJO`) y `LineaManoObra` gana un campo
   `modalidad: ModalidadManoObra = ModalidadManoObra.JORNAL` como **último** campo, con valor por
   defecto. `calcular_apu` separa la suma en dos: las líneas `JORNAL` siguen exactamente la fórmula
   actual (FCAS, bono, división entre rendimiento); las líneas `DESTAJO` entran completas, sin FCAS
   ni bono ni división — porque el destajo, por definición del artículo 114, no usa el tiempo como
   medida. `ComposicionAPU.total_obreros` debe excluir las líneas a destajo: un subcontratista que
   cobra por metro no devenga bono de alimentación como obrero de planilla.

2. **Sueldo sintético armado fuera del núcleo, sin tocar el contrato.** Hay precedente exacto:
   `scripts/seed_telecom.py` (líneas 81‑100) implementa la política «mano de obra = 50 % del
   presupuesto total» de los PDF de ARENAZA despejando, **fuera del motor**, el `sueldo` de una
   `LineaManoObra` sintética de una sola «cuadrilla» para que `cantidad * sueldo * (1 + fcas) más
   bono`, dividido entre el rendimiento, dé exactamente la fracción pedida — sin modificar
   `core/costing/motor.py` ni `core/contracts/apu.py`. La diferencia con este caso: allí se conocía
   el **total** que la línea sintética debía alcanzar (una fracción fija del costo directo impresa
   en el PDF) y se despejaba el sueldo hacia atrás. Aquí no hay total que despejar: el destajo es
   un precio por unidad que el proyectista teclea directamente por línea (RF‑34), y ese precio no
   debe llevar FCAS ni bono ni dividirse entre el rendimiento — no hay ecuación que invertir, hay
   una rama de cálculo distinta que el motor tendría que aplicar de todos modos. La técnica no
   encaja para esta necesidad.

3. **No implementarlo y declararlo limitación del prototipo.** Es la opción más barata, pero deja
   sin cumplir RF‑34 (ya esencial en la ERS, trazado a UC‑10 y UC‑11) y bloquea permanentemente el
   caso de uso que motivó esta sesión: componer una partida con la estructura venezolana real de
   costos incluye el destajo, no es un adorno. Se descarta.

4. **Cuarta categoría, «subcontratos», paralela a materiales/equipos/mano_obra.** En vez de
   modificar `LineaManoObra`, `ComposicionAPU` ganaría un cuarto bloque (p. ej.
   `subcontratos: tuple[LineaSubcontrato, ...]`) que entra completo, como un material. Toca `core/`
   igual que la opción 1, pero con más superficie: un tipo nuevo, un cuarto sumando que
   `core.budget`, el exportador de Excel y las reglas de verificación (R2, R6) tendrían que conocer
   además de materiales/equipos/mano_obra. Y es legalmente impreciso: los artículos 112 y 114 de la
   LOTTT clasifican el destajo como una **forma de estipular el salario**, no como un subcontrato
   civil — modelarlo como «subcontrato» tergiversaría su naturaleza jurídica. Se descarta.

**Recomendación: opción 1.** Es aditiva y retrocompatible — con el valor por defecto
(`ModalidadManoObra.JORNAL`) ninguna composición existente cambia, y la línea base
(`tests/fixtures/apu_linea_base.py`, que esta tarea no toca) reproduce el mismo precio unitario
hasta el último decimal. Queda elevada como decisión **D9** en `docs/dossier_g0.md`, a implementar
en la Fase P1 del sprint del prototipo (meta P4 de `scripts/meta_prototipo.py`).

## Nota sobre la numeración RF‑33 a RF‑35

La Tarea 1 (commit `b3d2666`) dejó abierta la conveniencia de que el tutor confirme la numeración
que deja **RF‑32 vacante** (reservado a UC‑09 del asistente, `PLAN_ASISTENTE.md`) y continúa en
RF‑33 (`docs/ERS.md`, líneas 14‑18 y 395‑398). Esta sesión no la resuelve: es una decisión ya
tomada por la Tarea 1 y **pendiente de aval del tutor**, no un hecho consumado. Se cita aquí porque
RF‑34 (modalidad jornal/destajo por línea) es, junto con el hallazgo de esta bitácora, el
fundamento directo de D9.

## Estado al cierre

Hallazgo documentado; D9 añadida a `docs/dossier_g0.md`; D4 actualizada con la ausencia de fuente
normativa del FCAS; vista lógica de `docs/arquitectura.md` actualizada con `ui/composicion.py` y
`ui/paginas/componer.py`. No se tocó código: solo `docs/`. Verificación de cierre y hash del commit
en `.superpowers/sdd/2026-09-16-prototipo-arenia-fase-p0-p1/task-3-report.md`.
