"""Persistencia y catálogo (Sesión I0.4).

Criterio de cierre: los cinco APU de la línea base se reconstruyen desde SQLite **idénticos** al
fixture `tests/fixtures/apu_linea_base.py`, que es la única copia de esos datos (NORMAS.md §2).
Las comparaciones son por igualdad de dataclass del contrato; no interviene el motor de costos.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from core import contracts, models
from core.catalog import Catalogo, CatalogoIncompleto, abrir_sesion, crear_esquema, crear_motor
from scripts.seed import main, sembrar
from tests.fixtures import apu_linea_base as linea_base

CODIGOS = [apu.codigo_partida for apu in linea_base.APUS_LINEA_BASE]
TABLAS_SEMBRADAS = (
    models.Proyecto,
    models.ListaPrecios,
    models.Partida,
    models.Insumo,
    models.PrecioInsumo,
    models.ComposicionAPU,
    models.Rendimiento,
)


def _contar(sesion, entidad) -> int:
    return sesion.scalar(select(func.count()).select_from(entidad))


def test_seed_carga_cinco_partidas_y_una_lista(sesion):
    assert _contar(sesion, models.Proyecto) == 1
    assert _contar(sesion, models.Partida) == len(linea_base.APUS_LINEA_BASE)
    assert _contar(sesion, models.ListaPrecios) == 1
    assert _contar(sesion, models.Rendimiento) == len(linea_base.APUS_LINEA_BASE)

    lista = sesion.scalars(select(models.ListaPrecios)).one()
    assert lista.moneda == linea_base.MONEDA
    assert lista.fecha_vigencia == linea_base.FECHA_LINEA_BASE

    catalogo = Catalogo(sesion)
    assert [partida.codigo for partida in catalogo.partidas()] == sorted(CODIGOS)
    assert catalogo.partida("LB-01-EXC").dominio == contracts.Dominio.CIVIL
    with pytest.raises(KeyError):
        catalogo.partida("NO-EXISTE")


@pytest.mark.parametrize("apu", linea_base.APUS_LINEA_BASE, ids=CODIGOS)
def test_composicion_reconstruye_cada_apu_identico(sesion, apu):
    assert Catalogo(sesion).composicion(apu.codigo_partida) == apu


def test_precios_se_reconstruyen_a_fecha(sesion):
    catalogo = Catalogo(sesion)
    base = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)

    nueva = models.ListaPrecios(
        nombre="Junio 2026",
        moneda=linea_base.MONEDA,
        fecha_vigencia=date(2026, 6, 1),
        origen="prueba",
    )
    sesion.add(nueva)
    sesion.flush()
    for precio in base.precios:
        subido = precio.insumo.descripcion == "Cemento Portland"
        sesion.add(
            models.PrecioInsumo(
                lista_id=nueva.id,
                insumo_id=precio.insumo_id,
                precio=Decimal("18") if subido else precio.precio,
            )
        )
    sesion.flush()

    def cemento(fecha: date) -> Decimal:
        composicion = catalogo.composicion(linea_base.APU_CONCRETO.codigo_partida, fecha=fecha)
        return next(
            linea.precio
            for linea in composicion.materiales
            if linea.descripcion == "Cemento Portland"
        )

    assert catalogo.lista_vigente(date(2026, 5, 1)).id == base.id
    assert catalogo.lista_vigente(date(2026, 6, 15)).id == nueva.id
    assert cemento(date(2026, 5, 1)) == linea_base.precio_de_insumo("Cemento Portland")
    assert cemento(date(2026, 6, 15)) == Decimal("18")


def test_un_material_sin_unidad_es_un_catalogo_incompleto(sesion):
    """La frontera modelo → contrato debe nombrar el insumo que falta, como sus ramas vecinas.

    `insumo.unidad or ""` mandaba la cadena vacía a `normalizar_unidad`, que lanza el `ValueError`
    del contrato: un error sin código ni descripción, que no dice cuál de los insumos del catálogo
    hay que completar (revisión final, ítem 7).
    """
    codigo_partida = linea_base.APU_CONCRETO.codigo_partida
    linea = sesion.scalars(
        select(models.ComposicionAPU)
        .join(models.Partida, models.Partida.id == models.ComposicionAPU.partida_id)
        .join(models.Insumo, models.Insumo.id == models.ComposicionAPU.insumo_id)
        .where(
            models.Partida.codigo == codigo_partida,
            models.Insumo.tipo == models.TipoInsumo.MATERIAL.value,
        )
        .order_by(models.ComposicionAPU.orden)
    ).first()
    linea.insumo.unidad = None
    sesion.flush()

    with pytest.raises(CatalogoIncompleto) as error:
        Catalogo(sesion).composicion(codigo_partida)

    assert linea.insumo.codigo in str(error.value)
    assert linea.insumo.descripcion in str(error.value)


def test_rendimiento_medido_exige_ejecucion(sesion):
    catalogo = Catalogo(sesion)
    partida = catalogo.partida("LB-01-EXC")

    sesion.add(
        models.Rendimiento(
            partida_id=partida.id,
            valor=Decimal("95"),
            tipo=contracts.TipoRendimiento.MEDIDO.value,
            fecha=date(2026, 7, 1),
            condiciones="sin ejecución declarada",
            ejecucion_id=None,
        )
    )
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()

    sesion.add(
        models.Ejecucion(
            referencia="EJ-001",
            fecha_inicio=date(2026, 7, 1),
            descripcion="Drenaje de la clínica, tramo ejecutado",
        )
    )
    sesion.flush()
    medido = Catalogo(sesion).registrar_rendimiento(
        contracts.Rendimiento(
            codigo_partida="LB-01-EXC",
            valor=Decimal("95"),
            tipo=contracts.TipoRendimiento.MEDIDO,
            fecha=date(2026, 7, 1),
            condiciones="suelo blando",
            referencia_ejecucion="EJ-001",
        )
    )
    sesion.flush()
    assert medido.ejecucion.referencia == "EJ-001"
    assert medido.tipo == contracts.TipoRendimiento.MEDIDO.value

    rendimientos = Catalogo(sesion).rendimientos("LB-01-EXC")
    assert [rendimiento.tipo for rendimiento in rendimientos] == [
        contracts.TipoRendimiento.ESTIMADO,
        contracts.TipoRendimiento.MEDIDO,
    ]
    assert rendimientos[-1].referencia_ejecucion == "EJ-001"


def test_el_vehiculo_es_un_solo_insumo_con_cinco_lineas(sesion):
    """El precio del vehículo es 50,00 en los cinco APU: un solo insumo, cinco líneas.

    Lo que varía es la depreciación (1,00 en cuatro APU y 0,03 en tubería: hallazgo 7), y eso es
    atributo de la línea, no del insumo. Es la contraparte del hallazgo de datos de §6 del modelo.
    """
    insumos = sesion.scalars(
        select(models.Insumo).where(models.Insumo.descripcion == "Vehículo de transporte")
    ).all()
    assert len(insumos) == 1

    lineas = insumos[0].lineas
    assert len(lineas) == len(linea_base.APUS_LINEA_BASE)
    assert {linea.depreciacion for linea in lineas} == {Decimal("1.00"), Decimal("0.03")}


def test_insumos_homonimos_con_precio_distinto_se_cargan_como_variantes(sesion):
    """Hallazgo de datos: cuatro insumos de la línea base cuestan dos cosas distintas el mismo día.

    El esquema no admite dos precios por (lista, insumo), así que la carga crea una variante con la
    misma descripción y un código con sufijo. Candidata a regla R8 (docs/modelo_datos.md §6).
    """
    duplicados = sesion.execute(
        select(models.Insumo.descripcion, func.count(models.Insumo.id))
        .group_by(models.Insumo.tipo, models.Insumo.descripcion)
        .having(func.count(models.Insumo.id) > 1)
    ).all()

    assert {descripcion for descripcion, _ in duplicados} == {
        "Agua",
        "Pala",
        "Cinta métrica",
        "Nivel de mano",
    }
    assert all(cuantos == 2 for _, cuantos in duplicados)

    lista = Catalogo(sesion).lista_vigente()
    for descripcion, _ in duplicados:
        variantes = sesion.scalars(
            select(models.Insumo)
            .where(models.Insumo.descripcion == descripcion)
            .order_by(models.Insumo.id)
        ).all()
        precios = {
            sesion.scalar(
                select(models.PrecioInsumo.precio).where(
                    models.PrecioInsumo.lista_id == lista.id,
                    models.PrecioInsumo.insumo_id == insumo.id,
                )
            )
            for insumo in variantes
        }
        assert len(precios) == 2, f"{descripcion} debería tener dos precios distintos"
        assert variantes[1].codigo.startswith(f"{variantes[0].codigo}-")


def test_sembrar_es_idempotente(sesion):
    antes = {entidad.__name__: _contar(sesion, entidad) for entidad in TABLAS_SEMBRADAS}
    sembrar(sesion)
    despues = {entidad.__name__: _contar(sesion, entidad) for entidad in TABLAS_SEMBRADAS}

    assert antes == despues
    assert Catalogo(sesion).composicion("LB-03-ENC") == linea_base.APU_ENCOFRADO


def test_cargar_composicion_dos_veces_lanza_valueerror(sesion):
    """Recargar una partida ya compuesta duplicaría sus líneas: el catálogo lo rechaza.

    `cargar_composicion` no es reentrante y no debe fingir que lo es: reemplazar en silencio
    dejaría un APU con las líneas repetidas y un segundo rendimiento estimado de la misma fecha.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    lineas_antes = _contar(sesion, models.ComposicionAPU)
    rendimientos_antes = _contar(sesion, models.Rendimiento)

    with pytest.raises(ValueError, match="LB-05-REL"):
        catalogo.cargar_composicion(
            linea_base.APU_RELLENO,
            lista,
            contracts.Dominio.CIVIL,
            linea_base.FECHA_LINEA_BASE,
            "reintento de carga",
        )

    assert _contar(sesion, models.ComposicionAPU) == lineas_antes
    assert _contar(sesion, models.Rendimiento) == rendimientos_antes
    assert Catalogo(sesion).composicion("LB-05-REL") == linea_base.APU_RELLENO


