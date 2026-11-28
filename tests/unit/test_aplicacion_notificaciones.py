"""C11 (servidor): notificaciones por persona con retención de 30 días
(`aplicacion.notificaciones`).

Oráculos escritos a mano sobre datos construidos ficticios (Ana, Rita). Cubre:
- agregar y listar solo las notificaciones propias (otra cuenta no ve ni marca las mías);
- orden de más reciente a más antigua (creada descendente, id descendente);
- retención exacta de 30 días: 30 días exactos se conservan, 30 días + 1 segundo se descartan y se
  borran de la base (sin tocar las de otra persona);
- tope de 200 notificaciones por persona;
- marcar leídas por lista de ids y marcar todas, sin afectar a otra cuenta;
- validación de gravedad, largos máximos, enlace incompleto y rechazo de rutas inseguras
  (`http://`, `https://`, `//evil`, `javascript:`, `\\`, caracteres de control).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from aplicacion import notificaciones
from aplicacion.notificaciones import (
    DIAS_RETENCION,
    GRAVEDADES,
    MAX_DETALLE,
    MAX_ENLACE_RUTA,
    MAX_ENLACE_TEXTO,
    MAX_TITULO,
    MAXIMO_NOTIFICACIONES,
    DatosNotificacion,
    ItemNotificacion,
)
from seguridad.modelo import Notificacion, Usuario
from tests.fixtures.instalacion import administrador, instalacion, persona

BASE = datetime(2026, 11, 26, 12, 0, 0)


@pytest.fixture
def bd_con_cuentas(tmp_path: Path) -> Iterator[tuple[Session, Usuario, Usuario]]:
    with instalacion(tmp_path) as sesion:
        admin = administrador(sesion, tmp_path)
        ana = persona(sesion, admin, "ana", ("arma",), "Ana Demo")
        rita = persona(sesion, admin, "rita", ("revisa",), "Rita Demo")
        sesion.commit()
        yield sesion, ana, rita


def _datos(
    titulo: str = "Presupuesto guardado",
    *,
    gravedad: str = "listo",
    detalle: str = "",
    enlace_texto: str = "",
    enlace_ruta: str = "",
) -> DatosNotificacion:
    return DatosNotificacion(
        gravedad=gravedad,
        titulo=titulo,
        detalle=detalle,
        enlace_texto=enlace_texto,
        enlace_ruta=enlace_ruta,
    )


# --- agregar, listar y orden ---------------------------------------------------------------------


def test_agregar_y_listar_devuelve_campos_exactos_en_orden_descendente(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, _ = bd_con_cuentas
    primera = notificaciones.agregar(
        sesion,
        ana.id,
        _datos("Primera", gravedad="info", detalle="Detalle uno"),
        BASE - timedelta(hours=2),
    )
    segunda = notificaciones.agregar(
        sesion,
        ana.id,
        _datos(
            "Segunda",
            gravedad="advertencia",
            detalle="Detalle dos",
            enlace_texto="Abrir hoja",
            enlace_ruta="/obras/1/hoja?tab=partidas",
        ),
        BASE - timedelta(hours=1),
    )
    tercera = notificaciones.agregar(
        sesion,
        ana.id,
        _datos("Tercera", gravedad="error"),
        BASE,
    )

    lista = notificaciones.listar(sesion, ana.id, BASE)
    assert lista == [tercera, segunda, primera]
    assert segunda == ItemNotificacion(
        id=segunda.id,
        gravedad="advertencia",
        titulo="Segunda",
        detalle="Detalle dos",
        enlace_texto="Abrir hoja",
        enlace_ruta="/obras/1/hoja?tab=partidas",
        creada=BASE - timedelta(hours=1),
        leida=False,
    )


def test_empate_en_fecha_ordena_por_id_descendente(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, _ = bd_con_cuentas
    a = notificaciones.agregar(sesion, ana.id, _datos("A"), BASE)
    b = notificaciones.agregar(sesion, ana.id, _datos("B"), BASE)
    c = notificaciones.agregar(sesion, ana.id, _datos("C"), BASE)

    lista = notificaciones.listar(sesion, ana.id, BASE)
    assert [n.id for n in lista] == [c.id, b.id, a.id]


@pytest.mark.parametrize("gravedad", GRAVEDADES)
def test_acepta_las_cuatro_gravedades_validas(
    bd_con_cuentas: tuple[Session, Usuario, Usuario], gravedad: str
) -> None:
    sesion, ana, _ = bd_con_cuentas
    item = notificaciones.agregar(sesion, ana.id, _datos("Aviso", gravedad=gravedad), BASE)
    assert item.gravedad == gravedad


# --- aislamiento por persona ---------------------------------------------------------------------


def test_cada_persona_ve_solo_las_suyas(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, rita = bd_con_cuentas
    notificaciones.agregar(sesion, ana.id, _datos("Solo de Ana"), BASE)
    notificaciones.agregar(sesion, rita.id, _datos("Solo de Rita"), BASE)

    assert [n.titulo for n in notificaciones.listar(sesion, ana.id, BASE)] == ["Solo de Ana"]
    assert [n.titulo for n in notificaciones.listar(sesion, rita.id, BASE)] == ["Solo de Rita"]


def test_marcar_leidas_por_ids_no_toca_las_de_otra_persona(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, rita = bd_con_cuentas
    n_ana = notificaciones.agregar(sesion, ana.id, _datos("De Ana"), BASE)
    n_rita = notificaciones.agregar(sesion, rita.id, _datos("De Rita"), BASE)

    marcadas = notificaciones.marcar_leidas(sesion, ana.id, ids=[n_ana.id, n_rita.id])
    assert marcadas == 1
    assert notificaciones.listar(sesion, ana.id, BASE)[0].leida is True
    assert notificaciones.listar(sesion, rita.id, BASE)[0].leida is False


def test_marcar_todas_leidas_no_toca_las_de_otra_persona(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, rita = bd_con_cuentas
    notificaciones.agregar(sesion, ana.id, _datos("Ana 1"), BASE - timedelta(minutes=2))
    notificaciones.agregar(sesion, ana.id, _datos("Ana 2"), BASE - timedelta(minutes=1))
    notificaciones.agregar(sesion, rita.id, _datos("Rita 1"), BASE)

    marcadas = notificaciones.marcar_leidas(sesion, ana.id, todas=True)
    assert marcadas == 2
    assert all(n.leida for n in notificaciones.listar(sesion, ana.id, BASE))
    assert notificaciones.listar(sesion, rita.id, BASE)[0].leida is False
    # Volver a marcar no cuenta las ya leídas.
    assert notificaciones.marcar_leidas(sesion, ana.id, todas=True) == 0


def test_marcar_leidas_con_argumentos_invalidos_falla(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, _ = bd_con_cuentas
    with pytest.raises(ValueError, match="identificadores"):
        notificaciones.marcar_leidas(sesion, ana.id, ids=[1], todas=True)
    with pytest.raises(ValueError, match="marcar"):
        notificaciones.marcar_leidas(sesion, ana.id)
    with pytest.raises(ValueError, match="positivo"):
        notificaciones.marcar_leidas(sesion, ana.id, ids=[0])
    assert notificaciones.marcar_leidas(sesion, ana.id, ids=[]) == 0


# --- retención exacta de 30 días -----------------------------------------------------------------


def test_retencion_30_dias_exactos_conserva_en_el_limite_y_borra_lo_anterior(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, rita = bd_con_cuentas
    vencida = BASE - timedelta(days=DIAS_RETENCION, seconds=1)
    justa = BASE - timedelta(days=DIAS_RETENCION)
    reciente = BASE - timedelta(days=1)

    sesion.add_all(
        [
            Notificacion(
                usuario_id=ana.id,
                gravedad="info",
                titulo="Vencida Ana",
                detalle="",
                enlace_texto="",
                enlace_ruta="",
                creada=vencida,
                leida=False,
            ),
            Notificacion(
                usuario_id=ana.id,
                gravedad="listo",
                titulo="Justa 30 dias",
                detalle="",
                enlace_texto="",
                enlace_ruta="",
                creada=justa,
                leida=False,
            ),
            Notificacion(
                usuario_id=ana.id,
                gravedad="error",
                titulo="Reciente Ana",
                detalle="",
                enlace_texto="",
                enlace_ruta="",
                creada=reciente,
                leida=False,
            ),
            Notificacion(
                usuario_id=rita.id,
                gravedad="info",
                titulo="Vencida Rita",
                detalle="",
                enlace_texto="",
                enlace_ruta="",
                creada=vencida,
                leida=False,
            ),
        ]
    )
    sesion.flush()

    lista_ana = notificaciones.listar(sesion, ana.id, BASE)
    assert [n.titulo for n in lista_ana] == ["Reciente Ana", "Justa 30 dias"]

    # La vencida de Ana se borró de la tabla; la de Rita no se tocó al listar Ana.
    restantes_ana = list(
        sesion.scalars(select(Notificacion.titulo).where(Notificacion.usuario_id == ana.id))
    )
    assert set(restantes_ana) == {"Reciente Ana", "Justa 30 dias"}
    restantes_rita = list(
        sesion.scalars(select(Notificacion.titulo).where(Notificacion.usuario_id == rita.id))
    )
    assert restantes_rita == ["Vencida Rita"]


# --- tope de 200 notificaciones ------------------------------------------------------------------


def test_tope_de_200_conserva_las_mas_recientes(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, _ = bd_con_cuentas
    total = MAXIMO_NOTIFICACIONES + 15
    for i in range(total):
        notificaciones.agregar(
            sesion,
            ana.id,
            _datos(f"Notif {i}"),
            BASE - timedelta(minutes=total - i),
        )

    lista = notificaciones.listar(sesion, ana.id, BASE)
    assert len(lista) == MAXIMO_NOTIFICACIONES
    assert lista[0].titulo == f"Notif {total - 1}"
    assert lista[-1].titulo == "Notif 15"

    en_base = list(
        sesion.scalars(select(Notificacion.id).where(Notificacion.usuario_id == ana.id))
    )
    assert len(en_base) == MAXIMO_NOTIFICACIONES


def test_con_el_tope_lleno_de_avisos_del_servidor_la_nueva_queda_y_sale_el_mas_viejo(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    """T5, n.o 5: sin notificaciones del front que podar, se poda el aviso del servidor más viejo;
    la recién creada nunca."""
    sesion, ana, _ = bd_con_cuentas
    for i in range(200):  # el tope, escrito a mano
        notificaciones.agregar(
            sesion,
            ana.id,
            _datos(f"Servidor {i}"),
            BASE - timedelta(minutes=300 - i),
            clave_evento=f"evento:{i}",
        )
    nueva = notificaciones.agregar(sesion, ana.id, _datos("Del front"), BASE)
    titulos = {n.titulo for n in notificaciones.listar(sesion, ana.id, BASE)}
    assert len(titulos) == 200
    assert nueva.titulo in titulos
    assert "Servidor 0" not in titulos and "Servidor 1" in titulos


def test_listar_tambien_limita_a_200_si_hay_mas_en_base(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, _ = bd_con_cuentas
    filas = [
        Notificacion(
            usuario_id=ana.id,
            gravedad="info",
            titulo=f"Directa {i}",
            detalle="",
            enlace_texto="",
            enlace_ruta="",
            creada=BASE - timedelta(seconds=210 - i),
            leida=False,
        )
        for i in range(210)
    ]
    sesion.add_all(filas)
    sesion.flush()

    lista = notificaciones.listar(sesion, ana.id, BASE)
    assert len(lista) == MAXIMO_NOTIFICACIONES
    assert lista[0].titulo == "Directa 209"
    assert lista[-1].titulo == "Directa 10"


# --- validaciones y seguridad de enlace_ruta -----------------------------------------------------


@pytest.mark.parametrize(
    "ruta_mala",
    [
        "http://ejemplo.com/obras",
        "https://ejemplo.com/obras",
        "//evil.example/robo",
        "///evil.example",
        "/obras//evil",
        "javascript:alert(1)",
        "JAVASCRIPT:alert(1)",
        "data:text/html,<h1>x</h1>",
        "obras/1",
        "/\\evil.example",
        "/obras/1\r\nSet-Cookie: a=1",
        "/obras/1\x00",
        "/javascript:alert(1)",
    ],
)
def test_rutas_inseguras_en_enlace_ruta_son_rechazadas(
    bd_con_cuentas: tuple[Session, Usuario, Usuario], ruta_mala: str
) -> None:
    sesion, ana, _ = bd_con_cuentas
    with pytest.raises(ValueError, match="interna"):
        notificaciones.agregar(
            sesion,
            ana.id,
            _datos("Con enlace malo", enlace_texto="Abrir", enlace_ruta=ruta_mala),
            BASE,
        )


@pytest.mark.parametrize(
    "ruta_buena",
    [
        "/",
        "/obras",
        "/obras/12/hoja",
        "/aprobaciones?estado=pendiente",
        "/cuenta/actividad#resumen",
        "/obras/12/hoja?partida=E-01&vista=apu#fila-3",
    ],
)
def test_rutas_internas_seguras_son_aceptadas(
    bd_con_cuentas: tuple[Session, Usuario, Usuario], ruta_buena: str
) -> None:
    sesion, ana, _ = bd_con_cuentas
    item = notificaciones.agregar(
        sesion,
        ana.id,
        _datos("Con enlace", enlace_texto="Ir", enlace_ruta=ruta_buena),
        BASE,
    )
    assert item.enlace_ruta == ruta_buena
    assert item.enlace_texto == "Ir"


def test_validacion_de_gravedad_largos_y_enlace_incompleto(
    bd_con_cuentas: tuple[Session, Usuario, Usuario],
) -> None:
    sesion, ana, _ = bd_con_cuentas
    with pytest.raises(ValueError, match="gravedad"):
        notificaciones.agregar(sesion, ana.id, _datos("X", gravedad="critico"), BASE)
    with pytest.raises(ValueError, match="título"):
        notificaciones.agregar(sesion, ana.id, _datos("   "), BASE)
    with pytest.raises(ValueError, match="200"):
        notificaciones.agregar(sesion, ana.id, _datos("a" * (MAX_TITULO + 1)), BASE)
    with pytest.raises(ValueError, match="1 000"):
        notificaciones.agregar(
            sesion, ana.id, _datos("OK", detalle="b" * (MAX_DETALLE + 1)), BASE
        )
    with pytest.raises(ValueError, match="120"):
        notificaciones.agregar(
            sesion,
            ana.id,
            _datos("OK", enlace_texto="c" * (MAX_ENLACE_TEXTO + 1), enlace_ruta="/obras"),
            BASE,
        )
    with pytest.raises(ValueError, match="300"):
        notificaciones.agregar(
            sesion,
            ana.id,
            _datos("OK", enlace_texto="Ir", enlace_ruta="/" + "d" * MAX_ENLACE_RUTA),
            BASE,
        )
    with pytest.raises(ValueError, match="enlace"):
        notificaciones.agregar(sesion, ana.id, _datos("OK", enlace_texto="Solo texto"), BASE)
    with pytest.raises(ValueError, match="enlace"):
        notificaciones.agregar(sesion, ana.id, _datos("OK", enlace_ruta="/obras"), BASE)
