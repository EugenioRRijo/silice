"""T8b: las alertas del control de obra salen con tilde aunque el texto del núcleo no la lleve.

El texto de las alertas nace en `core/budget/valor_ganado.py` (y el del punto de equilibrio en
`core/budget/equilibrio.py`), que no se toca. La capa de aplicación restituye las tildes sobre las
FRASES FIJAS del núcleo (nunca sobre palabras sueltas) y deja intacto lo que escribió el usuario.

Los oráculos con tilde están escritos a mano, frase por frase, leyendo el núcleo.
"""

from __future__ import annotations

import ast
import re
import time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from aplicacion.control import PLANTILLAS_DEL_NUCLEO, alertas_en_filas, con_tildes
from core.budget.valor_ganado import Alerta, Alertas
from core.contracts.verificacion import Severidad

RAIZ = Path(__file__).resolve().parents[2]

# (texto tal como lo emite el núcleo, texto esperado con tildes). Una fila por plantilla del núcleo.
CASOS = [
    # AL-1 y AL-2: sin palabras con tilde, salen tal cual.
    ("retraso: SPI 0.8000", "retraso: SPI 0.8000"),
    ("sobrecosto: CPI 0.7000", "sobrecosto: CPI 0.7000"),
    # AL-3
    (
        "el termino proyectado (dia 12) pasa 3 dia(s) habil(es) del plan base (dia 9)",
        "el término proyectado (día 12) pasa 3 día(s) hábil(es) del plan base (día 9)",
    ),
    # AL-4 (alerta)
    (
        "el punto de equilibrio proyectado: no existe punto de equilibrio: el margen de "
        "contribucion no es positivo",
        "el punto de equilibrio proyectado: no existe punto de equilibrio: el margen de "
        "contribución no es positivo",
    ),
    (
        "el punto de equilibrio proyectado: el punto de equilibrio no se alcanza dentro del "
        "contrato",
        "el punto de equilibrio proyectado: el punto de equilibrio no se alcanza dentro del "
        "contrato",
    ),
    (
        "el punto de equilibrio proyectado: el presupuesto no tiene ventas: no aplica",
        "el punto de equilibrio proyectado: el presupuesto no tiene ventas: no aplica",
    ),
    (
        "el punto de equilibrio proyectado: se alcanza en Mes 3",
        "el punto de equilibrio proyectado: se alcanza en Mes 3",
    ),
    (
        "el punto de equilibrio proyectado: sin curva de inversion: el punto de equilibrio no "
        "se ubica en el plan",
        "el punto de equilibrio proyectado: sin curva de inversión: el punto de equilibrio no "
        "se ubica en el plan",
    ),
    (
        "el punto de equilibrio proyectado sube mas de 10 puntos porcentuales sobre el de la "
        "linea base",
        "el punto de equilibrio proyectado sube más de 10 puntos porcentuales sobre el de la "
        "línea base",
    ),
    # AL-5
    (
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvia 12.50 "
        "sobre un valor ganado de 100.00",
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvía 12.50 "
        "sobre un valor ganado de 100.00",
    ),
    # AL-6
    (
        "la partida 01-A tiene trabajo planificado y ningun avance (detenida)",
        "la partida 01-A tiene trabajo planificado y ningún avance (detenida)",
    ),
    # Motivos de las alertas sin evaluar
    ("SPI no aplica", "SPI no aplica"),
    ("CPI no disponible", "CPI no disponible"),
    ("AC no disponible", "AC no disponible"),
    ("EAC no disponible", "EAC no disponible"),
    (
        "el punto de equilibrio no aplica o AC no esta disponible",
        "el punto de equilibrio no aplica o AC no está disponible",
    ),
    ("sin avance ejecutado", "sin avance ejecutado"),
    ("sin costos reales declarados", "sin costos reales declarados"),
    (
        "PV = 0: el corte es anterior a todo trabajo planificado",
        "PV = 0: el corte es anterior a todo trabajo planificado",
    ),
    ("AC = 0: aun no hay costos reales", "AC = 0: aún no hay costos reales"),
    ("sin precios del corte", "sin precios del corte"),
    (
        "sin precios del corte (S1): la separacion no esta disponible",
        "sin precios del corte (S1): la separación no está disponible",
    ),
    ("sin precio del corte para la partida 01-A", "sin precio del corte para la partida 01-A"),
    ("sin precio del corte para 01-A, 01-B", "sin precio del corte para 01-A, 01-B"),
    (
        "sin avance o sin costos reales: el rendimiento del consumo no existe",
        "sin avance o sin costos reales: el rendimiento del consumo no existe",
    ),
    (
        "sin tasa aplicable para: 10 USD del 2026-01-05",
        "sin tasa aplicable para: 10 USD del 2026-01-05",
    ),
    ("no proyectable: 01-A, 01-B", "no proyectable: 01-A, 01-B"),
    (
        "nada queda pendiente: la fecha de la ultima valuacion",
        "nada queda pendiente: la fecha de la última valuación",
    ),
    # Motivos por partida de la reproyección (mismo vocabulario cerrado del núcleo)
    ("la partida no esta en el plan", "la partida no está en el plan"),
    (
        "el SPI global es 0: sin ritmo no se proyecta",
        "el SPI global es 0: sin ritmo no se proyecta",
    ),
    # Recuperación (opciones): títulos, supuestos, requisitos y motivos
    ("Mas cuadrillas", "Más cuadrillas"),
    ("Horas extra", "Horas extra"),
    ("Partidas en paralelo", "Partidas en paralelo"),
    ("Aceptar el retraso", "Aceptar el retraso"),
    ("ninguna partida pasa del objetivo", "ninguna partida pasa del objetivo"),
    (
        "ninguna partida sin empezar con inicio posterior al periodo siguiente",
        "ninguna partida sin empezar con inicio posterior al período siguiente",
    ),
    (
        "no aplica (01-A: sin composicion de APU; 01-B: sin rendimiento; 01-C: sin mano de obra "
        "a jornal)",
        "no aplica (01-A: sin composición de APU; 01-B: sin rendimiento; 01-C: sin mano de obra "
        "a jornal)",
    ),
    ("sin composicion de APU", "sin composición de APU"),
    ("sin rendimiento", "sin rendimiento"),
    ("sin mano de obra a jornal", "sin mano de obra a jornal"),
    (
        "sin fuente: ninguna norma verificada la fija",
        "sin fuente: ninguna norma verificada la fija",
    ),
    (
        "permiso de la Inspectoria del Trabajo (LOTTT art. 182) para las horas extra",
        "permiso de la Inspectoría del Trabajo (LOTTT art. 182) para las horas extra",
    ),
    ("penalizacion diaria", "penalización diaria"),
    ("composiciones de la linea base", "composiciones de la línea base"),
    ("costo diario de la cuadrilla", "costo diario de la cuadrilla"),
    ("costo fijo en el tiempo", "costo fijo en el tiempo"),
    ("CF' = CF · D'/D", "CF' = CF · D'/D"),
    ("eta de cuadrillas", "eta de cuadrillas"),
    (
        "Lee (2022) es la base del metodo, no del valor",
        "Lee (2022) es la base del método, no del valor",
    ),
    ("cuadrillas maximas", "cuadrillas máximas"),
    ("horas extra por dia", "horas extra por día"),
    ("tope legal 2 h", "tope legal 2 h"),
    ("eta de horas extra", "eta de horas extra"),
    ("LOTTT art. 118: por lo menos 50 %", "LOTTT art. 118: por lo menos 50 %"),
    ("FCAS sobre las horas extra", "FCAS sobre las horas extra"),
    ("si", "sí"),
    (
        "interpretacion de los arts. 104 y 178; decide el tutor",
        "interpretación de los arts. 104 y 178; decide el tutor",
    ),
    ("jornada ordinaria", "jornada ordinaria"),
    ("LOTTT art. 173", "LOTTT art. 173"),
    ("limites de horas extra", "límites de horas extra"),
    ("10 h por semana, 100 h por año", "10 h por semana, 100 h por año"),
    ("LOTTT art. 178", "LOTTT art. 178"),
    ("independencia de las partidas", "independencia de las partidas"),
    (
        "el plan no tiene dependencias: el usuario lo declara con su fuente (S2-R4)",
        "el plan no tiene dependencias: el usuario lo declara con su fuente (S2-R4)",
    ),
    (
        "LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)",
        "LOTTT G.O. 6.076 Ext. 07-05-2012 (docs/fuentes/LOTTT_GO_6076_Ext_2012-05-07.txt)",
    ),
    # Mensajes del punto de equilibrio sueltos (campo `mensaje` de la API y de las opciones)
    (
        "no existe punto de equilibrio: el margen de contribucion no es positivo",
        "no existe punto de equilibrio: el margen de contribución no es positivo",
    ),
    (
        "el punto de equilibrio no se alcanza dentro del contrato",
        "el punto de equilibrio no se alcanza dentro del contrato",
    ),
    (
        "el presupuesto no tiene ventas: no aplica",
        "el presupuesto no tiene ventas: no aplica",
    ),
    ("se alcanza en Mes 3", "se alcanza en Mes 3"),
    (
        "sin curva de inversion: el punto de equilibrio no se ubica en el plan",
        "sin curva de inversión: el punto de equilibrio no se ubica en el plan",
    ),
]


