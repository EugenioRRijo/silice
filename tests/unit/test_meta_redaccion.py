"""Pruebas de `scripts/meta_redaccion.py` (Sprint R1: capitulos I y II).

Funciones puras sobre texto sintetico: ninguna prueba lee el disco ni ejecuta procesos. Los
casos negativos imitan los errores que un tutor marcaria: una seccion que falta, OE7 en la
variante equivocada, primera persona, una cita sin referencia, una referencia pendiente sin marca,
un caso didactico presentado como real y "gemelo digital" fuera de su delimitacion.
"""

import pytest

from scripts import meta_redaccion as meta
from scripts.meta_alpha import Estado

CAPITULO_1 = """# Capítulo I — El problema

| Capítulo | Estado | Última revisión |
|---|---|---|
| I | borrador completo | 2026-09-15 |

## 1.1 Planteamiento del problema

Según Sacks et al. (2020) la trazabilidad falla [verificación pendiente].

## 1.2 Formulación del problema

¿Cómo automatizar la cadena de trazabilidad?

## 1.3 Objetivos de la investigación

### Variante A — con extensibilidad multidominio

OE1 Diagnosticar. OE7 Validar la extensibilidad del modelo a otros dominios.

### Variante B — extensibilidad como resultado complementario

OE1 Diagnosticar. OE6 Evaluar la exactitud.

## 1.4 Justificación

Se justifica por la literatura (Elmousalami, 2020).

## 1.5 Alcance y delimitación

### Lo que la investigación no comprende

- Gemelo digital en sentido estricto.
- La validación con presupuestos reales queda como limitación.
"""

CAPITULO_2 = """# Capítulo II — Marco teórico

| Capítulo | Estado | Última revisión |
|---|---|---|
| II | borrador completo | 2026-09-15 |

## 2.1 Antecedentes

### 2.1.1 Ámbito internacional

Elmousalami (2020) comparó veinte técnicas.

### 2.1.2 Ámbito latinoamericano

Trabajos regionales.

### 2.1.3 Ámbito nacional

Trabajos venezolanos.

## 2.2 Bases teóricas

### 2.2.3 BIM‑5D, sombra digital y gemelo digital

Un gemelo digital exige realimentación bidireccional.

## 2.3 Bases normativas

COVENIN.

## 2.4 Definición de términos

Gemelo digital: modelo con lazo cerrado.
"""

REFERENCIAS = """# Referencias

## Aprendizaje automático

### Elmousalami (2020)

Elmousalami, H. H. (2020). Artificial intelligence...

- **Estado:** verificada

### Sacks et al. (2020)

Sacks, R., et al. (2020). Construction with digital twin information systems.

- **Estado:** pendiente

### Tayefeh Hashemi et al. (2020)

Tayefeh Hashemi, S., et al. (2020). Cost estimation and prediction.

- **Estado:** verificada
"""


# --- Capitulos ------------------------------------------------------------------------------


def test_capitulo_1_completo_ok():
    estado, evidencia = meta.evaluar_capitulo_1(CAPITULO_1)

    assert estado is Estado.OK, evidencia


def test_capitulo_1_sin_justificacion_falla_nombrandola():
    sin_justificacion = CAPITULO_1.replace("## 1.4 Justificación", "## 1.4 Otra cosa")

    estado, evidencia = meta.evaluar_capitulo_1(sin_justificacion)

    assert estado is Estado.FALLA
    assert "justificacion" in evidencia


def test_capitulo_sin_tabla_de_estado_falla():
    sin_tabla = CAPITULO_1.replace("| Capítulo | Estado | Última revisión |", "| Otra | tabla |")

    assert meta.evaluar_capitulo_1(sin_tabla)[0] is Estado.FALLA


def test_capitulo_ausente_pendiente():
    assert meta.evaluar_capitulo_1(None)[0] is Estado.PENDIENTE
    assert meta.evaluar_capitulo_2(None)[0] is Estado.PENDIENTE


def test_objetivos_en_dos_variantes_ok():
    estado, evidencia = meta.evaluar_objetivos(CAPITULO_1)

    assert estado is Estado.OK, evidencia


def test_oe7_en_la_variante_b_falla():
    oe7_en_b = CAPITULO_1.replace("OE6 Evaluar la exactitud.", "OE7 Validar la extensibilidad.")

    estado, evidencia = meta.evaluar_objetivos(oe7_en_b)

    assert estado is Estado.FALLA
    assert "Variante B" in evidencia