def test_cargar_composicion_sin_condiciones_lanza_valueerror(sesion):
    """RF‑33 alcanza los dos caminos, no solo el de UC‑11 (spec §3.3).

    `reemplazar_composicion` ya lo exigía; crear una partida nueva sin declarar en qué condiciones
    se midió su rendimiento dejaba un ESTIMADO con `condiciones=''`, que es exactamente el valor
    por defecto silencioso que el spec prohíbe.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    nueva = replace(linea_base.APU_RELLENO, codigo_partida="LB-98-NUE")
    lineas_antes = _contar(sesion, models.ComposicionAPU)
    partidas_antes = _contar(sesion, models.Partida)

    with pytest.raises(ValueError, match="RF-33"):
        catalogo.cargar_composicion(
            nueva, lista, contracts.Dominio.CIVIL, linea_base.FECHA_LINEA_BASE, "   "
        )

    assert _contar(sesion, models.ComposicionAPU) == lineas_antes
    assert _contar(sesion, models.Partida) == partidas_antes, (
        "la guarda va antes de crear la partida: un rechazo no puede dejar una partida huérfana"
    )


def test_cargar_composicion_registra_las_condiciones_declaradas(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    nueva = replace(linea_base.APU_RELLENO, codigo_partida="LB-97-NUE")

    catalogo.cargar_composicion(
        nueva,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        "cuadrilla de cuatro, suelo seco",
    )
    sesion.flush()

    registrado = sesion.scalars(
        select(models.Rendimiento)
        .join(models.Partida)
        .where(models.Partida.codigo == "LB-97-NUE")
    ).one()
    assert registrado.condiciones == "cuadrilla de cuatro, suelo seco"
    assert registrado.tipo == contracts.TipoRendimiento.ESTIMADO


def test_reemplazar_composicion_permite_corregir_una_partida(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    corregido = replace(
        linea_base.APU_RELLENO,
        rendimiento=linea_base.APU_RELLENO.rendimiento + Decimal("1"),
    )

    resumen = catalogo.reemplazar_composicion(
        corregido,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        condiciones="cuadrilla ampliada a siete obreros",
    )

    assert resumen.partida.codigo == "LB-05-REL"
    assert Catalogo(sesion).composicion("LB-05-REL") == corregido


def test_reemplazar_conserva_el_rendimiento_anterior_en_el_historico(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    original = linea_base.APU_RELLENO.rendimiento
    corregido = replace(linea_base.APU_RELLENO, rendimiento=original + Decimal("1"))

    catalogo.reemplazar_composicion(
        corregido,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        condiciones="cuadrilla ampliada a siete obreros",
    )

    valores = [rendimiento.valor for rendimiento in catalogo.rendimientos("LB-05-REL")]
    assert original in valores
    assert corregido.rendimiento in valores


def test_reemplazar_una_partida_inexistente_lanza_lookuperror(sesion):
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    inventada = replace(linea_base.APU_RELLENO, codigo_partida="LB-99-NADA")

    with pytest.raises(LookupError, match="LB-99-NADA"):
        catalogo.reemplazar_composicion(
            inventada,
            lista,
            contracts.Dominio.CIVIL,
            linea_base.FECHA_LINEA_BASE,
            condiciones="cuadrilla ampliada a siete obreros",
        )


def test_reemplazar_composicion_exige_condiciones_no_vacias(sesion):
    """RF-33: no se persiste una composicion cuyo rendimiento no declare condiciones (arreglo 1).

    Antes del arreglo, `reemplazar_composicion` ni siquiera aceptaba `condiciones`: llamaba a
    `a_modelo_rendimiento_estimado` sin ese dato y dejaba un `Rendimiento` con `condiciones=''`
    en cada edicion de UC-11. La reproduccion manual (script efimero sobre `data/apu.db`
    sembrada) lo confirmo antes de tocar el codigo: la segunda fila impresa traia
    `condiciones=''`.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    corregido = replace(
        linea_base.APU_RELLENO,
        rendimiento=linea_base.APU_RELLENO.rendimiento + Decimal("1"),
    )

    for condiciones_vacias in ("", "   "):
        with pytest.raises(ValueError, match="condiciones"):
            catalogo.reemplazar_composicion(
                corregido,
                lista,
                contracts.Dominio.CIVIL,
                linea_base.FECHA_LINEA_BASE,
                condiciones=condiciones_vacias,
            )