@pytest.mark.parametrize(("emitido", "esperado"), CASOS)
def test_cada_plantilla_del_nucleo_sale_con_tilde(emitido: str, esperado: str) -> None:
    assert con_tildes(emitido) == esperado


def test_la_funcion_es_idempotente_y_respeta_lo_que_ya_trae_tilde() -> None:
    ya = "el término proyectado (día 12) pasa 3 día(s) hábil(es) del plan base (día 9)"
    assert con_tildes(ya) == ya
    for _emitido, esperado in CASOS:
        assert con_tildes(esperado) == esperado


@pytest.mark.parametrize(
    ("emitido", "esperado"),
    [
        # El usuario puso «dia» o «ningun» en el nombre o código de la partida: no se toca.
        (
            "la partida dia ningun desvia tiene trabajo planificado y ningun avance (detenida)",
            "la partida dia ningun desvia tiene trabajo planificado y ningún avance (detenida)",
        ),
        (
            "sin precio del corte para la partida dia-ningun",
            "sin precio del corte para la partida dia-ningun",
        ),
        (
            "sin precio del corte para dia, ningun, habil",
            "sin precio del corte para dia, ningun, habil",
        ),
        ("no proyectable: dia, termino", "no proyectable: dia, termino"),
        (
            "sin tasa aplicable para: ningun dia habil",
            "sin tasa aplicable para: ningun dia habil",
        ),
    ],
)
def test_un_nombre_de_partida_del_usuario_no_se_altera(emitido: str, esperado: str) -> None:
    assert con_tildes(emitido) == esperado