def test_objetivos_sin_variante_b_falla():
    sin_b = CAPITULO_1.replace("### Variante B", "### Otra variante")

    assert meta.evaluar_objetivos(sin_b)[0] is Estado.FALLA


def test_capitulo_2_completo_ok():
    estado, evidencia = meta.evaluar_capitulo_2(CAPITULO_2)

    assert estado is Estado.OK, evidencia


def test_capitulo_2_sin_ambito_nacional_falla_nombrandolo():
    sin_nacional = CAPITULO_2.replace("### 2.1.3 Ámbito nacional", "### 2.1.3 Otro ámbito")

    estado, evidencia = meta.evaluar_capitulo_2(sin_nacional)

    assert estado is Estado.FALLA
    assert "nacional" in evidencia


# --- Redaccion ------------------------------------------------------------------------------


def test_voz_impersonal_ok():
    assert meta.evaluar_primera_persona({"cap1": CAPITULO_1, "cap2": CAPITULO_2})[0] is Estado.OK


def test_primera_persona_falla_citando_capitulo_y_palabra():
    con_primera = CAPITULO_1 + "\nEn nuestro caso realizamos la auditoría.\n"

    estado, evidencia = meta.evaluar_primera_persona({"cap1": con_primera})

    assert estado is Estado.FALLA
    assert "cap1" in evidencia and "nuestro" in evidencia and "realizamos" in evidencia


def test_primera_persona_con_verbos_fuera_de_una_lista_cerrada():
    """Una prueba sobre el capitulo real mostro que "empleamos" pasaba: la deteccion no puede
    depender de una lista de verbos. Los sustantivos y adjetivos terminados igual no cuentan.
    """
    con_verbos = "Para examinar el mecanismo empleamos un caso y decidimos auditarlo."
    sin_verbos = (
        "La tubería tiene cuatro tramos; los últimos préstamos y los mínimos extremos no cambian."
    )

    estado, evidencia = meta.evaluar_primera_persona({"cap1": con_verbos})

    assert estado is Estado.FALLA
    assert "empleamos" in evidencia and "decidimos" in evidencia
    assert meta.evaluar_primera_persona({"cap1": sin_verbos})[0] is Estado.OK


def test_sin_capitulos_que_revisar_pendiente():
    assert meta.evaluar_primera_persona({})[0] is Estado.PENDIENTE


# --- Citas y referencias --------------------------------------------------------------------


def test_citas_narrativas_y_parenteticas_con_referencia_ok():
    texto = (
        "Según Sacks et al. (2020) hay lazo cerrado. "
        "Otros lo confirman (Elmousalami, 2020; Tayefeh Hashemi et al., 2020)."
    )

    estado, evidencia = meta.evaluar_citas({"cap": texto}, REFERENCIAS)

    assert estado is Estado.OK, evidencia


def test_cita_sin_referencia_falla_nombrandola():
    textos = {"cap": "Los listados de MaPreX (2026) muestran."}

    estado, evidencia = meta.evaluar_citas(textos, REFERENCIAS)

    assert estado is Estado.FALLA
    assert "MaPreX (2026)" in evidencia


def test_cita_con_anio_distinto_no_encuentra_referencia():
    textos = {"cap": "Elmousalami (2019) reporta."}

    assert meta.evaluar_citas(textos, REFERENCIAS)[0] is Estado.FALLA


def test_autores_con_guion_encuentran_su_referencia():
    """El apellido de la referencia se separa por espacios y guiones, igual que el de la cita."""
    referencias = (
        REFERENCIAS
        + "\n### IP-3 (s.f.)\n\n- **Estado:** verificada\n"
        + "\n### Rozo-Martínez y Tumay-Gamba (2024)\n\n- **Estado:** verificada\n"
    )
    texto = "Lo documentan Rozo-Martínez y Tumay-Gamba (2024) y el fabricante (IP-3, s.f.)."

    estado, evidencia = meta.evaluar_citas({"cap": texto}, referencias)

    assert estado is Estado.OK, evidencia


def test_autor_corporativo_con_abreviatura_encuentra_su_referencia():
    """APA 7: la primera cita de un autor corporativo introduce la abreviatura entre corchetes.
    Sobre las referencias reales, R5 rechazaba "(Comisión Venezolana de Normas Industriales
    [COVENIN], 1999)" porque el corchete quedaba pegado a la palabra.
    """
    referencias = REFERENCIAS + "\n### COVENIN (1999)\n\n- **Estado:** verificada\n"
    texto = (
        "La norma (Comisión Venezolana de Normas Industriales [COVENIN], 1999) fija la unidad; "
        "la misma norma (COVENIN, 1999) la codifica."
    )

    estado, evidencia = meta.evaluar_citas({"cap": texto}, referencias)

    assert estado is Estado.OK, evidencia


