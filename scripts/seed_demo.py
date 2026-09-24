"""Una sola orden deja la aplicacion lista: linea base, demostracion y presupuesto (Sesion P4.2).

Antes sembraba solo el caso de demostracion (Sesion P3.4, fase P3); desde la Tarea 2 de P4.2,
``main`` deja la base de datos lista de punta a punta con una sola orden: primero la linea base
civil (``scripts.seed.sembrar``), despues las tres partidas ``DEMO-*`` con su lista de precios
heredando **todos** los precios de la vigente, y por ultimo el presupuesto ``DEMO-001`` guardado
con su informe de auditoria. Corregia ademas un defecto real heredado de P3: la lista de precios
de la demostracion nacia vacia, asi que sembrar la linea base y la demostracion en la misma base
dejaba las cinco partidas ``LB-*`` sin precio desde la fecha de la demostracion en adelante.

**Caso didactico, no obra ejecutada.** Igual que la linea base civil (`scripts/seed.py`) y los
catalogos telecom/industrial/sistemas, las tres partidas de este modulo son un ejercicio academico
ficticio (CLAUDE.md §1): nadie tendio esta tuberia ni instalo esta valvula. Su unico proposito es
que, al abrir la aplicacion contra `data/apu.db` (el archivo que todas las paginas de `ui/paginas/`
usan por defecto), el catalogo no aparezca vacio y muestre algo que ademas de existir **ensena**
la decision D9: una partida con mano de obra a jornal y a destajo a la vez.

Hermano de `scripts/seed.py`, `scripts/seed_telecom.py`, `scripts/seed_industrial.py` y
`scripts/seed_sistemas.py`: mismo patron de `--db`, `--reiniciar`, `Catalogo` y resumen impreso.
A diferencia de ellos, este caso no proviene de ningun PDF ni CSV externo (no hay fixture que
citar): las tres composiciones se escriben aqui mismo, en `construir_caso_demo`, que es la
**unica** construccion del caso en todo el repositorio (principio DRY, CLAUDE.md §2). Cualquier
otro modulo que necesite este caso -- por ejemplo la prueba de extremo a extremo de la Tarea 3 de
P3, `tests/integration/test_composicion_extremo_a_extremo.py` -- la importa desde aqui en vez de
copiarla: un caso de demostracion escrito dos veces es dos casos que divergen en la primera
correccion. `elaborar_caso_demo` es, del mismo modo, la **unica** elaboracion del caso: la usan el
resumen impreso, `guardar_presupuesto_demo` y las pruebas.

Que ejercita el caso, partida por partida
==========================================

- ``DEMO-01-INST`` (Instalacion de tuberia PVC de 6 pulgadas): mano de obra **jornal y destajo en
  la misma partida** (decision D9, articulo 114 de la LOTTT: el destajo se paga por unidad de obra
  instalada, sin FCAS ni bono, y entra completo al precio unitario); material con desperdicio
  (tuberia, cantidad 1,05 por cada metro: 5 % de merma, igual convencion que
  ``tests/fixtures/apu_linea_base.py``); equipos con depreciacion parcial. Ademas acumula **dos**
  observaciones de rendimiento (``FECHA_OBSERVACION_PREVIA``, anterior a ``FECHA_DEMO``, y la de
  su composicion) para que la advertencia de RF-27 tenga historial que ejercitar.
- ``DEMO-02-VALV`` (Suministro e instalacion de valvula de paso de 6 pulgadas): mano de obra toda
  a jornal, para que el contraste con la partida anterior sea visible; material con desperdicio
  (empaques de caucho, 2 unidades + 5 % de merma = 2,10); mismo equipo que la partida anterior con
  el mismo factor de depreciacion (0,05), declarado igual en ambas para no reproducir el hallazgo 7
  de la linea base (CLAUDE.md §7, regla R6).
- ``DEMO-03-PRUEBA`` (Prueba hidrostatica de la linea instalada): partida adicional, solo para que
  el presupuesto tenga tres periodos y una curva de inversion con mas de un tramo.

Uso::

    uv run python scripts/seed_demo.py                 # crea/actualiza data/apu.db
    uv run python scripts/seed_demo.py --db /tmp/x.db  # otra ruta
    uv run python scripts/seed_demo.py --reiniciar     # borra el esquema y lo vuelve a crear

Deja sembrados, todo idempotente: los cinco APU ``LB-*`` de la linea base, las tres partidas
``DEMO-*``, las dos listas de precios (la de la linea base y la de la demostracion, que hereda
todos los precios de la primera), el presupuesto ``DEMO-001`` guardado con su informe de
auditoria, y dos observaciones de rendimiento para ``DEMO-01-INST``.

**Nunca se corrio este script contra ``data/apu.db`` durante el desarrollo**: todas las pruebas de
`tests/integration/test_seed_demo.py` se hicieron contra un archivo temporal, siguiendo la misma
precaucion que pide el plan de la fase P4.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

# Igual que en scripts/seed.py: ejecutado como `python scripts/...`, sys.path[0] es scripts/ y
# `core` no se resuelve (pyproject declara `package = false`: no hay instalacion que lo exponga).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core import models  # noqa: E402
from core.budget import (  # noqa: E402
    ResultadoElaboracion,
    elaborar,
    guardar_presupuesto,
    plan_secuencial,
)
from core.catalog import (  # noqa: E402
    Catalogo,
    abrir_sesion,
    crear_esquema,
    crear_motor,
    registrar_rendimiento,
)
from core.contracts import (  # noqa: E402
    ComposicionAPU,
    Dominio,
    ItemComputo,
    LineaEquipo,
    LineaManoObra,
    LineaMaterial,
    ModalidadManoObra,
    OrigenTipo,
    ParametrosCosto,
    TipoRendimiento,
)
from core.verification.informe import DECIMALES_PRESENTACION  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402
from scripts import seed  # noqa: E402

NOMBRE_PROYECTO = "AREN.IA: caso de demostracion (linea de agua potable, didactico)"
DESCRIPCION_PROYECTO = (
    "Caso didactico sembrado para que el prototipo AREN.IA no abra con el catalogo vacio: tres "
    "partidas ficticias de una linea de agua potable que, entre las tres, ejercitan mano de obra "
    "a jornal y a destajo en la misma partida (decision D9), materiales con desperdicio y equipos "
    "con depreciacion parcial. No representa obra ejecutada."
)
NOMBRE_LISTA = "Lista de referencia del caso de demostracion AREN.IA"
ORIGEN_LISTA = "scripts/seed_demo.py (precios de ejemplo, no cotizados)"
CODIGO_PRESUPUESTO = "DEMO-001"
MONEDA = "USD"
FECHA_DEMO = date(2026, 9, 20)
RUTA_POR_DEFECTO = seed.RUTA_POR_DEFECTO  # fuente unica de la ruta de trabajo (INV-044)

# Parametros de la estructura de costos: los valores por defecto del contrato (CLAUDE.md §4), sin
# repetirlos aqui (principio DRY).
PARAMETROS_DEMO = ParametrosCosto()

#: Segunda observacion didactica de rendimiento de `DEMO-01-INST` (hecho verificado 9 del plan):
#: sin ella, ninguna partida sembrada llega a `MINIMO_OBSERVADO_PARA_ADVERTIR` observaciones y la
#: advertencia de RF-27 no se puede ejercitar contra la base sembrada. Fechada **antes** de
#: `FECHA_DEMO` a proposito: `Catalogo.composicion` y `proponer_rendimiento` siguen escogiendo el
#: rendimiento mas reciente (el de la composicion, en `FECHA_DEMO`), asi que el total y la
#: composicion de la demostracion no se mueven.
FECHA_OBSERVACION_PREVIA = date(2026, 8, 15)
#: Distinto del rendimiento de la composicion (60) para que el rango observado no sea degenerado.
RENDIMIENTO_OBSERVACION_PREVIA = Decimal("50")
CONDICIONES_OBSERVACION_PREVIA = (
    "segunda estimacion didactica de DEMO-01-INST, previa a la vigente; no proviene de una "
    "ejecucion medida (rendimiento observado antes de ajustar la cuadrilla mixta a 60 m/dia)"
)

#: RF-33 (docs/ERS.md, UC-10; spec §3.3): `Catalogo.cargar_composicion` exige declarar, junto con
#: el rendimiento, las condiciones bajo las que se estimo -- y que no proviene de una ejecucion
#: medida, igual que en `scripts/seed.py` (`CONDICIONES_LINEA_BASE`) y en los otros dos sembradores.
CONDICIONES_DEMO: dict[str, str] = {
    "DEMO-01-INST": (
        "cuadrilla mixta de dos personas (un supervisor a jornal y una cuadrilla instaladora a "
        "destajo por metro instalado, articulo 114 LOTTT), tuberia PVC de 6 pulgadas en zanja "
        "abierta; rendimiento estimado del caso didactico, no proviene de una ejecucion medida"
    ),
    "DEMO-02-VALV": (
        "plomero de 1ra y un ayudante, valvula de paso de 6 pulgadas sobre linea de PVC ya "
        "instalada; rendimiento estimado del caso didactico, no proviene de una ejecucion medida"
    ),
    "DEMO-03-PRUEBA": (
        "tecnico de pruebas y un ayudante, prueba hidrostatica con bomba manual sobre el tramo ya "
        "instalado; rendimiento estimado del caso didactico, no proviene de una ejecucion medida"
    ),
}


# ---------------------------------------------------------------------------------------------
# El caso de demostracion: unica construccion en el repositorio (ver docstring del modulo)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CasoDemo:
    """Empaqueta el caso completo: composiciones, cantidades de obra y como presupuestarlas.

    `composiciones` y `items` viajan emparejados por `codigo_partida`: `elaborar` los consume
    directo (encurva y audita siempre), sin transformacion.
    """

    composiciones: tuple[ComposicionAPU, ...]
    items: tuple[ItemComputo, ...]
    parametros: ParametrosCosto
    condiciones: dict[str, str]
    codigo_presupuesto: str
    fecha: date
    moneda: str


def _mat(descripcion: str, unidad: str, cantidad: str, precio: str) -> LineaMaterial:
    return LineaMaterial(descripcion, unidad, Decimal(cantidad), Decimal(precio))


def _eq(descripcion: str, cantidad: str, precio: str, depreciacion: str) -> LineaEquipo:
    return LineaEquipo(descripcion, Decimal(cantidad), Decimal(precio), Decimal(depreciacion))


def _mo(
    descripcion: str,
    cantidad: str,
    sueldo: str,
    modalidad: ModalidadManoObra = ModalidadManoObra.JORNAL,
) -> LineaManoObra:
    return LineaManoObra(descripcion, Decimal(cantidad), Decimal(sueldo), modalidad)


def construir_composiciones_demo() -> tuple[ComposicionAPU, ...]:
    """Las tres `ComposicionAPU` del caso, en el orden en que se presupuestan.

    Pura: no toca disco ni sesion, no imprime nada. Es la funcion que debe importarse en vez de
    copiar el caso (ver docstring del modulo).
    """
    apu_instalacion = ComposicionAPU(
        codigo_partida="DEMO-01-INST",
        descripcion="Instalacion de tuberia PVC de 6 pulgadas con cuadrilla mixta",
        unidad="m",
        rendimiento=Decimal("60"),
        materiales=(
            # 1,05 = 1 m de tuberia + 5 % de desperdicio, misma convencion que la linea base.
            _mat("Tuberia PVC 6 pulg", "m", "1.05", "9.50"),
            _mat("Pegamento para PVC", "unidad", "0.02", "18.00"),
            _mat("Lija para PVC", "unidad", "0.02", "1.50"),
        ),
        equipos=(
            _eq("Cortadora de tubos", "1", "40.00", "0.05"),
            _eq("Nivel laser", "1", "60.00", "0.05"),
        ),
        mano_obra=(
            _mo("Supervisor de cuadrilla", "1", "8.00"),
            # Destajo (articulo 114 LOTTT, decision D9): "sueldo" es el precio por metro
            # instalado, no un jornal diario; entra completo, sin FCAS ni bono.
            _mo(
                "Cuadrilla instaladora a destajo",
                "1",
                "3.50",
                ModalidadManoObra.DESTAJO,
            ),
        ),
    )

    apu_valvula = ComposicionAPU(
        codigo_partida="DEMO-02-VALV",
        descripcion="Suministro e instalacion de valvula de paso de 6 pulgadas",
        unidad="unidad",
        rendimiento=Decimal("6"),
        materiales=(
            _mat("Valvula de paso 6 pulg", "unidad", "1.00", "85.00"),
            # 2,10 = 2 empaques + 5 % de desperdicio.
            _mat("Empaques de caucho", "unidad", "2.10", "1.20"),
            _mat("Pegamento para PVC", "unidad", "0.05", "18.00"),
        ),
        equipos=(
            # Mismo factor de depreciacion (0,05) que en DEMO-01-INST: un mismo insumo lleva un
            # solo factor en todos los APU (regla R6; hallazgo 7 de la linea base, evitado aqui).
            _eq("Cortadora de tubos", "1", "40.00", "0.05"),
            _eq("Llave de cadena", "2", "20.00", "0.05"),
        ),
        mano_obra=(
            _mo("Plomero de 1ra", "1", "7.00"),
            _mo("Ayudante", "1", "4.00"),
        ),
    )

    apu_prueba = ComposicionAPU(
        codigo_partida="DEMO-03-PRUEBA",
        descripcion="Prueba hidrostatica de la linea de PVC instalada",
        unidad="m",
        rendimiento=Decimal("120"),
        materiales=(
            _mat("Agua para prueba", "m3", "0.05", "2.00"),
            _mat("Tapones de prueba PVC 6 pulg", "unidad", "0.02", "6.00"),
        ),
        equipos=(
            _eq("Bomba de prueba hidrostatica", "1", "70.00", "0.10"),
            _eq("Manometro", "1", "15.00", "0.05"),
        ),
        mano_obra=(
            _mo("Tecnico de pruebas", "1", "7.50"),
            _mo("Ayudante", "1", "4.00"),
        ),
    )

    return (apu_instalacion, apu_valvula, apu_prueba)


def construir_items_demo() -> tuple[ItemComputo, ...]:
    """Las cantidades de obra del caso: 180 m de linea, 4 valvulas, y la prueba sobre esos 180 m.

    Pura, igual que `construir_composiciones_demo`. Origen MANUAL (CLAUDE.md §5): son cantidades
    declaradas para el caso didactico, no derivadas de una regla ni de un modelo IFC.
    """
    return (
        ItemComputo(
            codigo_partida="DEMO-01-INST",
            descripcion="Tramo de linea de agua potable",
            unidad="m",
            cantidad=Decimal("180"),
            origen_id="DEMO-TRAMO-01",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        ),
        ItemComputo(
            codigo_partida="DEMO-02-VALV",
            descripcion="Valvulas de paso del tramo",
            unidad="unidad",
            cantidad=Decimal("4"),
            origen_id="DEMO-VALVULAS-01",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        ),
        ItemComputo(
            codigo_partida="DEMO-03-PRUEBA",
            descripcion="Prueba hidrostatica del tramo",
            unidad="m",
            cantidad=Decimal("180"),
            origen_id="DEMO-PRUEBA-01",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        ),
    )


def construir_caso_demo() -> CasoDemo:
    """El caso completo, listo para persistir (`sembrar_demo`) o para elaborar un presupuesto.

    Funcion de nombre claro y sin efectos secundarios (no abre sesion, no toca disco): es la que
    debe importarse -- por ejemplo desde
    `tests/integration/test_composicion_extremo_a_extremo.py` (Tarea 3) -- en vez de copiar el
    caso. Ver el docstring del modulo para el detalle de cada partida.
    """
    return CasoDemo(
        composiciones=construir_composiciones_demo(),
        items=construir_items_demo(),
        parametros=PARAMETROS_DEMO,
        condiciones=CONDICIONES_DEMO,
        codigo_presupuesto=CODIGO_PRESUPUESTO,
        fecha=FECHA_DEMO,
        moneda=MONEDA,
    )


def elaborar_caso_demo(caso: CasoDemo) -> ResultadoElaboracion:
    """El presupuesto del caso, con su curva secuencial, elaborado y auditado.

    **Unica** elaboracion del caso en el modulo (principio DRY, CLAUDE.md §2): antes vivia en
    linea dentro de `_imprimir_resumen`, que ahora la llama en vez de repetirla; tambien la usan
    `guardar_presupuesto_demo` y `tests/integration/test_seed_demo.py`.
    """
    composiciones_por_codigo = {apu.codigo_partida: apu for apu in caso.composiciones}
    return elaborar(
        caso.items,
        composiciones_por_codigo,
        caso.parametros,
        codigo=caso.codigo_presupuesto,
        fecha=caso.fecha,
        moneda=caso.moneda,
        plan=plan_secuencial,
    )


# ---------------------------------------------------------------------------------------------
# Persistencia: el caso de demostracion en SQLite
# ---------------------------------------------------------------------------------------------


def sembrar_demo(sesion: Session, caso: CasoDemo | None = None) -> models.Proyecto:
    """Carga proyecto, lista de precios y las tres partidas `DEMO-*`. Idempotente: si el proyecto
    ya existe, no vuelve a cargar nada (mismo criterio que `scripts/seed.py:sembrar`).

    La lista nueva **hereda todos los precios de la vigente** antes de cargar ninguna composicion,
    igual que exige `core.catalog.precios.crear_lista_desde_archivo`: "la lista nueva nace con
    todos los precios de la anterior". Esa funcion no sirve aqui porque exige una ruta de archivo
    (`leer_lista_precios`) que este caso de demostracion no tiene -- `caso` lo construye
    `construir_caso_demo()` en Python, no un archivo tabular -- (decision documentada en el brief
    de la Tarea 2; coste si es equivocado: cinco lineas que migrar a `core/catalog/precios.py` el
    dia que un tercer creador de listas las necesite). Este sembrador **no** funciona sobre una
    base vacia: igual que `crear_lista_desde_archivo`, exige una lista vigente a `caso.fecha` de la
    que heredar; si no hay ninguna, `Catalogo.lista_vigente` lanza `CatalogoIncompleto` tal cual.
    """
    caso = caso if caso is not None else construir_caso_demo()

    proyecto = sesion.scalars(
        select(models.Proyecto).where(models.Proyecto.nombre == NOMBRE_PROYECTO)
    ).one_or_none()
    if proyecto is not None:
        return proyecto

    anterior = Catalogo(sesion).lista_vigente(caso.fecha)

    proyecto = models.Proyecto(
        nombre=NOMBRE_PROYECTO,
        descripcion=DESCRIPCION_PROYECTO,
        dominio=str(Dominio.CIVIL),
    )
    lista = models.ListaPrecios(
        nombre=NOMBRE_LISTA,
        moneda=caso.moneda,
        fecha_vigencia=caso.fecha,
        origen=ORIGEN_LISTA,
    )
    sesion.add_all((proyecto, lista))
    sesion.flush()

    sesion.add_all(
        models.PrecioInsumo(lista_id=lista.id, insumo_id=precio.insumo_id, precio=precio.precio)
        for precio in anterior.precios
    )
    sesion.flush()

    catalogo = Catalogo(sesion)
    for composicion in caso.composiciones:
        catalogo.cargar_composicion(
            composicion,
            lista,
            Dominio.CIVIL,
            caso.fecha,
            caso.condiciones[composicion.codigo_partida],
        )

    registrar_rendimiento(
        sesion,
        "DEMO-01-INST",
        RENDIMIENTO_OBSERVACION_PREVIA,
        TipoRendimiento.ESTIMADO,
        FECHA_OBSERVACION_PREVIA,
        CONDICIONES_OBSERVACION_PREVIA,
    )

    sesion.commit()
    return proyecto


def guardar_presupuesto_demo(
    sesion: Session, proyecto: models.Proyecto, caso: CasoDemo
) -> models.Presupuesto | None:
    """Guarda el presupuesto elaborado del caso de demostracion. Idempotente: no hace nada si el
    proyecto ya tiene un presupuesto con `caso.codigo_presupuesto`. No confirma la transaccion,
    igual que `core.budget.guardar_presupuesto`: eso es de quien llama (`main`)."""
    existente = sesion.scalars(
        select(models.Presupuesto).where(
            models.Presupuesto.proyecto_id == proyecto.id,
            models.Presupuesto.codigo == caso.codigo_presupuesto,
        )
    ).one_or_none()
    if existente is not None:
        return None

    lista = Catalogo(sesion).lista_vigente(caso.fecha)
    resultado = elaborar_caso_demo(caso)
    return guardar_presupuesto(
        sesion, resultado.presupuesto, resultado.informe, proyecto, lista, caso.parametros
    )


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--db",
        default=RUTA_POR_DEFECTO,
        help=f"ruta del archivo SQLite (por defecto {RUTA_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--reiniciar", action="store_true", help="borra el esquema antes de crearlo de nuevo"
    )
    argumentos = analizador.parse_args(argv)

    caso = construir_caso_demo()
    ruta = Path(argumentos.db)
    motor = crear_motor(f"sqlite:///{ruta.as_posix()}")
    try:
        if argumentos.reiniciar:
            models.Base.metadata.drop_all(motor)
        crear_esquema(motor)
        with abrir_sesion(motor) as sesion:
            # Una sola orden deja la aplicacion lista de punta a punta (P4.2): la linea base
            # primero (de la que la demostracion hereda precios), despues la demostracion y su
            # presupuesto guardado.
            seed.sembrar(sesion)
            proyecto = sembrar_demo(sesion, caso)
            guardar_presupuesto_demo(sesion, proyecto, caso)
            sesion.commit()
            _imprimir_resumen(sesion, ruta, proyecto, caso)
    finally:
        motor.dispose()
    return 0


_TABLAS_DEL_RESUMEN = (
    models.Partida,
    models.Insumo,
    models.PrecioInsumo,
    models.ComposicionAPU,
    models.Rendimiento,
)


def _imprimir_resumen(
    sesion: Session, ruta: Path, proyecto: models.Proyecto, caso: CasoDemo
) -> None:
    catalogo = Catalogo(sesion)
    lista = catalogo.lista_vigente(caso.fecha)

    print(f"Base de datos: {ruta}")
    print(f"Proyecto: {proyecto.nombre} ({proyecto.dominio})")
    print(
        f"Lista de precios: {lista.nombre} ({lista.moneda}, vigente desde {lista.fecha_vigencia})"
    )
    conteos = " | ".join(
        f"{tabla.__name__}: {sesion.scalar(select(func.count()).select_from(tabla))}"
        for tabla in _TABLAS_DEL_RESUMEN
    )
    print(conteos)

    print("Partidas del caso de demostracion:")
    for partida in catalogo.partidas(Dominio.CIVIL):
        if partida.codigo not in caso.condiciones:
            continue
        composicion = catalogo.composicion(partida.codigo, fecha=caso.fecha)
        modalidades = ", ".join(sorted({linea.modalidad.value for linea in composicion.mano_obra}))
        print(
            f"  {partida.codigo}  {partida.unidad:<6} rendimiento {composicion.rendimiento:>4}"
            f"  materiales {len(composicion.materiales)}"
            f"  equipos {len(composicion.equipos)}"
            f"  mano de obra {len(composicion.mano_obra)} ({modalidades})"
        )

    print(resumen(elaborar_caso_demo(caso), caso.moneda))


def _monto(valor: Decimal) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def resumen(resultado: ResultadoElaboracion, moneda: str) -> str:
    """El texto del presupuesto que imprime `main`: partidas, total, curva y auditoria.

    Los montos se redondean con la fuente unica de presentacion (`formatear_decimal` con
    `DECIMALES_PRESENTACION`, `ROUND_HALF_UP`), no con `:.2f`, que redondea al par (INV-049).
    """
    presupuesto = resultado.presupuesto
    lineas = [f"Presupuesto {presupuesto.codigo} ({len(presupuesto.partidas)} partidas):"]
    lineas += [
        f"  {partida.item.codigo_partida} [{partida.item.origen_id}] "
        f"{partida.item.cantidad:f} {partida.item.unidad} x "
        f"{_monto(partida.resultado.precio_unitario)} = {_monto(partida.total)} {moneda}"
        for partida in presupuesto.partidas
    ]
    lineas.append(f"  Total: {_monto(presupuesto.total)} {moneda}")
    lineas.append("Curva de inversion:")
    lineas += [
        f"  {punto.periodo}: {_monto(punto.monto)} (acumulado {_monto(punto.acumulado)})"
        for punto in presupuesto.curva
    ]
    lineas.append(
        f"Auditoria: {len(resultado.informe.hallazgos)} hallazgo(s), "
        f"{'CUMPLE' if resultado.informe.cumple else 'NO CUMPLE'}"
    )
    return "\n".join(lineas)


if __name__ == "__main__":
    raise SystemExit(main())