def test_reemplazar_composicion_propaga_las_condiciones_al_rendimiento(sesion):
    """Arreglo 1: el rendimiento que registra la edicion trae las condiciones que se declararon."""
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    corregido = replace(
        linea_base.APU_RELLENO,
        rendimiento=linea_base.APU_RELLENO.rendimiento + Decimal("1"),
    )

    catalogo.reemplazar_composicion(
        corregido,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        condiciones="cuadrilla ampliada a siete obreros",
    )

    rendimientos = catalogo.rendimientos("LB-05-REL")
    assert rendimientos[-1].condiciones == "cuadrilla ampliada a siete obreros"
    assert all(rendimiento.condiciones for rendimiento in rendimientos)


def test_reemplazar_composicion_sin_cambios_no_agrega_rendimiento(sesion):
    """Arreglo 2: repetir el mismo valor y las mismas condiciones no anade una fila al historico.

    Es la patologia que el ruling de la tarea 7 elimino de la siembra (`4f2075a`), reintroducida
    por `reemplazar_composicion`: registrar un rendimiento nuevo en cada edicion, aunque nada
    cambie, deja `obs=2, min=8, max=8` (varianza cero) y hace que cualquier valor futuro dispare
    `advertencia_rendimiento`. Reemplazar las lineas con la misma composicion no debe tocar el
    historico de rendimientos.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    antes = catalogo.rendimientos("LB-05-REL")

    catalogo.reemplazar_composicion(
        linea_base.APU_RELLENO,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        condiciones=antes[-1].condiciones,
    )

    despues = catalogo.rendimientos("LB-05-REL")
    assert despues == antes
    assert Catalogo(sesion).composicion("LB-05-REL") == linea_base.APU_RELLENO


def test_reemplazar_composicion_tras_un_medido_no_deja_el_estimado_obsoleto(sesion):
    """Regresion: `_registrar_rendimiento_si_cambia` comparaba contra el ultimo rendimiento de
    CUALQUIER tipo, pero `composicion()` reconstruye el APU con el ultimo ESTIMADO (via
    `_rendimiento_estimado`). Si entre medio se registra un MEDIDO con el mismo valor y
    condiciones que la edicion siguiente, la comparacion contra "cualquiera" concluye que nada
    cambio y no registra el ESTIMADO nuevo -- `composicion()` sigue devolviendo el rendimiento
    viejo, en silencio.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    condiciones = "cuadrilla ampliada, compactadora nueva"

    sesion.add(
        models.Ejecucion(
            referencia="EJ-REL-01",
            fecha_inicio=date(2026, 7, 1),
            descripcion="Relleno compactado, tramo medido",
        )
    )
    sesion.flush()
    catalogo.registrar_rendimiento(
        contracts.Rendimiento(
            codigo_partida="LB-05-REL",
            valor=Decimal("9"),
            tipo=contracts.TipoRendimiento.MEDIDO,
            fecha=date(2026, 7, 1),
            condiciones=condiciones,
            referencia_ejecucion="EJ-REL-01",
        )
    )

    corregido = replace(linea_base.APU_RELLENO, rendimiento=Decimal("9"))
    catalogo.reemplazar_composicion(
        corregido,
        lista,
        contracts.Dominio.CIVIL,
        date(2026, 7, 2),
        condiciones=condiciones,
    )

    assert Catalogo(sesion).composicion("LB-05-REL").rendimiento == Decimal("9")