def test_la_cita_no_arrastra_texto_de_la_linea_anterior():
    """Sobre el capitulo II real, la evidencia salio como 'BIM\\n\\nMa et al. (2011)': la
    secuencia de nombres cruzaba saltos de linea y tomaba la ultima palabra del subtitulo.
    """
    texto = "#### Costos desde modelos BIM\n\nSacks et al. (2020) formularon el concepto."

    (cita,) = meta.citas_de(texto)

    assert cita.texto == "Sacks et al. (2020)"


def test_referencia_pendiente_sin_marca_falla():
    textos = {"cap": "Según Sacks et al. (2020) hay lazo."}

    estado, evidencia = meta.evaluar_pendientes(textos, REFERENCIAS)

    assert estado is Estado.FALLA
    assert "Sacks" in evidencia


def test_referencia_pendiente_con_marca_ok():
    texto = "Según Sacks et al. (2020) [verificación pendiente] hay lazo."

    assert meta.evaluar_pendientes({"cap": texto}, REFERENCIAS)[0] is Estado.OK


# --- Honestidad de datos y terminologia ------------------------------------------------------


def test_caso_presentado_como_real_falla():
    texto = "Se auditó un presupuesto real elaborado por el procedimiento tradicional."

    estado, evidencia = meta.evaluar_datos_reales({"cap1": texto})

    assert estado is Estado.FALLA
    assert "presupuesto real" in evidencia


def test_limitacion_sobre_datos_reales_ok():
    texto = (
        "La validación con presupuestos reales queda como limitación. "
        "El caso no corresponde a una obra ejecutada."
    )

    assert meta.evaluar_datos_reales({"cap1": texto})[0] is Estado.OK


def test_gemelo_digital_en_su_delimitacion_ok():
    assert meta.evaluar_gemelo_digital({"cap1": CAPITULO_1, "cap2": CAPITULO_2})[0] is Estado.OK


def test_gemelo_digital_fuera_de_su_delimitacion_falla():
    fuera = CAPITULO_2.replace("COVENIN.", "El sistema es un gemelo digital de la obra.")

    estado, evidencia = meta.evaluar_gemelo_digital({"cap2": fuera})

    assert estado is Estado.FALLA
    assert "Bases normativas" in evidencia


# --- Instrumentos del tutor -----------------------------------------------------------------


RUBRICA = "\n".join(f"| **T{n}** | criterio {n} | detalle |" for n in range(1, 15))


def test_rubrica_completa_ok_y_sin_t14_falla():
    assert meta.evaluar_rubrica(RUBRICA)[0] is Estado.OK

    estado, evidencia = meta.evaluar_rubrica(RUBRICA.replace("| **T14** |", "| **TX** |"))

    assert estado is Estado.FALLA
    assert "T14" in evidencia


def _acta(veredictos: dict[int, str]) -> str:
    return "\n".join(f"| T{n} | {v} | observacion | respuesta |" for n, v in veredictos.items())


def test_acta_completa_ok():
    veredictos = {n: "cumple" for n in range(1, 15)} | {5: "cumple con observaciones"}

    assert meta.evaluar_acta(_acta(veredictos))[0] is Estado.OK


def test_acta_con_no_cumple_falla_citando_el_criterio():
    veredictos = {n: "cumple" for n in range(1, 15)} | {11: "no cumple"}

    estado, evidencia = meta.evaluar_acta(_acta(veredictos))

    assert estado is Estado.FALLA
    assert "T11" in evidencia


def test_acta_incompleta_falla_y_ausente_pendiente():
    incompleta = {n: "cumple" for n in range(1, 14)}

    assert meta.evaluar_acta(_acta(incompleta))[0] is Estado.FALLA
    assert meta.evaluar_acta(None)[0] is Estado.PENDIENTE


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("**Naturaleza de los datos.** Los APU son ficticios; incluye ARENAZA.", Estado.OK),
        ("**Naturaleza de la línea base.** El presupuesto es un ejemplo.", Estado.FALLA),
        ("**Naturaleza de los datos.** Los APU son ficticios.", Estado.FALLA),
    ],
)
def test_naturaleza_de_los_datos_en_la_fuente_unica(texto, esperado):
    assert meta.evaluar_naturaleza_datos(texto)[0] is esperado
