"""«Revisar un paquete» en la capa de aplicación (T7 de la migración final; RM-1, UC-23, RF-86/87).

La lógica sin Streamlit de la revisión pasa de `ui/revision.py` a `aplicacion/revision.py` (la API
nueva no puede importar `ui/`), y con ella lo que la pantalla clásica calculaba y decía por su
cuenta (`ui/paginas/revisar.py`: el análisis de un archivo y los textos de cada sección), para que
la clásica y la nueva digan lo mismo con las mismas palabras. `ui/revision.py` queda como
reexportación explícita, igual que `ui/subidas.py` (el nombre seguro de una subida, que la
recepción usa al guardar el archivo).

Oráculos: los textos literales de `ui/paginas/revisar.py` antes de la mudanza (copiados a mano),
la memoria del ejemplo mínimo (`tests/fixtures/canonico/ejemplo_v1.py`: total 836,7975) y la
aritmética del contraste con una lista del revisor hecha a mano en la prueba. Datos ficticios.
"""

from __future__ import annotations

import ast
import copy
import hashlib
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from core import models
from core.budget.canonico import json_canonico
from core.catalog import abrir_sesion, crear_esquema, crear_motor
from paquete import modelo as paq
from seguridad import empresas, firma
from seguridad.modelo import EmpresaRegistrada
from tests.fixtures.canonico.ejemplo_v1 import EJEMPLO_V1
from tests.fixtures.canonico_minimo import sembrar_minimo
from tests.fixtures.instalacion import AHORA, instalacion
from tests.fixtures.paquetes import EMPRESA, con_manifiesto, paquete

RAIZ = Path(__file__).resolve().parents[2]
PAR = firma.generar_par()
RECIBIDO = datetime(2026, 11, 12, 10, 0)
TOTAL = Decimal("836.7975")  # 20 m3 x 41,839875 USD/m3 (memoria del ejemplo mínimo)


def _definiciones(ruta: Path) -> list[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    return [
        nodo.name
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef)
    ]


@pytest.mark.parametrize(
    ("reexportado", "original", "archivo"),
    [
        ("ui.revision", "aplicacion.revision", "ui/revision.py"),
        ("ui.subidas", "aplicacion.subidas", "ui/subidas.py"),
    ],
)
def test_ui_reexporta_la_capa_de_aplicacion(reexportado: str, original: str, archivo: str) -> None:
    """RM-1: los mismos objetos (no copias) y ninguna definición propia en `ui/`."""
    import importlib

    de_ui = importlib.import_module(reexportado)
    de_aplicacion = importlib.import_module(original)
    assert de_ui.__all__ and set(de_ui.__all__) <= set(vars(de_aplicacion))
    for nombre in de_ui.__all__:
        assert getattr(de_ui, nombre) is getattr(de_aplicacion, nombre), nombre
    assert _definiciones(RAIZ / archivo) == []


def test_ui_revision_sigue_ofreciendo_lo_que_usaban_la_pantalla_y_las_pruebas() -> None:
    """Lo que `ui/revision.py` exportaba antes de la mudanza sigue ahí (lista escrita a mano)."""
    from ui import revision

    antes = {
        "LIMITE_SEGUNDOS",
        "DiferenciaDeclarada",
        "EntregaAnterior",
        "Recibido",
        "Reauditoria",
        "ReferenciaDeMercado",
        "Servicios",
        "auditar_excel_externo",
        "banner_de_version",
        "cambios_nuevos",
        "contra_la_base_del_revisor",
        "contra_la_entrega_anterior",
        "declaracion_retroactiva",
        "dictaminar",
        "empresa_propia_para_revisar",
        "entrega_anterior",
        "excel_de_presupuesto",
        "excel_de_revision",
        "instantanea_del_documento",
        "leer_documento",
        "login_de",
        "plantilla_uc05",
        "precios_de_lista",
        "reauditar",
        "recibir",
        "revisor_armo",
        "tablas_de_revision",
    }
    assert antes <= set(revision.__all__)


def test_ui_subidas_sigue_ofreciendo_el_nombre_seguro() -> None:
    from ui import subidas

    assert {"LONGITUD_MAXIMA", "Subida", "guardar_subida", "nombre_seguro"} <= set(subidas.__all__)
    assert subidas.nombre_seguro("..\\..\\CON.silice") == "_CON.silice"


