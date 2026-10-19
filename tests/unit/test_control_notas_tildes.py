"""T8b (ampliación): las notas, motivos y títulos del núcleo en la pantalla de Control, con tilde.

Además de las alertas, el texto del núcleo llega a las columnas `Nota` de los indicadores, de la
reproyección y de las opciones de recuperación. Mismo método: frases fijas, el texto del usuario
(código o nombre de partida) no se altera. Oráculos con tilde escritos a mano.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from aplicacion import control
from core.budget.recuperacion import Opcion, Supuesto


def _partida(codigo: str, motivo: str = "", detenida: bool = False, evidencia: bool = False):
    return SimpleNamespace(
        codigo=codigo,
        pendiente=Decimal(1),
        indice=Decimal("0.5"),
        fin=None,
        motivo=motivo,
        detenida=detenida,
        sin_evidencia=evidencia,
    )


def test_la_nota_de_la_reproyeccion_sale_con_tilde_y_el_codigo_del_usuario_no_cambia() -> None:
    resultado = SimpleNamespace(
        reproyeccion=SimpleNamespace(
            partidas=[
                _partida("dia-ningun", "la partida no esta en el plan"),
                _partida("termino habil", "el SPI global es 0: sin ritmo no se proyecta"),
                _partida("ningun", detenida=True),
            ]
        )
    )
    filas = control.filas_de_reproyeccion(resultado)  # type: ignore[arg-type]
    assert [(f["Partida"], f["Nota"]) for f in filas] == [
        ("dia-ningun", "la partida no está en el plan"),
        ("termino habil", "el SPI global es 0: sin ritmo no se proyecta"),
        ("ningun", "detenida"),
    ]


def _resultado_de_indicadores(no_ind: dict[str, str], no_sep: dict[str, str], fuente: str):
    n = Decimal(1)
    return SimpleNamespace(
        instantanea=SimpleNamespace(moneda="USD", corte=None),
        indicadores=SimpleNamespace(
            bac=n,
            pv=n,
            ev=n,
            ac=None,
            sv=n,
            cv=None,
            spi=n,
            cpi=None,
            eac_indice=None,
            eac_sistema=None,
            vac=None,
            termino_indice=None,
            no_disponible=no_ind,
        ),  # fmt: skip
        separacion=SimpleNamespace(
            precio=None, consumo=None, metodo="comprobacion", fuente=fuente, no_disponible=no_sep
        ),
    )


def test_las_notas_de_los_indicadores_salen_con_tilde(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(control, "_otra_moneda", lambda sesion, resultado: ("Bs", None))
    resultado = _resultado_de_indicadores(
        {"AC": "sin costos reales declarados", "CPI": "AC = 0: aun no hay costos reales"},
        {"precio": "sin precios del corte (S1): la separacion no esta disponible"},
        fuente="Nota del usuario: dia ningun termino",
    )
    filas = {
        f["Indicador"]: f
        for f in control.filas_de_indicadores(None, resultado)  # type: ignore[arg-type]
    }
    assert filas["CPI"]["Nota"] == "AC = 0: aún no hay costos reales"
    assert filas["Desvio de precio (USD)"]["Nota"] == (
        "sin precios del corte (S1): la separación no está disponible"
    )
    # La fuente del precio la escribió el usuario: no se toca.
    fuente = filas["Metodo y fuente del precio del corte"]["Nota"]
    assert fuente == "Nota del usuario: dia ningun termino"


def test_la_nota_de_las_opciones_sale_con_tilde_y_los_codigos_del_usuario_no_cambian() -> None:
    sin_aplicar = Opcion(
        "cuadrillas",
        False,
        "no aplica (dia-1: sin composicion de APU; ningun-2: sin mano de obra a jornal; "
        "habil-3: sin rendimiento)",
    )
    paralelo = Opcion(
        "paralelo",
        False,
        "ninguna partida sin empezar con inicio posterior al periodo siguiente",
    )
    aplicada = Opcion(
        "horas_extra",
        True,
        "",
        termino=20,
        retraso=1,
        equilibrio=SimpleNamespace(punto=Decimal(5), mensaje="se alcanza en Mes 3"),
        supuestos=(
            Supuesto("penalizacion diaria", "5", "DATO_DEL_CONTRATO"),
            Supuesto("cuadrillas maximas", "3", "SUPUESTO_DECLARADO"),
            Supuesto("horas extra por dia", "2", "SUPUESTO_DECLARADO", "tope legal 2 h"),
            Supuesto("FCAS sobre las horas extra", "si", "SUPUESTO_DECLARADO"),
            Supuesto(
                "limites de horas extra", "10 h por semana, 100 h por año", "FUENTE_VERIFICADA"
            ),
            Supuesto("costo diario de la cuadrilla", "composiciones de la linea base", "S"),
            Supuesto("independencia de las partidas", "dia, ningun", "SUPUESTO_DECLARADO"),
        ),
    )
    filas = {f["Opcion"]: f for f in control.filas_de_opciones([sin_aplicar, paralelo, aplicada])}
    assert filas["Más cuadrillas"]["Nota"] == (
        "no aplica (dia-1: sin composición de APU; ningun-2: sin mano de obra a jornal; "
        "habil-3: sin rendimiento)"
    )
    assert filas["Partidas en paralelo"]["Nota"] == (
        "ninguna partida sin empezar con inicio posterior al período siguiente"
    )
    assert filas["Horas extra"]["Nota"] == (
        "penalización diaria: 5 (DATO_DEL_CONTRATO); cuadrillas máximas: 3 (SUPUESTO_DECLARADO); "
        "horas extra por día: 2 (SUPUESTO_DECLARADO); "
        "FCAS sobre las horas extra: sí (SUPUESTO_DECLARADO); "
        "límites de horas extra: 10 h por semana, 100 h por año (FUENTE_VERIFICADA); "
        "costo diario de la cuadrilla: composiciones de la línea base (S); "
        "independencia de las partidas: dia, ningun (SUPUESTO_DECLARADO)"
    )
    assert filas["Horas extra"]["Punto de equilibrio"] == "5.00 (se alcanza en Mes 3)"


@pytest.mark.parametrize(
    ("emitido", "esperado"),
    [
        ("Mas cuadrillas", "Más cuadrillas"),
        ("Horas extra", "Horas extra"),
        ("Partidas en paralelo", "Partidas en paralelo"),
        ("Aceptar el retraso", "Aceptar el retraso"),
        (
            "permiso de la Inspectoria del Trabajo (LOTTT art. 182) para las horas extra",
            "permiso de la Inspectoría del Trabajo (LOTTT art. 182) para las horas extra",
        ),
        (
            "no existe punto de equilibrio: el margen de contribucion no es positivo",
            "no existe punto de equilibrio: el margen de contribución no es positivo",
        ),
        (
            "sin curva de inversion: el punto de equilibrio no se ubica en el plan",
            "sin curva de inversión: el punto de equilibrio no se ubica en el plan",
        ),
        ("ninguna partida pasa del objetivo", "ninguna partida pasa del objetivo"),
        # Lo que escribió el usuario no entra en el catálogo.
        ("Mas cuadrillas de dia", "Mas cuadrillas de dia"),
        ("no aplica (dia: motivo ningun)", "no aplica (dia: motivo ningun)"),
    ],
)
def test_titulos_requisitos_y_mensajes_sueltos_del_nucleo(emitido: str, esperado: str) -> None:
    assert control.con_tildes(emitido) == esperado
