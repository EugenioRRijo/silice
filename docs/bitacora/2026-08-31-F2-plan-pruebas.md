# Bitácora — Sesión F.2: plan de pruebas (IEEE 829) y evaluación de calidad (ISO/IEC 25010)

**Fecha:** 2026‑08‑31 · **Rama:** `inc/F2-plan-pruebas` (fusionada a `main` con `--no-ff`) ·
**Base:** `02f961a` (cierre del sprint I6) · **Sesión del PLAN:** F.2 (Fase 6), retomada por el
usuario («retomemos la sesión de trabajo»).

## Qué se hizo

1. **[docs/plan_pruebas.md](../plan_pruebas.md)** (IEEE 829): identificador, elementos y
   características a probar/no probar con causa, enfoque (siete prácticas del proyecto), criterios
   de aprobación y suspensión, entorno, **matriz RF‑01…RF‑31 → prueba(s) → resultado** y matriz
   RNF → verificación, más el registro de la ejecución del día. DRY: los enunciados de los RF no
   se copian; cada fila cita la fila homónima de la ERS.
2. **[docs/calidad_iso25010.md](../calidad_iso25010.md)**: evaluación por característica
   (adecuación funcional, fiabilidad, eficiencia, usabilidad, mantenibilidad, portabilidad,
   seguridad, compatibilidad) con las métricas medidas y veredicto por fila; tabla resumen con
   tres estados honestos: cumple / parcial / pendiente.
3. **`scripts/medir_rnf03.py`** (nuevo): evidencia reproducible del RNF‑03. Siembra la línea
   base, la replica hasta 100 partidas de catálogo, elabora y guarda el presupuesto 001, escribe
   una lista con todos los insumos +10 % y cronometra solo `actualizar_precios` (UC‑02 completo
   con auditoría e histórico). Resultado: **1,17 s para 100 partidas y 41 insumos revalorados**
   (umbral 5 s, margen 4×). Mismo patrón que `seed.py`: importa el fixture a propósito (única
   copia de la línea base).
4. **Ejecución registrada** (criterio de cierre del PLAN): `uv run pytest -W error --cov=…` →
   **385 passed en 104,54 s**, 0 advertencias; cobertura de líneas: `core/` **97,99 %**, `ml/`
   99,29 %, `api/` 94,04 %, `adapters/` 88,78 % (total medido 95,99 %). RNF‑06 (≥ 80 %) cumplido.
5. **Mantenimiento de índices** (desactualización detectada al abrir la sesión):
   `docs/README.md` marcaba `resultados_ml.md` y `api.json` como pendientes ya existiendo; la ERS
   marcaba las pruebas de RF‑30/31 como «pendiente (Sesión F.1)» cuando F.1 cerró con UC‑08
   **fuera de alcance** por decisión de su diseño. Ambas cosas quedan corregidas y apuntando al
   plan de pruebas §3.

## Decisiones

| Decisión | Motivo |
|---|---|
| Medir RNF‑03 con un script versionado (`scripts/medir_rnf03.py`) y no con una cifra suelta en el documento | Mismo patrón que `generar_resultados_ml.py`: toda métrica del capítulo de resultados debe poder regenerarse con un comando; una medición irrepetible no es evidencia |
| Replicar los 5 APU reales hasta 100 partidas en vez de inventar composiciones sintéticas | Lo que RNF‑03 mide es volumen de recálculo, no variedad; réplicas de APU auditados mantienen el escenario dentro de datos verificados (DRY sobre el fixture) |
| La evidencia numérica vive en `plan_pruebas.md` §9–§10 y `calidad_iso25010.md` la interpreta | Un solo lugar por hecho (NORMAS.md §2.1); la evaluación cambia de opinión, el registro no |
| RF‑30/31 declarados **pendientes** en el plan, no «cubiertos por diseño» | El plan de pruebas es el documento donde mentir sale más caro: los dos RF sin prueba quedan en fila propia con causa y referencia; los 26 esenciales sí están todos en verde |
| Cobertura medida sobre `core`, `adapters`, `ml` y `api` (no `ui/` ni `scripts/`) | La meta de RNF‑06 es sobre el núcleo; adapters/ml/api se reportan como contexto. La UI de Streamlit se prueba por humo (importación) y medir sus páginas daría un número sin significado |

## Hallazgos

1. **UC‑08 (RF‑30 deseable, RF‑31 opcional) es la única funcionalidad de la ERS sin prueba.**
   Quedó fuera de F.1 por decisión documentada («usa el mecanismo de UC‑02 sin persistir, se
   añade después») y ningún incremento la retomó. Decisión para el cierre: implementarla en una
   sesión corta o degradar RF‑30/31 en la ERS con acuerdo del tutor (G0).
2. **RNF‑03 tiene margen 4×** ya con auditoría completa incluida en el ciclo: el motor puro y la
   recomposición por lista son el costo dominante y escalan lineal (1,17 s ≈ 12 ms por partida).
3. El hallazgo recurrente de I2/I6 sigue vigente y ahora consta también en el plan de pruebas:
   la persistencia de RF‑16 espera un flujo de creación de partidas que no existe (para G0).

## Estado al cierre

```
uv run pytest -W error --cov=core --cov=adapters --cov=ml --cov=api
                                     -> 385 passed en 104,54 s; core 97,99 %
uv run ruff check .                  -> limpio
uv run python scripts/medir_rnf03.py -> 100 partidas en 1,17 s: RNF-03 CUMPLE
git diff --stat core/ (en la rama)   -> vacio: la sesion no toco el nucleo
```

## Próximos pasos

1. **Sesión F.3** (última del PLAN): `docs/manual_usuario.md` y `docs/manual_tecnico.md`, con la
   guía para escribir un adaptador nuevo (el aporte extensible del trabajo).
2. Decidir UC‑08 (hallazgo 1) antes o durante G0 con el tutor.
3. Pendientes externos sin cambio: G0 (revisión del tutor), G1 contra un IFC real, RNF‑04
   (juicio de expertos) y RNF‑07 en Linux.