# --- los textos de la pantalla, en un solo lugar ------------------------------------------------


def test_los_textos_fijos_son_los_de_la_pantalla_clasica() -> None:
    from aplicacion import revision

    assert revision.AVISO_YA_RECIBIDO == "Ya recibió este mismo paquete"
    assert revision.AYUDA_EMPRESA_NO_REGISTRADA == (
        "Para que sus paquetes salgan verificados, el administrador debe registrar la clave "
        "de esa empresa (Administración), comprobando su huella por otro canal."
    )
    assert revision.PRECIOS_COINCIDEN == (
        "Los precios y totales que declara el paquete coinciden con los recalculados."
    )
    assert revision.PRECIOS_NO_COINCIDEN == (
        "Hay precios o totales declarados que no coinciden con el recálculo."
    )
    assert revision.SIN_ENTREGA_ANTERIOR == (
        "Esta instalación no recibió una entrega anterior de este proyecto."
    )
    assert revision.SIN_LISTAS == "Este caso no tiene listas de precios para contrastar."
    assert revision.TITULO_CONTRA_MI_LISTA == "El paquete con los precios de mi lista"
    assert revision.DICTAMEN_GUARDADO == "Dictamen guardado, atado al SHA-256 de este archivo."
    assert revision.NOTA_EXCEL == (
        "Este Excel se regeneró aquí desde presupuesto.json; el del emisor no se ofrece."
    )
    assert revision.EXCEL_NO_VERIFICADO == (
        "No verificado: un Excel no trae cadena ni firma. Se audita igual."
    )
    assert revision.CARPETA_PAQUETES == "paquetes"  # datos\\paquetes\\, como antes de T7
    assert revision.SIN_DICTAMEN == (
        "Este paquete no quedó registrado (está alterado o no trae los datos mínimos): no admite "
        "dictamen. Pida al emisor uno nuevo."
    )
    assert revision.TITULOS_DE_HALLAZGOS == (
        ("nuevos", "El emisor no los declaró"),
        ("ya_no", "Los declaró y ya no aparecen"),
        ("comunes", "En común"),
    )


def test_el_aviso_de_quien_armo_dice_las_versiones() -> None:
    from aplicacion import revision

    assert revision.aviso_de_quien_armo(()) is None
    assert revision.aviso_de_quien_armo(("004", "005")) == (
        "Usted armó o cambió este presupuesto: lo está revisando la misma persona que lo "
        "armó (figura en la versión 004, 005). Su dictamen lo dejará registrado; no se le "
        "impide darlo."
    )


def test_titulos_y_leyendas_de_las_secciones() -> None:
    from aplicacion import revision

    assert revision.titulo_de_cambios(False) == "Quién cambió qué"
    assert revision.titulo_de_cambios(True) == "Quién cambió qué desde la entrega anterior"
    assert revision.titulo_contra_anterior("004") == "Contra la entrega anterior (004)"
    assert revision.nombre_de_excel("presupuesto", "a" * 64) == f"presupuesto-{'a' * 12}.xlsx"
    assert revision.nombre_de_excel("revision", "b" * 64) == f"revision-{'b' * 12}.xlsx"
    with pytest.raises(ValueError):
        revision.nombre_de_excel("emisor", "c" * 64)


def test_el_dictamen_anterior_se_lee_en_una_linea() -> None:
    from aplicacion import revision

    fila = {
        "resultado": "con observaciones",
        "usuario": "Rita <rita>",
        "fecha": datetime(2026, 11, 12, 10, 5, 59),
        "estado_verificacion": "verificado",
    }
    assert revision.texto_de_dictamen(fila) == (
        "Dictamen anterior: con observaciones · Rita <rita> · 2026-11-12 10:05 · "
        "verificación entonces: verificado"
    )


# --- el análisis de un archivo (lo que la pantalla clásica calculaba en `_analizar`) -----------