def test_reemplazar_composicion_agrega_rendimiento_solo_si_cambian_condiciones(sesion):
    """Arreglo 2, complemento: mismo valor pero condiciones distintas si cuenta como cambio."""
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    antes = catalogo.rendimientos("LB-05-REL")

    catalogo.reemplazar_composicion(
        linea_base.APU_RELLENO,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        condiciones="compactacion manual, sin compactadora",
    )

    despues = catalogo.rendimientos("LB-05-REL")
    assert len(despues) == len(antes) + 1
    assert despues[-1].condiciones == "compactacion manual, sin compactadora"
    assert despues[-1].valor == linea_base.APU_RELLENO.rendimiento


def test_script_seed_crea_la_base(tmp_path):
    ruta = tmp_path / "apu.db"
    assert main(["--db", str(ruta)]) == 0
    assert ruta.exists()

    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        with abrir_sesion(motor) as sesion:
            catalogo = Catalogo(sesion)
            assert _contar(sesion, models.Partida) == len(linea_base.APUS_LINEA_BASE)
            composiciones = catalogo.composiciones(CODIGOS)
            assert composiciones == {apu.codigo_partida: apu for apu in linea_base.APUS_LINEA_BASE}
    finally:
        motor.dispose()


def test_la_siembra_deja_rendimientos_estimados_con_condiciones(sesion):
    """Sin condiciones declaradas, un rendimiento estimado no tiene procedencia que auditar.

    La pagina de composicion (fase P2) exige declararlas; la siembra de la linea base tiene que
    dar el ejemplo, y ademas es lo que permite que proponer_rendimiento sugiera algo.
    """
    catalogo = Catalogo(sesion)

    for codigo in CODIGOS:
        registrados = catalogo.rendimientos(codigo)
        assert registrados, codigo
        assert all(rendimiento.condiciones for rendimiento in registrados), codigo


