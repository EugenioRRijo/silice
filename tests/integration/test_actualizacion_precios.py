"""UC‑02 de extremo a extremo: una lista de precios nueva sobre el presupuesto guardado (I1).

Flujo completo: SQLite sembrada → presupuesto 001 elaborado, auditado y guardado →
`crear_lista_desde_archivo` con la muestra `data/samples/precios/lista_2026-06-01.csv` →
`actualizar_precios` produce el presupuesto 002, registra los `CambioPrecio` con su
`IncidenciaCambio` y devuelve el comparativo.

Los importes esperados son exactos (`Decimal`, sin tolerancia): la muestra solo sube el cemento
(15 → 18 USD/saco) y la arena (30 → 33 USD/m3), ambos exclusivos del vaciado de concreto, así que
cuatro de los cinco renglones deben quedar idénticos y el quinto subir una cantidad calculable a
mano. Es la comprobación que exige RF‑12 y RF‑13 de docs/ERS.md.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import select

from core import models
from core.budget import (
    COLUMNAS_COMPARATIVO,
    actualizar_precios,
    cargar_presupuesto,
    descartar_version,
    elaborar,
    generar_curva,
    generar_presupuesto,
    guardar_presupuesto,
    plan_secuencial,
)
from core.budget import actualizacion as modulo_actualizacion
from core.catalog import (
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_lista_desde_archivo,
    crear_motor,
    leer_lista_precios,
    registrar_cambios,
)
from core.catalog.precios import leer_tabla
from scripts.seed import NOMBRE_PROYECTO, sembrar
from tests.fixtures import apu_linea_base as linea_base
from tests.fixtures.actualizacion_uc02 import (
    ARENA,
    CEMENTO,
    INCREMENTO_PU_CONCRETO,
    INCREMENTO_TOTAL,
    PRECIOS_NUEVOS,
    VARIACIONES,
)
from tests.fixtures.computo_auditado import items_auditados

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "data" / "samples" / "precios" / "lista_2026-06-01.csv"

FECHA_NUEVA = date(2026, 6, 1)
CODIGO_NUEVO = "002"
NOMBRE_LISTA_NUEVA = "Lista de precios 01/06/2026"
CONCRETO = linea_base.APU_CONCRETO.codigo_partida
CODIGOS = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]

# Variación del precio unitario del concreto, en porcentaje y con cuatro decimales.
VARIACION_PU_CONCRETO_PCT = Decimal("12.4342")


# ---------------------------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def presupuesto_001(sesion):
    """El presupuesto 001 de la línea base elaborado, auditado, con curva y guardado."""
    catalogo = Catalogo(sesion)
    items = items_auditados()
    composiciones = catalogo.composiciones(CODIGOS, fecha=linea_base.FECHA_LINEA_BASE)
    argumentos = dict(
        codigo=linea_base.CODIGO_PRESUPUESTO,
        fecha=linea_base.FECHA_LINEA_BASE,
        moneda=linea_base.MONEDA,
    )
    borrador = generar_presupuesto(
        items, composiciones, linea_base.PARAMETROS_LINEA_BASE, **argumentos
    )
    resultado = elaborar(
        items,
        composiciones,
        linea_base.PARAMETROS_LINEA_BASE,
        plan=plan_secuencial(borrador),
        **argumentos,
    )
    guardar_presupuesto(
        sesion,
        resultado.presupuesto,
        resultado.informe,
        proyecto=sembrar(sesion),
        lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
        parametros=linea_base.PARAMETROS_LINEA_BASE,
    )
    return resultado


@pytest.fixture
def lista_nueva(sesion, presupuesto_001):
    """La lista del 01/06/2026 creada a partir de la muestra del repositorio."""
    return crear_lista_desde_archivo(
        sesion,
        MUESTRA,
        nombre=NOMBRE_LISTA_NUEVA,
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
        origen=MUESTRA.name,
    )


@pytest.fixture
def actualizacion(sesion, presupuesto_001, lista_nueva):
    """El resultado de UC‑02: presupuesto 002 con su informe y el comparativo."""
    return actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_nueva.lista,
        CODIGO_NUEVO,
        plan=plan_secuencial(presupuesto_001.presupuesto),
    )


def _por_codigo(presupuesto):
    """Los renglones del presupuesto indexados por código de partida."""
    return {partida.item.codigo_partida: partida for partida in presupuesto.partidas}


# ---------------------------------------------------------------------------------------------
# Lectura del archivo y creación de la lista
# ---------------------------------------------------------------------------------------------


def test_leer_lista_precios_devuelve_decimales_exactos():
    leidos = {precio.descripcion: precio for precio in leer_lista_precios(MUESTRA)}

    assert leidos[CEMENTO].precio == PRECIOS_NUEVOS[CEMENTO]
    assert leidos[ARENA].precio == PRECIOS_NUEVOS[ARENA]
    assert all(isinstance(precio.precio, Decimal) for precio in leidos.values())
    assert leidos[CEMENTO].tipo is models.TipoInsumo.MATERIAL
    assert leidos[CEMENTO].unidad == "saco"
    # Equipos y mano de obra no llevan unidad en el catálogo: la columna va vacía.
    assert leidos["Retroexcavadora"].tipo is models.TipoInsumo.EQUIPO
    assert leidos["Retroexcavadora"].unidad is None


def test_leer_lista_precios_xlsx_lee_decimales_exactos(tmp_path):
    """El XLSX no puede pasar por `float`: 18,10 y 0,10 no son exactos en binario, y el `Decimal`
    debe llegar igual al que se escribio en la celda, no al que produce el motor de Excel al
    analizarla como numero (hallazgo de la ronda de correccion 1; antes de esta correccion la
    lectura no tenia ninguna prueba de integracion con un archivo XLSX real).
    """
    archivo = tmp_path / "lista.xlsx"
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.append(["tipo", "insumo", "unidad", "precio"])
    hoja.append(["material", "Cemento Portland", "saco", 18.10])
    hoja.append(["material", "Arena lavada", "m3", 0.10])
    hoja.append(["equipo", "Retroexcavadora", None, 200])
    libro.save(archivo)

    leidos = {precio.descripcion: precio for precio in leer_lista_precios(archivo)}

    assert leidos["Cemento Portland"].precio == Decimal("18.10")
    assert leidos["Arena lavada"].precio == Decimal("0.10")
    assert leidos["Retroexcavadora"].precio == Decimal("200")
    assert all(isinstance(precio.precio, Decimal) for precio in leidos.values())
    assert leidos["Retroexcavadora"].unidad is None


@pytest.mark.parametrize("precio", ["nan", "Infinity", "-Infinity", "-1"])
def test_leer_lista_precios_rechaza_lo_que_no_es_un_numero_no_negativo(tmp_path, precio):
    """`ValueError` citando archivo y fila, como promete el docstring de `leer_lista_precios`.

    Antes de la corrección solo se cubría el negativo: `Decimal("nan") < 0` lanza
    `decimal.InvalidOperation` (un `ArithmeticError`, no un `ValueError`) fuera del `except` de la
    construcción, y `Decimal("Infinity") < 0` es `False`, así que un precio infinito entraba a la
    lista en silencio (revisión final, ítem 4).
    """
    archivo = tmp_path / "lista.csv"
    archivo.write_text(
        f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},saco,{precio}\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match=r"lista\.csv, fila 2"):
        leer_lista_precios(archivo)


def test_leer_lista_precios_rechaza_un_tipo_desconocido_con_archivo_y_fila(tmp_path):
    """QA H3: el tipo de insumo que no es material, equipo ni mano de obra cita archivo y fila."""
    archivo = tmp_path / "lista.csv"
    archivo.write_text(
        f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},saco,15\nherramienta,Pala,,3\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"lista\.csv, fila 3: tipo de insumo 'herramienta'"):
        leer_lista_precios(archivo)


def test_un_csv_no_tiene_hojas(tmp_path):
    """QA H3: pedir una hoja de un CSV es un error que lo dice, no una lectura silenciosa."""
    archivo = tmp_path / "lista.csv"
    archivo.write_text("tipo,insumo,unidad,precio\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"lista\.csv: un CSV no tiene hojas.*'Insumos'"):
        leer_tabla(archivo, hoja="Insumos")


def test_crear_lista_copia_los_precios_anteriores_y_sobrescribe_los_del_archivo(
    sesion, presupuesto_001, lista_nueva
):
    catalogo = Catalogo(sesion)
    anterior = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    nueva = lista_nueva.lista

    assert lista_nueva.desconocidos == ()
    assert nueva.fecha_vigencia == FECHA_NUEVA
    assert catalogo.lista_vigente(FECHA_NUEVA) is nueva
    assert len(nueva.precios) == len(anterior.precios)

    precios = {precio.insumo.descripcion: precio.precio for precio in nueva.precios}
    assert precios[CEMENTO] == PRECIOS_NUEVOS[CEMENTO]
    assert precios[ARENA] == PRECIOS_NUEVOS[ARENA]
    assert precios["Piedra picada"] == linea_base.precio_de_insumo("Piedra picada")
    assert precios["Retroexcavadora"] == linea_base.precio_de_insumo("Retroexcavadora")


def test_crear_lista_reporta_los_insumos_desconocidos_sin_crearlos(
    sesion, presupuesto_001, tmp_path
):
    archivo = tmp_path / "con_desconocido.csv"
    archivo.write_text(
        f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},saco,18\nmaterial,Cemento blanco,saco,25\n",
        encoding="utf-8",
    )
    insumos_antes = len(Catalogo(sesion).insumos())

    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=NOMBRE_LISTA_NUEVA,
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
        origen=archivo.name,
    )

    assert [precio.descripcion for precio in resumen.desconocidos] == ["Cemento blanco"]
    assert len(Catalogo(sesion).insumos()) == insumos_antes
    precios = {precio.insumo.descripcion: precio.precio for precio in resumen.lista.precios}
    assert precios[CEMENTO] == PRECIOS_NUEVOS[CEMENTO]
    assert "Cemento blanco" not in precios


def test_crear_lista_actualiza_todas_las_variantes_homonimas(sesion, tmp_path):
    """Una fila del archivo actualiza TODAS las variantes de su (tipo, descripcion, unidad).

    El catalogo sembrado trae "Cinta metrica" en dos variantes con distinto factor de
    depreciacion (`EQU-007` y `EQU-007-B`, docs/modelo_datos.md §6): la politica declarada en el
    docstring de `core.catalog.precios` (seccion "Homonimos") es que el archivo declara un precio
    por insumo, sin distinguir variantes, y las actualiza a todas. Sin esta prueba (hallazgo de la
    ronda de correccion 1) la politica estaba implementada pero ninguna prueba la fijaba.
    """
    descripcion = "Cinta métrica"
    catalogo = Catalogo(sesion)
    variantes_antes = {
        insumo.codigo for insumo in catalogo.insumos() if insumo.descripcion == descripcion
    }
    assert len(variantes_antes) == 2, "la linea base debe traer dos variantes de Cinta metrica"

    archivo = tmp_path / "cinta_metrica.csv"
    archivo.write_text(f"tipo,insumo,unidad,precio\nequipo,{descripcion},,50\n", encoding="utf-8")

    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=NOMBRE_LISTA_NUEVA,
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
        origen=archivo.name,
    )

    precios_actualizados = {
        precio.insumo.codigo: precio.precio
        for precio in resumen.lista.precios
        if precio.insumo.codigo in variantes_antes
    }
    assert precios_actualizados.keys() == variantes_antes
    assert all(precio == Decimal("50") for precio in precios_actualizados.values())


def test_un_precio_anterior_nulo_no_hace_fallar_el_registro_de_cambios(sesion, tmp_path):
    """INV‑004: un precio 0 es válido (`leer_lista_precios` acepta no negativos), así que la
    variación con base nula no puede lanzar `DivisionByZero` en medio de UC‑02.
    """
    donado = tmp_path / "cemento_donado.csv"
    donado.write_text(f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},saco,0\n", encoding="utf-8")
    intermedia = crear_lista_desde_archivo(
        sesion,
        donado,
        nombre="Lista con cemento donado",
        moneda=linea_base.MONEDA,
        fecha_vigencia=date(2026, 5, 15),
    ).lista
    nueva = crear_lista_desde_archivo(
        sesion, MUESTRA, nombre=NOMBRE_LISTA_NUEVA, moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
    ).lista

    cambios = {
        cambio.insumo.descripcion: cambio
        for cambio in registrar_cambios(sesion, intermedia, nueva)
    }

    assert cambios[CEMENTO].precio_anterior == Decimal("0")
    assert cambios[CEMENTO].variacion == Decimal("0")
    assert cambios[ARENA].variacion == VARIACIONES[ARENA]


# ---------------------------------------------------------------------------------------------
# Actualización del presupuesto
# ---------------------------------------------------------------------------------------------


def test_actualizar_precios_solo_revalora_el_concreto(presupuesto_001, actualizacion):
    nuevo, _ = actualizacion
    anteriores = _por_codigo(presupuesto_001.presupuesto)
    nuevos = _por_codigo(nuevo.presupuesto)

    assert nuevo.presupuesto.codigo == CODIGO_NUEVO
    assert nuevo.presupuesto.fecha == FECHA_NUEVA
    for codigo in CODIGOS:
        esperado = anteriores[codigo].resultado.precio_unitario
        if codigo == CONCRETO:
            esperado += INCREMENTO_PU_CONCRETO
        assert nuevos[codigo].resultado.precio_unitario == esperado, codigo
        assert nuevos[codigo].item.cantidad == anteriores[codigo].item.cantidad

    assert nuevos[CONCRETO].total == anteriores[CONCRETO].total + INCREMENTO_TOTAL
    assert nuevo.presupuesto.total == presupuesto_001.presupuesto.total + INCREMENTO_TOTAL


def test_registra_un_cambio_de_precio_por_insumo_afectado(sesion, actualizacion):
    cambios = sesion.scalars(select(models.CambioPrecio)).all()

    assert len(cambios) == 2
    por_insumo = {cambio.insumo.descripcion: cambio for cambio in cambios}
    assert set(por_insumo) == set(PRECIOS_NUEVOS)
    for descripcion, cambio in por_insumo.items():
        assert cambio.precio_nuevo == PRECIOS_NUEVOS[descripcion]
        assert cambio.variacion == VARIACIONES[descripcion]
        assert cambio.fecha == FECHA_NUEVA
        assert cambio.lista_nueva.nombre == NOMBRE_LISTA_NUEVA
    assert por_insumo[CEMENTO].precio_anterior == linea_base.precio_de_insumo(CEMENTO)
    assert por_insumo[ARENA].precio_anterior == linea_base.precio_de_insumo(ARENA)


def test_registra_la_incidencia_de_cada_cambio_en_el_concreto(
    sesion, presupuesto_001, actualizacion
):
    incidencias = sesion.scalars(select(models.IncidenciaCambio)).all()
    anterior = _por_codigo(presupuesto_001.presupuesto)[CONCRETO].resultado.precio_unitario

    assert len(incidencias) == 2
    assert {incidencia.partida.codigo for incidencia in incidencias} == {CONCRETO}
    for incidencia in incidencias:
        assert incidencia.precio_unitario_anterior == anterior
        assert incidencia.precio_unitario_nuevo == anterior + INCREMENTO_PU_CONCRETO
        assert incidencia.variacion == INCREMENTO_PU_CONCRETO / anterior
        assert incidencia.cambio.insumo.descripcion in PRECIOS_NUEVOS


def test_repetir_uc02_con_el_mismo_par_de_listas_no_duplica_el_historial(
    sesion, presupuesto_001, lista_nueva, actualizacion
):
    """`registrar_cambios` ya era idempotente; `_registrar_incidencias` no lo era.

    Un segundo `actualizar_precios` con el mismo par de listas duplicaba las `IncidenciaCambio`,
    la tabla que alimentará el módulo predictivo de I6 (revisión final, ítem 8).
    """
    cambios = len(sesion.scalars(select(models.CambioPrecio)).all())
    incidencias = len(sesion.scalars(select(models.IncidenciaCambio)).all())

    actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_nueva.lista,
        "003",
        plan=plan_secuencial(presupuesto_001.presupuesto),
    )

    assert len(sesion.scalars(select(models.CambioPrecio)).all()) == cambios
    assert len(sesion.scalars(select(models.IncidenciaCambio)).all()) == incidencias


@pytest.fixture
def cemento_en_dos_lineas(sesion):
    """El vaciado de concreto con el cemento repetido en dos líneas de su composición.

    Nada lo prohíbe en el modelo (`composicion_apu` no tiene clave única por partida e insumo) y
    hace que el `join` de `_partidas_por_insumo` devuelva la misma partida dos veces.
    """
    partida = sesion.scalars(select(models.Partida).where(models.Partida.codigo == CONCRETO)).one()
    linea = sesion.scalars(
        select(models.ComposicionAPU)
        .join(models.Insumo)
        .where(
            models.ComposicionAPU.partida_id == partida.id,
            models.Insumo.descripcion == CEMENTO,
        )
    ).one()
    sesion.add(
        models.ComposicionAPU(
            partida_id=partida.id,
            insumo_id=linea.insumo_id,
            cantidad=Decimal("0.5"),
            orden=linea.orden + 100,
        )
    )
    sesion.flush()
    return partida


def test_un_insumo_repetido_en_una_partida_registra_una_sola_incidencia(
    sesion, cemento_en_dos_lineas, presupuesto_001, lista_nueva
):
    """Una incidencia por par (cambio de precio, partida), aunque el insumo se repita."""
    actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_nueva.lista,
        CODIGO_NUEVO,
        plan=plan_secuencial(presupuesto_001.presupuesto),
    )

    incidencias = sesion.scalars(select(models.IncidenciaCambio)).all()

    assert len(incidencias) == 2
    assert len({(i.cambio_id, i.partida_id) for i in incidencias}) == 2


def test_el_presupuesto_anterior_sigue_reconstruyendose_a_su_fecha(
    sesion, presupuesto_001, actualizacion
):
    cargado = cargar_presupuesto(
        sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, Catalogo(sesion)
    )

    assert cargado == presupuesto_001.presupuesto
    assert cargado.total == presupuesto_001.presupuesto.total


def test_el_presupuesto_nuevo_queda_persistido_con_su_lista(sesion, lista_nueva, actualizacion):
    nuevo, _ = actualizacion
    cargado = cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(sesion))
    modelo = sesion.scalars(
        select(models.Presupuesto).where(models.Presupuesto.codigo == CODIGO_NUEVO)
    ).one()

    assert cargado == nuevo.presupuesto
    assert modelo.lista_precios is lista_nueva.lista
    assert modelo.fcas == linea_base.PARAMETROS_LINEA_BASE.fcas
    assert modelo.utilidad == linea_base.PARAMETROS_LINEA_BASE.utilidad
    assert len(modelo.hallazgos) == len(nuevo.informe.hallazgos)


def test_uc02_exige_composicion_para_todo_renglon_antes_de_guardar(
    sesion, presupuesto_001, lista_nueva, monkeypatch
):
    """INV‑013 no relaja UC‑02: la precondición corre antes de elaborar y de guardar.

    Las composiciones de `actualizar_precios` salen del catálogo para todos los códigos del
    presupuesto, así que un faltante no se puede provocar con datos: se provoca quitando el
    concreto justo en la precondición, y se comprueba que no quedó ninguna versión guardada.
    """
    original = modulo_actualizacion.exigir_composiciones

    def sin_concreto(items, composiciones):
        recortadas = {codigo: apu for codigo, apu in composiciones.items() if codigo != CONCRETO}
        original(items, recortadas)

    monkeypatch.setattr(modulo_actualizacion, "exigir_composiciones", sin_concreto)

    with pytest.raises(ValueError, match=CONCRETO):
        actualizar_precios(
            sesion,
            NOMBRE_PROYECTO,
            linea_base.CODIGO_PRESUPUESTO,
            lista_nueva.lista,
            CODIGO_NUEVO,
            plan=plan_secuencial,
        )
    with pytest.raises(KeyError, match=CODIGO_NUEVO):
        cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(sesion))


def test_uc02_acepta_el_plan_como_funcion_del_presupuesto_valorado(
    sesion, presupuesto_001, lista_nueva
):
    """INV‑069: `actualizar_precios` acepta el mismo `GeneradorPlan` que `elaborar`. El plan
    secuencial no depende de los montos, así que calcularlo sobre la versión nueva da la misma
    curva que calcularlo sobre la anterior, como hacían los llamadores."""
    nuevo, _ = actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_nueva.lista,
        CODIGO_NUEVO,
        plan=plan_secuencial,
    )

    esperada = generar_curva(nuevo.presupuesto, plan_secuencial(presupuesto_001.presupuesto))
    assert nuevo.presupuesto.curva == tuple(esperada)
    assert nuevo.presupuesto.total_curva == nuevo.presupuesto.total


def _estructura(composicion):
    """Lo que UC‑02 no puede tocar: rendimiento, líneas, cantidades, depreciaciones y
    modalidades."""
    return (
        composicion.rendimiento,
        tuple(
            (linea.descripcion, linea.unidad, linea.cantidad) for linea in composicion.materiales
        ),
        tuple(
            (linea.descripcion, linea.cantidad, linea.depreciacion) for linea in composicion.equipos
        ),
        tuple(
            (linea.descripcion, linea.cantidad, linea.modalidad) for linea in composicion.mano_obra
        ),
    )


def test_uc02_no_edita_ninguna_composicion(sesion, presupuesto_001, lista_nueva):
    """RF‑11 (INV‑014): las composiciones quedan idénticas; solo cambia la lista que las valora."""
    catalogo = Catalogo(sesion)
    antes = {
        codigo: catalogo.composicion(codigo, fecha=linea_base.FECHA_LINEA_BASE)
        for codigo in CODIGOS
    }
    lineas_antes = len(sesion.scalars(select(models.ComposicionAPU)).all())

    actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        linea_base.CODIGO_PRESUPUESTO,
        lista_nueva.lista,
        CODIGO_NUEVO,
        plan=plan_secuencial(presupuesto_001.presupuesto),
    )

    assert len(sesion.scalars(select(models.ComposicionAPU)).all()) == lineas_antes
    for codigo in CODIGOS:
        despues = catalogo.composicion(codigo, fecha=linea_base.FECHA_LINEA_BASE)
        assert despues == antes[codigo], codigo
        con_lista_nueva = catalogo.composicion(codigo, fecha=FECHA_NUEVA)
        assert _estructura(con_lista_nueva) == _estructura(antes[codigo]), codigo


def test_los_cambios_de_precio_se_releen_tras_cerrar_la_sesion(tmp_path):
    """RF‑12 (INV‑014): un registro por insumo, recuperable desde otra sesión y otro motor."""
    url = f"sqlite:///{(tmp_path / 'uc02.db').as_posix()}"
    motor = crear_motor(url)
    try:
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            proyecto = sembrar(sesion)
            catalogo = Catalogo(sesion)
            resultado = elaborar(
                items_auditados(),
                catalogo.composiciones(CODIGOS, fecha=linea_base.FECHA_LINEA_BASE),
                linea_base.PARAMETROS_LINEA_BASE,
                codigo=linea_base.CODIGO_PRESUPUESTO,
                fecha=linea_base.FECHA_LINEA_BASE,
                moneda=linea_base.MONEDA,
                plan=plan_secuencial,
            )
            guardar_presupuesto(
                sesion,
                resultado.presupuesto,
                resultado.informe,
                proyecto=proyecto,
                lista=catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE),
                parametros=linea_base.PARAMETROS_LINEA_BASE,
            )
            sesion.commit()
            nueva = crear_lista_desde_archivo(
                sesion,
                MUESTRA,
                nombre=NOMBRE_LISTA_NUEVA,
                moneda=linea_base.MONEDA,
                fecha_vigencia=FECHA_NUEVA,
            )
            actualizar_precios(
                sesion,
                NOMBRE_PROYECTO,
                linea_base.CODIGO_PRESUPUESTO,
                nueva.lista,
                CODIGO_NUEVO,
                plan=plan_secuencial(resultado.presupuesto),
            )
            sesion.commit()
    finally:
        motor.dispose()

    motor = crear_motor(url)
    try:
        with abrir_sesion(motor) as sesion:
            filas = list(sesion.scalars(select(models.CambioPrecio)))
            cambios = {cambio.insumo.descripcion: cambio for cambio in filas}
            assert set(cambios) == set(PRECIOS_NUEVOS)
            assert len(filas) == len(PRECIOS_NUEVOS)
            for descripcion, cambio in cambios.items():
                assert cambio.precio_anterior == linea_base.precio_de_insumo(descripcion)
                assert cambio.precio_nuevo == PRECIOS_NUEVOS[descripcion]
                assert cambio.variacion == VARIACIONES[descripcion]
                assert cambio.fecha == FECHA_NUEVA
                assert {i.partida.codigo for i in cambio.incidencias} == {CONCRETO}
    finally:
        motor.dispose()


def test_una_fila_con_unidad_no_equivalente_se_rechaza_y_las_demas_se_procesan(
    sesion, presupuesto_001, tmp_path
):
    """UC‑02, flujo 2b (INV‑015): la fila se rechaza y se reporta en `desconocidos`, el insumo
    conserva su precio anterior, y la fila con una grafía equivalente (m³ ≡ m3) se procesa."""
    archivo = tmp_path / "unidades.csv"
    archivo.write_text(
        f"tipo,insumo,unidad,precio\nmaterial,{CEMENTO},m3,99\nmaterial,{ARENA},m³,33\n",
        encoding="utf-8",
    )

    resumen = crear_lista_desde_archivo(
        sesion,
        archivo,
        nombre=NOMBRE_LISTA_NUEVA,
        moneda=linea_base.MONEDA,
        fecha_vigencia=FECHA_NUEVA,
    )

    assert [(p.descripcion, p.unidad) for p in resumen.desconocidos] == [(CEMENTO, "m3")]
    precios = {precio.insumo.descripcion: precio.precio for precio in resumen.lista.precios}
    assert precios[CEMENTO] == linea_base.precio_de_insumo(CEMENTO)
    assert precios[ARENA] == PRECIOS_NUEVOS[ARENA]


# ---------------------------------------------------------------------------------------------
# Comparativo e informe
# ---------------------------------------------------------------------------------------------


def test_el_comparativo_suma_los_totales(presupuesto_001, actualizacion):
    nuevo, comparativo = actualizacion
    tabla = comparativo.tabla

    assert list(tabla.columns) == list(COLUMNAS_COMPARATIVO)
    assert len(tabla.index) == len(CODIGOS)
    assert comparativo.insumos_afectados == len(PRECIOS_NUEVOS)
    assert comparativo.total_anterior == presupuesto_001.presupuesto.total
    assert comparativo.total_nuevo == nuevo.presupuesto.total
    assert comparativo.total_nuevo == comparativo.total_anterior + INCREMENTO_TOTAL
    assert comparativo.variacion == INCREMENTO_TOTAL
    assert sum(tabla["total_nuevo"], Decimal(0)) == comparativo.total_nuevo
    assert sum(tabla["total_anterior"], Decimal(0)) == comparativo.total_anterior
    # La incidencia de cada partida es su aporte a la variación del presupuesto: suman la global.
    assert sum(tabla["incidencia_pct"], Decimal(0)) == comparativo.variacion_pct


def test_el_comparativo_detalla_la_partida_que_cambio(presupuesto_001, actualizacion):
    _, comparativo = actualizacion
    filas = {fila["codigo_partida"]: fila for fila in comparativo.tabla.to_dict("records")}
    anterior = _por_codigo(presupuesto_001.presupuesto)[CONCRETO]
    concreto = filas[CONCRETO]

    assert all(isinstance(fila["pu_nuevo"], Decimal) for fila in filas.values())
    assert concreto["descripcion"] == anterior.item.descripcion
    assert concreto["cantidad"] == anterior.item.cantidad
    assert concreto["pu_anterior"] == anterior.resultado.precio_unitario
    assert concreto["pu_nuevo"] == anterior.resultado.precio_unitario + INCREMENTO_PU_CONCRETO
    assert round(concreto["variacion_pct"], 4) == VARIACION_PU_CONCRETO_PCT
    assert concreto["total_nuevo"] - concreto["total_anterior"] == INCREMENTO_TOTAL
    for codigo in CODIGOS:
        if codigo != CONCRETO:
            assert filas[codigo]["variacion_pct"] == Decimal(0), codigo
            assert filas[codigo]["incidencia_pct"] == Decimal(0), codigo


def test_el_presupuesto_nuevo_trae_su_informe_de_auditoria(actualizacion):
    nuevo, _ = actualizacion

    assert nuevo.informe.codigo_presupuesto == CODIGO_NUEVO
    assert nuevo.informe.hallazgos
    assert f"presupuesto {CODIGO_NUEVO}" in nuevo.informe.a_markdown()
    # Con plan de trabajo la curva del presupuesto nuevo cierra en su total (regla R2).
    assert nuevo.presupuesto.total_curva == nuevo.presupuesto.total


# ---------------------------------------------------------------------------------------------
# Consulta consolidada del historial (hallazgo menor diferido de la bitacora F.1)
# ---------------------------------------------------------------------------------------------


def test_cambios_precio_consulta_consolidada_con_filtros(sesion, actualizacion):
    """`core.catalog.cambios_precio` es la unica consulta del historial de `CambioPrecio`:
    `api/rutas/listas.py` y `ui/paginas/historico.py` la reproducian por separado (DRY).
    Orden estable (fecha, id); filtros por descripcion exacta y rango de fechas inclusivo.
    """
    from core.catalog import cambios_precio

    todos = cambios_precio(sesion)
    assert {cambio.insumo.descripcion for cambio in todos} == set(PRECIOS_NUEVOS)

    solo_cemento = cambios_precio(sesion, insumo=CEMENTO)
    assert [cambio.insumo.descripcion for cambio in solo_cemento] == [CEMENTO]
    assert solo_cemento[0].precio_nuevo == PRECIOS_NUEVOS[CEMENTO]

    assert cambios_precio(sesion, desde=FECHA_NUEVA) == todos
    assert cambios_precio(sesion, hasta=FECHA_NUEVA) == todos
    assert cambios_precio(sesion, desde=FECHA_NUEVA + timedelta(days=1)) == []
    assert cambios_precio(sesion, hasta=FECHA_NUEVA - timedelta(days=1)) == []


# ---------------------------------------------------------------------------------------------
# UC-02, flujo 7a: descartar la version nueva (INV-015, expediente C3.2)
# ---------------------------------------------------------------------------------------------


def _contar(sesion, entidad) -> int:
    return len(sesion.scalars(select(entidad)).all())


def test_descartar_la_version_nueva_la_marca_y_conserva_el_historial(sesion, actualizacion):
    """`docs/ERS.md:170`: se marca como descartada y el registro de cambios se conserva."""
    nuevo, _ = actualizacion
    sesion.commit()
    incidencias = _contar(sesion, models.IncidenciaCambio)

    marca = descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
    sesion.commit()

    assert marca.presupuesto.codigo == CODIGO_NUEVO
    assert marca.fecha == FECHA_NUEVA
    assert _contar(sesion, models.DescarteVersion) == 1
    # Oraculo: la muestra cambia exactamente dos insumos (tests/fixtures/actualizacion_uc02.py).
    assert _contar(sesion, models.CambioPrecio) == len(PRECIOS_NUEVOS) == 2
    assert _contar(sesion, models.IncidenciaCambio) == incidencias
    # La version descartada sigue siendo un documento que se carga.
    recargado = cargar_presupuesto(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, Catalogo(sesion))
    assert recargado.total == nuevo.presupuesto.total


def test_el_presupuesto_base_nunca_se_descarta(sesion, actualizacion):
    sesion.commit()
    with pytest.raises(ValueError, match="ultima version"):
        descartar_version(sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, FECHA_NUEVA)


def test_sin_version_revalorada_no_hay_nada_que_descartar(sesion, presupuesto_001):
    sesion.commit()
    with pytest.raises(ValueError, match="ultima version"):
        descartar_version(sesion, NOMBRE_PROYECTO, linea_base.CODIGO_PRESUPUESTO, FECHA_NUEVA)


def test_una_version_no_se_descarta_dos_veces(sesion, actualizacion):
    sesion.commit()
    descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
    with pytest.raises(ValueError, match="ya esta descartada"):
        descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)


def test_con_tres_versiones_solo_se_descarta_la_ultima(sesion, actualizacion, lista_nueva):
    """GC3, M‑2 de requisitos: con dos versiones «no es la última» coincide con «es la primera».

    Con tres (001, 002 y 003) la intermedia no es ni la primera ni la última: descartarla da
    `ValueError` y la 003 sí se descarta (fila INV‑015: nunca una versión que no sea la última).
    """
    nuevo, _ = actualizacion
    actualizar_precios(
        sesion,
        NOMBRE_PROYECTO,
        CODIGO_NUEVO,
        lista_nueva.lista,
        "003",
        plan=plan_secuencial(nuevo.presupuesto),
    )
    sesion.commit()

    with pytest.raises(ValueError, match="ultima version"):
        descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
    marca = descartar_version(sesion, NOMBRE_PROYECTO, "003", FECHA_NUEVA)
    assert marca.presupuesto.codigo == "003"
    assert _contar(sesion, models.DescarteVersion) == 1


def test_borrar_una_version_descartada_borra_su_marca_en_cascada(sesion, actualizacion):
    """GC3, M‑2 de pruebas: el `ondelete="CASCADE"` de `descarte_version` se comprueba por
    comportamiento, no solo en el esquema. Con `PRAGMA foreign_keys=ON` (el de `crear_motor`),
    borrar el presupuesto marcado elimina su `DescarteVersion`.
    """
    sesion.commit()
    assert sesion.connection().exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    marca = descartar_version(sesion, NOMBRE_PROYECTO, CODIGO_NUEVO, FECHA_NUEVA)
    sesion.commit()
    assert _contar(sesion, models.DescarteVersion) == 1

    sesion.delete(marca.presupuesto)
    sesion.commit()
    sesion.expunge_all()

    assert _contar(sesion, models.DescarteVersion) == 0
