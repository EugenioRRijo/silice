# Guía para el tercero que escribe la taxonomía de fallas (Fase 3)

**Para qué sirve.** Para medir de verdad si Sílice encuentra errores, las fallas que se siembran en los libros nuevos
tienen que salir de una lista escrita por **otra persona**, que no conozca las reglas del programa. Si la escribiera
quien hizo las reglas, la medición sería circular: Sílice encontraría justo lo que sus autores ya sabían buscar
([plan no circular](../planes/2026-11-23-plan-auditoria-no-circular.md); [acta del consejo del
2026-11-24](../bitacora/2026-11-24-consejo-auditoria-alertas-mercado.md)). Esta guía acompaña a la plantilla
[taxonomia_fallas_plantilla.toml](taxonomia_fallas_plantilla.toml), que trae el formato y las operaciones.

## Quién la escribe y qué no debe mirar

- **La escribe:** Nicolaz o el tutor, como dice el plan.
- **No la escriben:** Eugenio ni Claude, que hicieron las reglas.
- **No debe abrir antes de terminar:** las reglas de auditoría (`adapters/hoja_empresa/reglas*.py`,
  `core/verification/`), el acta de los huecos de reglas del 2026-11-24 ni los resultados de las mediciones del libro
  de desarrollo. Basta con esta guía, la plantilla y la bibliografía.
- **Sí puede consultar** a un presupuestista sobre qué errores ve en la práctica, siempre que esa persona tampoco
  conozca las reglas.

## Base bibliográfica (verificada en [referencias.md](referencias.md))

- Panko y Halverson (1996) y su revisión, Panko y Aurigemma (2010): errores **cuantitativos** (mecánicos, lógicos y
  de omisión) y **cualitativos**.
- Rajalingham, Chadwick y Knight (2000), Figura 1:
  - errores del usuario **cuantitativos**: **accidentales** (del desarrollador, del que carga datos o del que
    interpreta; cada uno por omisión, alteración o duplicación) y **de razonamiento** (del dominio o de
    implementación);
  - errores **cualitativos**: semánticos y de mantenibilidad.

Cada categoría de la taxonomía cita en su campo `fuente` de cuál de estas obras sale.

## Qué se puede sembrar hoy

El inyector (`scripts/inyector_fallas.py`) tiene **6 operaciones**. La tabla relaciona cada familia de la literatura
con lo que el inyector puede producir. Es **orientativa**: el tercero decide qué categorías incluye, cómo las llama y
cuánto pesa cada una.

| Familia en la literatura | Operaciones del inyector que la producen | Ejemplo en un libro de presupuesto |
|---|---|---|
| Accidental por **alteración** (Rajalingham) / mecánico (Panko) | `valor_fijo`, `signo`, `escala` | Un precio tecleado sobre la fórmula; una cantidad con el signo cambiado; una unidad multiplicada por 1000 |
| Mecánico de **referencia** (Panko) | `referencia_desplazada` | Un BUSCARV o un total que lee la fila de al lado |
| Accidental por **omisión** (Rajalingham) / de omisión (Panko) | `rango_recortado`, `formula_borrada` | Un subtotal que deja fuera el último renglón; una fórmula borrada |
| Accidental por **duplicación** (Rajalingham) | **Ninguna hoy** | Un renglón contado dos veces |
| De **razonamiento** o de dominio (Rajalingham) / lógico (Panko) | **Ninguna hoy** | Un rendimiento absurdo o un factor mal escogido |
| **Cualitativos** (Panko; Rajalingham) | **Ninguna**: no cambian cifras | Una hoja difícil de mantener |

Si una familia que el tercero considera importante **no tiene operación**, se anota igual, pero en una lista aparte del
mismo archivo, `[[sin_operacion]]`, con `id`, `nombre`, `fuente` y `justificacion`. El inyector solo lee
`[[categorias]]` y rechaza una operación que no conoce, así que esa lista no se siembra; se reporta en la tesis como
límite de la medición: Sílice no se midió contra ese tipo de error.

```toml
[[sin_operacion]]
id = "TAX-X1"
nombre = "Renglón contado dos veces"
fuente = "Rajalingham et al. (2000), Figura 1: accidental por duplicación"
justificacion = "El inyector no tiene una operación que duplique renglones."
```

## Cómo se llena

1. Copiar la plantilla a un archivo nuevo, `taxonomia_tercero.toml`, y reemplazar las categorías de ejemplo por las
   propias: `id`, `nombre`, `fuente` (obra y página o figura), `operacion` y `peso`.
2. El `peso` dice qué tan seguido aparece cada error. Puede salir de la frecuencia que informa la literatura o del
   juicio del presupuestista consultado; la regla elegida se escribe en un comentario al principio del archivo.
3. Opcional: `hojas = [...]` para limitar dónde cae una categoría (por ejemplo, solo en los APU).

## Sellado antes de medir

1. El tercero entrega el archivo a Eugenio **antes** de que se abran los libros nuevos.
2. Se calcula su huella: `certutil -hashfile taxonomia_tercero.toml SHA256` en Windows.
3. La huella, la fecha y el nombre de quien la escribió se anotan en una entrada nueva de la bitácora, y se crea la
   etiqueta de git `taxonomia-tercero-sellada`. Desde ese momento el archivo no cambia. Si cambiara, se registra con
   fecha y motivo, y la medición se repite.
4. Recién entonces se siembran las fallas en los libros nuevos, con semilla fija y en el equipo de Eugenio, sin que
   los libros salgan de ahí.

Los criterios de fracaso de la medición ya están sellados en la etiqueta `reglas-congeladas-2026-11-24`. El tercero no
los cambia.