@pytest.fixture
def mundo(tmp_path: Path):
    """Un caso con MIN-001 sembrado (su «Lista de prueba») y una instalación que conoce la clave
    de «Contratista Demo, C.A.»."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'caso.db').as_posix()}")
    crear_esquema(motor)
    paq.crear_esquema_paquete(motor)
    with abrir_sesion(motor) as caso, instalacion(tmp_path / "revisor") as bd:
        sembrar_minimo(caso)
        caso.commit()
        bd.add(
            EmpresaRegistrada(
                empresa=EMPRESA,
                rif="J-00000000-0",
                publica=PAR.publica,
                huella=firma.huella_completa(PAR.publica),
                estado="activa",
                comprobada_con="Ana, por teléfono",
                metodo="telefono",
                fecha_comprobacion=AHORA,
                registrada_por="admin",
            )
        )
        bd.commit()
        yield caso, bd, tmp_path / "paquetes"
    motor.dispose()


def _documento() -> bytes:
    return json_canonico(copy.deepcopy(EJEMPLO_V1))


def _analizar(mundo, datos: bytes, login: str = "rita"):
    from aplicacion import revision

    caso, bd, carpeta = mundo
    return revision.analizar(
        datos,
        "recibido.silice",
        caso=caso,
        instalacion=bd,
        carpeta_paquetes=carpeta,
        revisor=f"{login.title()} <{login}>",
        login=login,
        ahora=RECIBIDO,
        servicios=revision.Servicios,
    )


def test_analizar_un_paquete_firmado_lo_recibe_lo_reaudita_y_lo_compara(mundo) -> None:
    datos = paquete(par=PAR, presupuesto=_documento(), anexos={})
    a = _analizar(mundo, datos)
    assert a.sha_del_archivo == hashlib.sha256(datos).hexdigest()
    assert a.login == "rita"
    assert a.recibido.verificacion.estado == "verificado"
    assert a.reauditoria is not None and a.reauditoria.total_recalculado == TOTAL
    assert a.previa is None and a.diferencia is None  # primera entrega de MIN-001
    assert a.armo == ()
    # los dos eslabones del paquete (004 y 005), con su cambio de cantidad, son nuevos
    assert [c["version"] for c in a.cambios] == ["004", "005"]
    caso, _, carpeta = mundo
    assert caso.scalar(select(paq.paq_recibido.c.huella_archivo)) == a.sha_del_archivo
    assert len(list(carpeta.iterdir())) == 1


def test_analizar_un_paquete_alterado_lo_audita_sin_cambios_que_mostrar(mundo) -> None:
    """Un archivo cambiado tras firmarse se audita igual (S3 §8.3) pero su cadena no se leyó: no
    hay «quién cambió qué». Antes de T7 la pantalla clásica caía aquí con un `TypeError`."""
    from tests.fixtures.paquetes import reempaquetar

    alterado = reempaquetar(
        paquete(par=PAR, presupuesto=_documento(), anexos={}), {"informe.json": b'{"otro":1}'}
    )
    a = _analizar(mundo, alterado)
    assert a.recibido.verificacion.estado == "alterado"
    assert a.reauditoria is not None and a.reauditoria.total_recalculado == TOTAL
    assert a.cambios == ()


def test_un_paquete_que_no_quedo_registrado_no_admite_dictamen(mundo) -> None:
    """`recibir` no registra un alterado sin cadena (paquete_id 0): el dictamen es un error de
    valor con mensaje, no un fallo de la clave foránea de `paq_dictamen`."""
    from aplicacion import revision
    from tests.fixtures.paquetes import reempaquetar

    alterado = reempaquetar(
        paquete(par=PAR, presupuesto=_documento(), anexos={}), {"informe.json": b'{"otro":1}'}
    )
    a = _analizar(mundo, alterado)
    assert a.recibido.paquete_id == 0
    caso, _, _ = mundo
    with pytest.raises(ValueError, match="no admite dictamen"):
        revision.dictaminar(
            caso,
            a.recibido,
            resultado="rechazado",
            notas="alterado",
            revisor="Rita <rita>",
            ahora=RECIBIDO,
            armo=False,
        )
    assert caso.execute(select(paq.paq_dictamen)).all() == []


def test_si_otra_peticion_registro_el_mismo_archivo_se_relee_lo_registrado(
    mundo, monkeypatch
) -> None:
    """Carrera de dos recepciones del mismo archivo: entre la búsqueda por huella y la inserción,
    la otra lo registró (UNIQUE de `huella_archivo`). Se relee y se trata como ya recibido."""
    datos = paquete(par=PAR, presupuesto=_documento(), anexos={})
    primera = _analizar(mundo, datos)
    real = paq.buscar_por_huella
    vistas: list[str] = []

    def ciega_una_vez(sesion, huella):
        vistas.append(huella)
        return None if len(vistas) == 1 else real(sesion, huella)

    monkeypatch.setattr(paq, "buscar_por_huella", ciega_una_vez)
    segunda = _analizar(mundo, datos)
    assert segunda.recibido.ya_recibido
    assert segunda.recibido.paquete_id == primera.recibido.paquete_id
    caso, _, _ = mundo
    assert len(caso.execute(select(paq.paq_recibido)).all()) == 1


def test_analizar_un_archivo_rechazado_no_reaudita_ni_guarda_nada(mundo) -> None:
    a = _analizar(mundo, b"esto no es un zip")
    assert a.recibido.verificacion.estado == "rechazado"
    assert a.reauditoria is None and a.cambios == () and a.armo == ()
    _, _, carpeta = mundo
    assert not carpeta.exists()


def test_analizar_dice_quien_armo_si_el_emisor_es_quien_revisa(mundo) -> None:
    caso, bd, _ = mundo
    empresas.guardar_empresa_propia(bd, EMPRESA, "J-00000000-0", "", "admin", AHORA)
    bd.commit()
    sin_firma = paquete(par=None, presupuesto=_documento(), anexos={})
    assert _analizar(mundo, sin_firma, login="ana").armo == ("004", "005")  # «Ana <ana>»
    otro = con_manifiesto(sin_firma, usuario_emisor="Rita <rita>")
    assert _analizar(mundo, otro, login="rita").armo == ("005",)


def test_contrastar_con_una_lista_del_revisor_revalora_en_memoria(mundo) -> None:
    """Memoria a mano: con la arena a 16,00 (y lo demás sin pareja, a su precio) el PU es
    (16 + 0,8875 + 18,1875) x 1,15 x 1,10 = 44,369875 y el total 20 x 44,369875 = 887,3975;
    Δ = 887,3975 - 836,7975 = 50,60, todo por precio."""
    from aplicacion import revision

    caso, _, _ = mundo
    arena = caso.scalars(select(models.Insumo).where(models.Insumo.codigo == "MAT-001")).one()
    mia = models.ListaPrecios(
        nombre="Lista del revisor", moneda="USD", fecha_vigencia=date(2026, 11, 5), origen=""
    )
    mia.precios.append(models.PrecioInsumo(insumo=arena, precio=Decimal("16.00")))
    caso.add(mia)
    caso.commit()
    assert [x.nombre for x in revision.listas_del_caso(caso)] == [
        "Lista del revisor",
        "Lista de prueba",
    ]  # la más nueva primero, como el selector de la pantalla
    a = _analizar(mundo, paquete(par=PAR, presupuesto=_documento(), anexos={}))
    diferencia, revalorado = revision.contra_mi_lista(caso, a.reauditoria.documento, mia)
    assert (diferencia.total_1, diferencia.total_2) == (TOTAL, Decimal("887.3975"))
    assert diferencia.desvio_precio == Decimal("50.60") and diferencia.desvio_cantidad == 0
    assert revision.texto_por_cantidad_y_precio(diferencia) == (
        "Por cantidad: 0.00. Por precio: 50.60."
    )
    assert revision.texto_de_no_contrastables(revalorado) == (
        "No contrastables (no están en mi lista; no suman): EQU-001, MO-001"
    )


def test_el_texto_de_las_reglas_corridas_lleva_la_fecha_de_emision(mundo) -> None:
    from aplicacion import revision

    a = _analizar(mundo, paquete(par=PAR, presupuesto=_documento(), anexos={}))
    assert revision.texto_de_reglas(a.reauditoria) == (
        "Reglas corridas a la fecha de emisión (2026-11-10): R1-R7, R11-R12."
    )


def test_los_avisos_visibles_no_repiten_el_ya_recibido_que_dice_el_banner(mundo) -> None:
    from aplicacion import revision

    datos = paquete(par=PAR, presupuesto=_documento(), anexos={}, destinatario="Obra Norte")
    _analizar(mundo, datos)
    otra = _analizar(mundo, datos)
    assert any(x.startswith("Ya recibió este mismo paquete") for x in otra.recibido.avisos)
    assert revision.avisos_visibles(otra.recibido) == ["Este paquete se emitió para Obra Norte."]


def test_la_ayuda_de_registro_solo_va_con_una_empresa_no_registrada(tmp_path: Path) -> None:
    from aplicacion import revision
    from paquete.verificar import verificar

    datos = paquete(par=PAR, presupuesto=_documento(), anexos={})
    ajena = verificar(datos, buscar_empresa=lambda _h: None, recibido_en=RECIBIDO)
    assert ajena.motivo == "empresa_no_registrada"
    assert revision.ayuda_de_registro(ajena) == revision.AYUDA_EMPRESA_NO_REGISTRADA
    sin_firma = verificar(
        paquete(par=None, presupuesto=_documento(), anexos={}),
        buscar_empresa=lambda _h: None,
        recibido_en=RECIBIDO,
    )
    assert revision.ayuda_de_registro(sin_firma) is None


# --- VB-19: la fecha se formatea EN SU RANURA, nunca con una busqueda sobre el texto -----------


def _recibido(**campos):
    from types import SimpleNamespace

    manifiesto = {"codigo": "2026-11-10", "emitido": "2026-11-10T08:00:00"}
    base = dict(
        verificacion=SimpleNamespace(manifiesto=manifiesto),
        ya_recibido=False,
        ya_recibido_el="",
        ultima_recibida="",
    )
    return SimpleNamespace(**{**base, **campos})


def test_fecha_es_pasa_la_fecha_iso_a_dd_mm_aaaa_y_deja_lo_que_no_lo_es() -> None:
    from aplicacion import revision

    assert revision.fecha_es("2026-11-10") == "10/11/2026"
    assert revision.fecha_es("V2026-01-01") == "V2026-01-01"
    assert revision.fecha_es("") == ""


def test_el_banner_de_version_formatea_solo_las_ranuras_de_fecha() -> None:
    from aplicacion import revision

    primera = _recibido()
    assert revision.banner_de_version(primera) == (
        "Versión 2026-11-10 del 2026-11-10; es la primera que recibe de este proyecto."
    )  # por omision, ISO como la clasica
    assert revision.banner_de_version(primera, fecha=revision.fecha_es) == (
        "Versión 2026-11-10 del 10/11/2026; es la primera que recibe de este proyecto."
    )  # el codigo con forma de fecha queda intacto
    otra = _recibido(ya_recibido=True, ya_recibido_el="2026-11-12")
    assert revision.banner_de_version(otra, fecha=revision.fecha_es).endswith(
        "ya recibió este mismo paquete el 12/11/2026."
    )
    previa = _recibido(ultima_recibida="versión 2026-01-01 del 2026-11-03")
    assert revision.banner_de_version(previa, fecha=revision.fecha_es).endswith(
        "la última que usted recibió de este proyecto: versión 2026-01-01 del 03/11/2026."
    )


def test_la_declaracion_retroactiva_formatea_la_fecha_y_no_el_codigo() -> None:
    from aplicacion import revision

    cadena = {
        "eslabones": [
            {"tipo": "retroactivo", "codigo": "2026-01-01", "fecha_hora": "2026-11-05T09:00"}
        ]
    }
    texto = revision.declaracion_retroactiva(cadena, fecha=revision.fecha_es)
    assert texto.startswith("Versión 2026-01-01 ") and " el 05/11/2026:" in texto


def test_el_texto_de_dictamen_formatea_la_fecha_y_no_el_login() -> None:
    from aplicacion import revision

    fila = {
        "resultado": "conforme",
        "usuario": "rita_2026-01-15",
        "fecha": datetime(2026, 11, 12, 10, 5, 59),
        "estado_verificacion": "verificado",
    }
    assert revision.texto_de_dictamen(fila, fecha=revision.fecha_es) == (
        "Dictamen anterior: conforme · rita_2026-01-15 · 12/11/2026 10:05 · "
        "verificación entonces: verificado"
    )


def test_la_ultima_recibida_solo_se_formatea_si_la_cola_es_un_dia_iso() -> None:
    from aplicacion import revision

    rara = _recibido(ultima_recibida="versión 2026-01-01 de otro modo 12345")
    assert revision.banner_de_version(rara, fecha=revision.fecha_es).endswith(
        "de este proyecto: versión 2026-01-01 de otro modo 12345."
    )
    corta = _recibido(ultima_recibida="versión 004 del 2026-1")
    assert revision.banner_de_version(corta, fecha=revision.fecha_es).endswith(
        "de este proyecto: versión 004 del 2026-1."
    )