@pytest.mark.parametrize(
    "libre",
    [
        "dia",
        "ningun avance",
        "la partida Excavacion del dia tiene ningun valor",
        "el termino proyectado de otra cosa",
        "desvia mucho",
        "una frase nueva del nucleo que desvia el termino en 3 dias habiles",
        "",
    ],
)
def test_una_frase_que_no_esta_catalogada_pasa_tal_cual(libre: str) -> None:
    assert con_tildes(libre) == libre


def test_alertas_en_filas_pasa_descripcion_y_motivo_por_la_funcion() -> None:
    resultado = SimpleNamespace(
        alertas=Alertas(
            (
                Alerta(
                    "AL-6",
                    Severidad.ADVERTENCIA,
                    "la partida dia tiene trabajo planificado y ningun avance (detenida)",
                    None,
                    None,
                ),
                Alerta(
                    "AL-3",
                    Severidad.ERROR,
                    "el termino proyectado (dia 12) pasa 3 dia(s) habil(es) del plan base (dia 9)",
                    Decimal(3),
                    Decimal(1),
                ),
            ),
            {"AL-4": "el punto de equilibrio no aplica o AC no esta disponible"},
        )
    )
    filas = alertas_en_filas(resultado)  # type: ignore[arg-type]
    assert [f["Descripcion"] for f in filas] == [
        "la partida dia tiene trabajo planificado y ningún avance (detenida)",
        "el término proyectado (día 12) pasa 3 día(s) hábil(es) del plan base (día 9)",
        "el punto de equilibrio no aplica o AC no está disponible",
    ]
    assert [f["Alerta"] for f in filas] == ["AL-6", "AL-3", "AL-4"]


# --- guardia: el núcleo no puede cambiar o agregar una frase sin que esta prueba lo diga ---------