def test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo(sesion):
    """Deuda 1 del ramal: una línea a destajo volvía como jornal (mapeo.py construía tres campos).

    Es la diferencia entre 6,00 USD/m2 y 6,00 × (1 + FCAS) + bono, dividido entre el rendimiento:
    el destajo del artículo 114 de la LOTTT deja de serlo en cuanto se guarda.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    mixto = contracts.ComposicionAPU(
        codigo_partida="LB-99-MIX",
        descripcion="Partida de prueba con las dos modalidades",
        unidad="m2",
        rendimiento=Decimal("20"),
        mano_obra=(
            contracts.LineaManoObra("Obrero de primera", Decimal("1"), Decimal("12.50")),
            contracts.LineaManoObra(
                "Friso a destajo",
                Decimal("1"),
                Decimal("6.00"),
                contracts.ModalidadManoObra.DESTAJO,
            ),
        ),
    )

    catalogo.cargar_composicion(
        mixto,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        "composicion de prueba con jornal y destajo",
    )
    sesion.flush()
    vuelta = Catalogo(sesion).composicion("LB-99-MIX", fecha=linea_base.FECHA_LINEA_BASE)

    modalidades = [linea.modalidad for linea in vuelta.mano_obra]
    assert modalidades == [
        contracts.ModalidadManoObra.JORNAL,
        contracts.ModalidadManoObra.DESTAJO,
    ]
    assert vuelta.total_obreros == Decimal("1"), "el destajista no devenga bono de alimentación"


def test_una_linea_sin_modalidad_persistida_vuelve_como_jornal(sesion):
    """Tras un `ALTER TABLE ... ADD COLUMN modalidad`, las filas preexistentes quedan en NULL y el
    contrato debe leerlas como JORNAL, su valor por defecto.

    Esta prueba simula esa migración asignando `None` a mano: no reproduce que una base anterior a
    esta columna "no cambia ni un céntimo" al leerse, porque sin el `ALTER TABLE` esa base ni
    siquiera abre — `Base.metadata.create_all` (`core/catalog/sesion.py`) nunca altera una tabla
    que ya existe. Ese hallazgo, y las dos salidas para conservar los datos de una base así, están
    en `docs/bitacora/2026-09-20-P2-hallazgo-migraciones.md`. Lo que esta prueba sí garantiza es la
    rama NULL→JORNAL de `core/catalog/mapeo.py:87-89`, que es la que hace legibles las filas viejas
    una vez aplicado el `ALTER TABLE`.

    La línea base solo trae JORNAL (NORMAS.md §4): sin sembrar aquí una línea a DESTAJO, poner en
    NULL cualquier fila y esperar JORNAL no tenía fase roja, porque JORNAL ya era su modalidad. Se
    siembra una partida mixta (mismo patrón que
    `test_la_modalidad_a_destajo_sobrevive_el_viaje_por_el_catalogo`), se comprueba que vuelve como
    DESTAJO, y solo entonces se pone en NULL en la base para comprobar que decae a JORNAL.
    """
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(linea_base.FECHA_LINEA_BASE)
    mixto = contracts.ComposicionAPU(
        codigo_partida="LB-98-NUL",
        descripcion="Partida de prueba para la migracion de modalidad",
        unidad="m2",
        rendimiento=Decimal("20"),
        mano_obra=(
            contracts.LineaManoObra(
                "Friso a destajo (migracion)",
                Decimal("1"),
                Decimal("6.00"),
                contracts.ModalidadManoObra.DESTAJO,
            ),
        ),
    )
    catalogo.cargar_composicion(
        mixto,
        lista,
        contracts.Dominio.CIVIL,
        linea_base.FECHA_LINEA_BASE,
        "composicion de prueba para la migracion NULL->JORNAL",
    )
    sesion.flush()

    antes = Catalogo(sesion).composicion("LB-98-NUL", fecha=linea_base.FECHA_LINEA_BASE)
    assert [obrero.modalidad for obrero in antes.mano_obra] == [
        contracts.ModalidadManoObra.DESTAJO
    ], "la fila debe empezar a destajo para que la prueba pueda fallar"

    linea = sesion.scalars(
        select(models.ComposicionAPU)
        .join(models.Insumo)
        .join(models.Partida)
        .where(models.Partida.codigo == "LB-98-NUL")
        .where(models.Insumo.tipo == models.TipoInsumo.MANO_OBRA)
    ).one()
    linea.modalidad = None
    sesion.flush()

    vuelta = Catalogo(sesion).composicion("LB-98-NUL", fecha=linea_base.FECHA_LINEA_BASE)

    assert all(
        obrero.modalidad is contracts.ModalidadManoObra.JORNAL for obrero in vuelta.mano_obra
    )


def test_crear_esquema_agrega_descarte_version_a_una_base_existente(tmp_path):
    """Expediente C3.2: la tabla es aditiva; una base creada sin ella la recibe sin perder datos."""
    motor = crear_motor(f"sqlite:///{(tmp_path / 'anterior.db').as_posix()}")
    try:
        anteriores = [t for t in models.Base.metadata.sorted_tables if t.name != "descarte_version"]
        models.Base.metadata.create_all(motor, tables=anteriores)
        with abrir_sesion(motor) as sesion:
            sembrar(sesion)
            sesion.commit()  # QA-1: `sembrar` solo hace flush y `abrir_sesion` revierte al cerrar
            partidas = _contar(sesion, models.Partida)

        crear_esquema(motor)

        assert "descarte_version" in inspect(motor).get_table_names()
        with abrir_sesion(motor) as sesion:
            assert _contar(sesion, models.Partida) == partidas == len(linea_base.APUS_LINEA_BASE)
        # A-11: borrar un presupuesto no queda bloqueado por su marca (PRAGMA foreign_keys=ON).
        (clave,) = inspect(motor).get_foreign_keys("descarte_version")
        assert clave["options"].get("ondelete") == "CASCADE"
    finally:
        motor.dispose()
