"""T8b: las alertas del control de obra salen con tilde aunque el texto del núcleo no la lleve.

El texto de las alertas nace en `core/budget/valor_ganado.py` (y el del punto de equilibrio en
`core/budget/equilibrio.py`), que no se toca. La capa de aplicación restituye las tildes sobre las
FRASES FIJAS del núcleo (nunca sobre palabras sueltas) y deja intacto lo que escribió el usuario.

Los oráculos con tilde están escritos a mano, frase por frase, leyendo el núcleo.
"""

from __future__ import annotations

import ast
import re
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