def _fragmentos_de_texto(ruta: Path) -> set[str]:
    """Los trozos de texto literal (con espacio) de un módulo del núcleo, sin docstrings ni
    mensajes de `raise` (que no llegan a la pantalla de alertas)."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    excluidos: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Raise):
            excluidos.update(id(n) for n in ast.walk(nodo))
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            cuerpo = nodo.body
            if (
                cuerpo
                and isinstance(cuerpo[0], ast.Expr)
                and isinstance(cuerpo[0].value, ast.Constant)
            ):
                excluidos.add(id(cuerpo[0].value))
    trozos: set[str] = set()
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Constant)
            and isinstance(nodo.value, str)
            and id(nodo) not in excluidos
            and " " in nodo.value.strip()
        ):
            trozos.add(nodo.value)
    return trozos


def test_ninguna_frase_del_nucleo_queda_sin_catalogar() -> None:
    """Si el núcleo agrega o cambia una frase de alerta o de motivo, esta prueba la lista.

    Hay que agregarla a `PLANTILLAS_DEL_NUCLEO` (y a CASOS arriba) para que no salga sin tilde.
    """
    crudos = [crudo for crudo, _ in PLANTILLAS_DEL_NUCLEO]
    sin_catalogar = sorted(
        f"{ruta.name}: {trozo!r}"
        for ruta in (
            RAIZ / "core" / "budget" / "valor_ganado.py",
            RAIZ / "core" / "budget" / "equilibrio.py",
            RAIZ / "core" / "budget" / "recuperacion.py",
            RAIZ / "core" / "budget" / "control.py",
        )
        for trozo in _fragmentos_de_texto(ruta)
        if not any(trozo.strip() in crudo for crudo in crudos)
    )
    assert sin_catalogar == [], "frases del núcleo sin catalogar:\n" + "\n".join(sin_catalogar)


def test_todo_caso_de_la_prueba_pertenece_al_catalogo_y_al_reves() -> None:
    """El catálogo no lleva plantillas muertas: cada una la ejerce algún caso escrito a mano."""
    emitidos = [e for e, _ in CASOS]
    for crudo, _ in PLANTILLAS_DEL_NUCLEO:
        assert any(_calza(crudo, e) for e in emitidos), crudo


def _calza(crudo: str, texto: str) -> bool:
    patron = re.escape(crudo)
    patron = re.sub(r"\\\{[a-z_]+\\\}", ".+", patron)
    return re.fullmatch(patron, texto) is not None


# --- robustez: el texto del usuario puede ser hostil (largo, anidado, con separadores) ----------

LIMITE_DE_SEGUNDOS = 1.0
N = 100_000


def _adversariales(n: int) -> dict[str, str]:
    al3 = "el termino proyectado (dia "
    al5 = (
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvia "
        + " sobre un valor ganado de " * (n // 26)
        + "\n!"
    )
    codigo = "X: el termino proyectado (dia " + "9) pasa 3 dia(s) habil(es) del plan base (dia " * (
        n // 46
    )
    return {
        "al3_sin_cierre": al3 + "1) pasa " * (n // 8) + "x",
        "al3_separadores": al3 + "9) pasa 3 dia(s) habil(es) del plan base (dia " * (n // 46) + "X",
        "al3_mezcla": al3 + ") pasa  dia(s) habil(es) del plan base (dia " * (n // 44) + "Z",
        "al5": al5,
        "al6": "la partida "
        + "tiene trabajo planificado y ningun avance (detenida) " * (n // 52)
        + "Q",
        "no_aplica_via_codigo": f"no aplica ({codigo}: sin composicion de APU)",
        "no_aplica_largo": "no aplica (" + "a: b; " * (n // 6) + ")",
    }


@pytest.mark.parametrize("n", [N, 1_900])
@pytest.mark.parametrize(
    "nombre", ["al3_sin_cierre", "al3_separadores", "al3_mezcla", "al5", "al6",
               "no_aplica_via_codigo", "no_aplica_largo"],
)  # fmt: skip
def test_un_texto_adversarial_vuelve_intacto_en_menos_de_un_segundo(nombre: str, n: int) -> None:
    texto = _adversariales(n)[nombre]
    inicio = time.perf_counter()
    salida = con_tildes(texto)
    segundos = time.perf_counter() - inicio
    print(f"{nombre} n={n}: {segundos:.3f} s")
    if nombre == "no_aplica_via_codigo" and n <= 2_000:
        # Bajo el tope, el código del usuario queda igual y solo se corrige el motivo del núcleo.
        assert salida == texto.replace("sin composicion de APU)", "sin composición de APU)")
    else:
        assert salida == texto
    assert segundos < LIMITE_DE_SEGUNDOS


@pytest.mark.parametrize("profundidad", [100, 2_000])
def test_un_no_aplica_anidado_no_revienta_y_vuelve_intacto(profundidad: int) -> None:
    texto = "no aplica (a: " * profundidad + "x" + ")" * profundidad
    assert con_tildes(texto) == texto
    via_codigo = f"no aplica ({texto}: sin rendimiento)"
    assert con_tildes(via_codigo) == via_codigo


def test_un_codigo_con_separadores_no_se_altera_fuera_de_su_motivo() -> None:
    # Fuera de un «no aplica (...)» no es una frase del núcleo: intacto.
    assert con_tildes("Z: sin composicion de APU; W") == "Z: sin composicion de APU; W"
    # Dentro, solo el motivo del núcleo (a la derecha del último «: ») se corrige.
    assert con_tildes("no aplica (A: B: sin composicion de APU)") == (
        "no aplica (A: B: sin composición de APU)"
    )
    assert con_tildes("no aplica (Z: sin composicion de APU; W: sin rendimiento)") == (
        "no aplica (Z: sin composición de APU; W: sin rendimiento)"
    )
    # Un motivo que no es del núcleo deja el item intacto, aunque parezca una plantilla.
    texto = (
        "no aplica (a: el termino proyectado (dia 1) pasa 2 dia(s) habil(es) del plan base (dia 3))"
    )
    assert con_tildes(texto) == texto
    anidado = "no aplica (a: no aplica (b: sin composicion de APU))"
    assert con_tildes(anidado) == anidado
