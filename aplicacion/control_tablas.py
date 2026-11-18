"""Tablas del control de obra para la pantalla y para el Excel de la hoja.

Valuaciones con su Estado e IVA, indicadores en las dos monedas, alertas con sus tildes
restituidas sobre las frases fijas del núcleo, reproyección, opciones y decisiones, y las hojas
«Valuaciones», «Valor ganado» y «Decisiones» del Excel (`hojas_extra`).

Salió de `aplicacion/control.py` sin cambios (tarea 4.3 del plan de desenredo);
`aplicacion.control` lo reexporta.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from aplicacion.control_comun import (
    COLUMNAS_DECISIONES,
    COLUMNAS_OPCIONES,
    NO_APLICA,
    NO_DISPONIBLE,
    _indice,
    _monto,
)
from aplicacion.control_corte import ultimo_corte
from aplicacion.impuestos import ResumenImpuestos, con_iva
from core.budget.control import (
    ResultadoControl,
    calcular_control,
)
from core.budget.decision import decisiones
from core.budget.excel import TablaExportable
from core.budget.recuperacion import Opcion
from core.budget.valor_ganado import PreciosDelCorte
from core.budget.valuaciones import (
    LineaBaseInvalidada,
    tabla_valuaciones,
    valuaciones_registradas,
)
from core.catalog import Catalogo
from core.catalog.indices import TasaNoDisponible, tasa_aplicable
from core.catalog.moneda import convertir
from core.verification.texto import formatear_decimal

_ORDEN = {"ERROR": 3, "ADVERTENCIA": 2, "INFO": 1}


def estado_de_valuaciones(resultado: ResultadoControl) -> dict[str, str]:
    """Por clave de valuación, el peor hallazgo de R13-R14 (columna Estado, como RF-55)."""
    peores: dict[str, tuple[int, str]] = {}
    for hallazgo in resultado.informe.hallazgos:
        clave = hallazgo.origen_ids[0].split(":")[1]
        rango = _ORDEN.get(hallazgo.severidad.name, 0)
        texto = f"{hallazgo.severidad.name}: {hallazgo.regla}"
        if clave not in peores or rango > peores[clave][0]:
            peores[clave] = (rango, texto)
    return {clave: texto for clave, (_, texto) in peores.items()}


def subtotales_de_valuaciones(resultado: ResultadoControl) -> dict[str, Decimal]:
    """Por clave de valuación, su monto sin IVA: la suma de cantidad × unitario de la línea base
    (en su perspectiva, en la moneda del proyecto). Una línea cuya partida no está en la línea base
    no suma: R13 ya la señala como hallazgo. Es lo medido, no lo aprobado ni lo pagado."""
    instantanea = resultado.instantanea
    costo = instantanea.linea_base.perspectiva == "costo"
    unitarios = {
        p.item.codigo_partida: p.resultado.costo_directo if costo else p.resultado.precio_unitario
        for p in instantanea.presupuesto.partidas
    }
    return {
        v.clave: sum(
            (
                linea.cantidad * unitarios.get(linea.codigo_partida, Decimal(0))
                for linea in v.lineas
            ),
            Decimal(0),
        )
        for v in instantanea.valuaciones
    }


def impuestos_de_valuaciones(resultado: ResultadoControl | None) -> ResumenImpuestos:
    """El IVA sobre lo medido en todas las valuaciones juntas (IVA del acumulado, no suma de los
    IVA de cada una: pueden diferir en un céntimo). Sin valuaciones, ceros."""
    if resultado is None:
        return con_iva(Decimal(0))
    return con_iva(sum(subtotales_de_valuaciones(resultado).values(), Decimal(0)))


def filas_de_valuaciones(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Las valuaciones guardadas, en solo lectura, con su fecha de registro y su Estado. Las fechas
    van en dd/mm/aaaa, cada una en su columna: el número y el inspector los escribió el usuario."""
    estados = estado_de_valuaciones(resultado)
    montos = subtotales_de_valuaciones(resultado)
    return [
        {
            "Numero": v.numero or f"#{v.id}",
            "Periodo": f"{v.desde:%d/%m/%Y} a {v.hasta:%d/%m/%Y}",
            "Fecha": "" if v.fecha is None else f"{v.fecha:%d/%m/%Y}",
            "Inspector": v.inspector,
            "Registrada": "" if v.fecha_hora is None else v.fecha_hora.strftime("%d/%m/%Y %H:%M"),
            "Estado": estados.get(v.clave, "sin hallazgos"),
            "Subtotal": _monto(con_iva(montos[v.clave]).subtotal),
            "IVA": _monto(con_iva(montos[v.clave]).iva),
            "Total con IVA": _monto(con_iva(montos[v.clave]).total),
        }
        for v in resultado.instantanea.valuaciones
    ]


def _otra_moneda(sesion: Session, resultado: ResultadoControl) -> tuple[str, Decimal | None]:
    """La moneda que no es la del proyecto y la tasa aplicable a la fecha del corte (S1)."""
    moneda = resultado.instantanea.moneda
    otra = "USD" if moneda == "Bs" else "Bs"
    try:
        return otra, tasa_aplicable(sesion, resultado.instantanea.corte).valor
    except TasaNoDisponible:
        return otra, None


def filas_de_indicadores(sesion: Session, resultado: ResultadoControl) -> list[dict[str, str]]:
    """La tabla de §4.2 y la separación de §4.3, cada monto en las dos monedas con la tasa del
    corte (S1); lo que no se puede calcular dice «no disponible» y por qué."""
    ind, sep = resultado.indicadores, resultado.separacion
    moneda = resultado.instantanea.moneda
    otra, tasa = _otra_moneda(sesion, resultado)

    def en_otra(valor: Decimal | None) -> str:
        """El monto en la otra moneda con su símbolo; sin monto o sin tasa, «no disponible» a secas
        (la moneda solo acompaña a una cifra)."""
        if valor is None or tasa is None:
            return NO_DISPONIBLE
        return f"{formatear_decimal(convertir(valor, moneda, otra, tasa), 2)} {otra}"

    def monto(nombre: str, valor: Decimal | None, nota: str = "") -> dict[str, str]:
        return {
            "Indicador": f"{nombre} ({moneda})",
            "Valor": _monto(valor),
            "En la otra moneda": en_otra(valor),
            "Nota": nota,
        }

    def indice(nombre: str, valor: Decimal | None, nota: str = "") -> dict[str, str]:
        return {"Indicador": nombre, "Valor": _indice(valor), "En la otra moneda": "", "Nota": nota}

    no = ind.no_disponible
    filas = [
        monto("BAC", ind.bac),
        monto("PV", ind.pv),
        monto("EV", ind.ev),
        monto("AC", ind.ac, con_tildes(no.get("AC", ""))),
        monto("SV (plazo)", ind.sv),
        monto("CV", ind.cv, con_tildes(no.get("CV", ""))),
        indice("SPI", ind.spi, con_tildes(no.get("SPI", ""))),
        indice("CPI", ind.cpi, con_tildes(no.get("CPI", ""))),
        monto("EAC (índice BAC/CPI)", ind.eac_indice, con_tildes(no.get("EAC", ""))),
        monto("EAC (sistema)", ind.eac_sistema, con_tildes(no.get("EAC", ""))),
        monto("VAC", ind.vac, con_tildes(no.get("VAC", ""))),
        {
            "Indicador": "Término por el índice (día hábil)",
            "Valor": NO_APLICA if ind.termino_indice is None else str(ind.termino_indice),
            "En la otra moneda": "",
            "Nota": "",
        },
        monto("Desvío de precio", sep.precio, con_tildes(sep.no_disponible.get("precio", ""))),
        monto("Desvío de consumo", sep.consumo, con_tildes(sep.no_disponible.get("consumo", ""))),
    ]
    if sep.metodo:
        filas.append(
            {
                "Indicador": "Método y fuente del precio del corte",
                "Valor": sep.metodo,
                "En la otra moneda": "",
                "Nota": sep.fuente,
            }
        )
    if tasa is None:
        filas.append(
            {
                "Indicador": "Tasa del corte",
                "Valor": NO_DISPONIBLE,
                "En la otra moneda": "",
                "Nota": "sin tasa aplicable a la fecha del corte",
            }
        )
    return filas


# --- tildes de las alertas ---------------------------------------------------------------------
#
# El texto de las alertas y de sus motivos nace en `core/budget/valor_ganado.py` y
# `core/budget/equilibrio.py` sin tildes, y `core/` no se toca. Aquí se restituyen sobre las FRASES
# FIJAS del núcleo, nunca sobre palabras sueltas: lo que escribió el usuario (código o nombre de una
# partida, montos, fechas) entra en un hueco `{nombre}` y sale tal cual. Una frase que el catálogo
# no conoce pasa sin cambios; la prueba de guardia (tests/unit/test_control_alertas_tildes.py)
# lista las frases del núcleo que falten aquí.

#: (frase tal como la emite el núcleo, la misma con tildes). Los huecos `{x}` son datos.
PLANTILLAS_DEL_NUCLEO: tuple[tuple[str, str], ...] = (
    # AL-1 y AL-2
    ("retraso: SPI {spi}", "retraso: SPI {spi}"),
    ("sobrecosto: CPI {cpi}", "sobrecosto: CPI {cpi}"),
    # AL-3
    (
        "el termino proyectado (dia {termino}) pasa {retraso} dia(s) habil(es) del plan base "
        "(dia {plan})",
        "el término proyectado (día {termino}) pasa {retraso} día(s) hábil(es) del plan base "
        "(día {plan})",
    ),
    # AL-4: el mensaje del punto de equilibrio que cierra la frase
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
        "el punto de equilibrio proyectado: se alcanza en {periodo}",
        "el punto de equilibrio proyectado: se alcanza en {periodo}",
    ),
    (
        "el punto de equilibrio proyectado: sin curva de inversión: el punto de equilibrio no "
        "se ubica en el plan",
        "el punto de equilibrio proyectado: sin curva de inversión: el punto de equilibrio no "
        "se ubica en el plan",
    ),
    (
        "el punto de equilibrio proyectado sube mas de {puntos} puntos porcentuales sobre el de "
        "la linea base",
        "el punto de equilibrio proyectado sube más de {puntos} puntos porcentuales sobre el de "
        "la línea base",
    ),
    # AL-5
    (
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvia {precio} "
        "sobre un valor ganado de {ev}",
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvía {precio} "
        "sobre un valor ganado de {ev}",
    ),
    # AL-6
    (
        "la partida {codigo} tiene trabajo planificado y ningun avance (detenida)",
        "la partida {codigo} tiene trabajo planificado y ningún avance (detenida)",
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
    ("sin tasa aplicable para: {cortes}", "sin tasa aplicable para: {cortes}"),
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
    (
        "sin precio del corte para la partida {codigo}",
        "sin precio del corte para la partida {codigo}",
    ),
    ("sin precio del corte para {partidas}", "sin precio del corte para {partidas}"),
    (
        "sin avance o sin costos reales: el rendimiento del consumo no existe",
        "sin avance o sin costos reales: el rendimiento del consumo no existe",
    ),
    ("no proyectable: {partidas}", "no proyectable: {partidas}"),
    (
        "nada queda pendiente: la fecha de la ultima valuacion",
        "nada queda pendiente: la fecha de la última valuación",
    ),
    # Motivos por partida de la reproyección
    ("la partida no esta en el plan", "la partida no está en el plan"),
    (
        "el SPI global es 0: sin ritmo no se proyecta",
        "el SPI global es 0: sin ritmo no se proyecta",
    ),
    # Recuperación (opciones), supuestos, requisitos y mensajes sueltos del punto de equilibrio
    ("Mas cuadrillas", "Más cuadrillas"),
    ("Horas extra", "Horas extra"),
    ("Partidas en paralelo", "Partidas en paralelo"),
    ("Aceptar el retraso", "Aceptar el retraso"),
    ("ninguna partida pasa del objetivo", "ninguna partida pasa del objetivo"),
    (
        "ninguna partida sin empezar con inicio posterior al periodo siguiente",
        "ninguna partida sin empezar con inicio posterior al período siguiente",
    ),
    ("no aplica ({lista})", "no aplica ({lista})"),
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
    (
        "no existe punto de equilibrio: el margen de contribucion no es positivo",
        "no existe punto de equilibrio: el margen de contribución no es positivo",
    ),
    (
        "el punto de equilibrio no se alcanza dentro del contrato",
        "el punto de equilibrio no se alcanza dentro del contrato",
    ),
    ("el presupuesto no tiene ventas: no aplica", "el presupuesto no tiene ventas: no aplica"),
    ("se alcanza en {periodo}", "se alcanza en {periodo}"),
    (
        "sin curva de inversión: el punto de equilibrio no se ubica en el plan",
        "sin curva de inversión: el punto de equilibrio no se ubica en el plan",
    ),
)


#: Más largo que esto no es una frase del núcleo (la más larga mide ~200 caracteres): el catálogo
#: de regex lo devuelve intacto sin tocarlas, para que un texto hostil no cueste tiempo. El
#: desglose «no aplica (...)» no usa esas regex y no lleva tope.
LARGO_MAXIMO_A_CORREGIR = 2_000

#: Un hueco acotado: su expresión y, si lo que calza se presenta de otra forma (una fecha del
#: sistema en dd/mm/aaaa), la función que lo presenta.
Hueco = str | tuple[str, Callable[[str], str]]

#: Huecos con forma conocida: las cifras que el núcleo imprime. Acotarlos por clase hace lineal la
#: coincidencia (un `.+` voraz encadenado sería cúbico). Todo hueco no listado es texto del usuario
#: y cada plantilla tiene a lo sumo uno, de modo que tampoco encadena.
_HUECOS_NUMERICOS: dict[str, Hueco] = {
    "termino": r"\d+",
    "retraso": r"\d+",
    "plan": r"\d+",
    "spi": r"[-+0-9.,E]+",
    "cpi": r"[-+0-9.,E]+",
    "precio": r"[-+0-9.,E]+",
    "ev": r"[-+0-9.,E]+",
    "puntos": r"[-+0-9.,E]+",
}

#: Los motivos por partida del desglose «no aplica (cod: motivo; ...)» de `recuperacion.py`.
_MOTIVOS_POR_PARTIDA = {
    "sin composicion de APU": "sin composición de APU",
    "sin rendimiento": "sin rendimiento",
    "sin mano de obra a jornal": "sin mano de obra a jornal",
}


def _expresion(hueco: Hueco) -> str:
    return hueco if isinstance(hueco, str) else hueco[0]


def _compilar(crudo: str, huecos: Mapping[str, Hueco] = _HUECOS_NUMERICOS) -> re.Pattern[str]:
    """La frase del núcleo como expresión: el texto fijo literal, cada hueco `{x}` un dato."""
    partes = re.split(r"\{(\w+)\}", crudo)
    libres = [h for h in partes[1::2] if h not in huecos]
    if len(libres) > 1:
        raise ValueError(f"la plantilla {crudo!r} encadena huecos de texto libre")
    patron = "".join(
        f"(?P<{p}>{_expresion(huecos[p]) if p in huecos else '.+'})" if i % 2 else re.escape(p)
        for i, p in enumerate(partes)
    )
    return re.compile(patron, re.DOTALL)


def catalogo_de_frases(
    plantillas: Sequence[tuple[str, str]],
    huecos: Mapping[str, Hueco] = _HUECOS_NUMERICOS,
    *,
    largo_maximo: int = LARGO_MAXIMO_A_CORREGIR,
) -> Callable[[str], str]:
    """El corrector de un catálogo de frases fijas del núcleo (T8b; lo usa también Reajuste).

    Devuelve una función pura que, si el texto COMPLETO calza con una plantilla, lo reescribe con su
    versión con tildes; si no, lo devuelve igual. Lo que calza en un hueco libre (texto del usuario)
    vuelve tal cual; un hueco acotado con función (una fecha) se presenta con ella. Más largo que
    `largo_maximo` vuelve intacto sin probar ninguna expresión. Cada plantilla lleva a lo sumo un
    hueco libre (`_compilar` lo exige), así que el costo es lineal en el largo.
    """
    compilado = tuple((_compilar(crudo, huecos), con_tilde) for crudo, con_tilde in plantillas)
    presentar = {nombre: h[1] for nombre, h in huecos.items() if not isinstance(h, str)}

    def corregir(texto: str) -> str:
        if len(texto) > largo_maximo:
            return texto
        for patron, con_tilde in compilado:
            calce = patron.fullmatch(texto)
            if calce is not None:
                return con_tilde.format(
                    **{
                        nombre: presentar[nombre](valor) if nombre in presentar else valor
                        for nombre, valor in calce.groupdict().items()
                    }
                )
        return texto

    return corregir


_NO_APLICA = re.compile(r"no aplica \((?P<lista>.+)\)", re.DOTALL)
_CORREGIR_FRASE = catalogo_de_frases(PLANTILLAS_DEL_NUCLEO)


def con_tildes(texto: str) -> str:
    """Restituye las tildes de una frase fija del núcleo; cualquier otro texto pasa sin cambios.

    Función pura, sin recursión y de costo lineal. Solo actúa si la frase COMPLETA coincide con una
    plantilla del catálogo, de modo que un nombre de partida con «dia» o «ningun» puesto por el
    usuario no se altera.

    Límite conocido: el núcleo arma el desglose con `"; ".join(f"{c}: {m}" ...)` (recuperacion.py,
    intocable), así que un código de partida que contenga «; » y «: » es ambiguo con dos items y
    solo se corrige lo que calce con un motivo del conjunto cerrado. El tope de largo vale solo
    para el catálogo de regex; el desglose es lineal (split, rpartition, dict) y no lo necesita.
    """
    desglose = _NO_APLICA.fullmatch(texto)
    if desglose is not None:
        # «no aplica (cod: motivo; cod: motivo)»: el código es del usuario; solo el motivo, a la
        # derecha del último «: », se busca en el conjunto cerrado del núcleo.
        items = []
        for item in desglose.group("lista").split("; "):
            codigo, separador, motivo = item.rpartition(": ")
            corregido = _MOTIVOS_POR_PARTIDA.get(motivo)
            items.append(f"{codigo}{separador}{corregido}" if separador and corregido else item)
        return "no aplica (" + "; ".join(items) + ")"
    return _CORREGIR_FRASE(texto)


def alertas_en_filas(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Las alertas que saltaron y, aparte, las que no se pudieron evaluar con su motivo."""
    filas = [
        {
            "Alerta": a.codigo,
            "Severidad": a.severidad.name,
            "Descripcion": con_tildes(a.descripcion),
            "Observado": ""
            if a.valor_observado is None
            else formatear_decimal(a.valor_observado, 4),
            "Umbral": ("" if a.umbral is None else formatear_decimal(a.umbral, 4))
            + f" ({a.naturaleza_umbral})",
        }
        for a in resultado.alertas.alertas
    ]
    filas.extend(
        {
            "Alerta": codigo,
            "Severidad": "sin evaluar",
            "Descripcion": con_tildes(motivo),
            "Observado": "",
            "Umbral": "",
        }
        for codigo, motivo in resultado.alertas.no_evaluadas.items()
    )
    return filas


def filas_de_reproyeccion(resultado: ResultadoControl) -> list[dict[str, str]]:
    """Por partida con obra pendiente: su índice, el día hábil en que termina y su nota."""
    filas = []
    for p in resultado.reproyeccion.partidas:
        if p.pendiente == 0:
            continue
        nota = con_tildes(p.motivo) or (
            "detenida"
            if p.detenida
            else "sin evidencia propia: SPI global"
            if p.sin_evidencia
            else ""
        )
        filas.append(
            {
                "Partida": p.codigo,
                "Indice": _indice(p.indice),
                "Fin (dia habil)": NO_DISPONIBLE if p.fin is None else formatear_decimal(p.fin, 2),
                "Nota": nota,
            }
        )
    return filas


def supuestos_de_opcion(opcion: Opcion) -> list[dict[str, str]]:
    """Los supuestos de una opción que aplica, cada uno en sus tres ranuras (nombre y valor con
    tilde, naturaleza tal cual): así el front los presenta por separado sin reescribir un texto
    armado que trae códigos del usuario (VD-1). La que no aplica no lista supuestos."""
    if not opcion.aplica:
        return []
    return [
        {"nombre": con_tildes(s.nombre), "valor": con_tildes(s.valor), "naturaleza": s.naturaleza}
        for s in opcion.supuestos
    ]


def filas_de_opciones(todas: Sequence[Opcion]) -> list[dict[str, str]]:
    """Una fila por opción con su término, sus costos, su punto de equilibrio y sus supuestos."""
    filas = []
    for o in todas:
        if not o.aplica:
            filas.append(
                {"Opcion": con_tildes(o.titulo), "Nota": con_tildes(o.motivo)}
                | dict.fromkeys(COLUMNAS_OPCIONES[1:-1], NO_APLICA)
            )
            continue
        pe = NO_APLICA
        if o.equilibrio is not None:
            pe = _monto(o.equilibrio.punto) + f" ({con_tildes(o.equilibrio.mensaje)})"
        filas.append(
            {
                "Opcion": con_tildes(o.titulo),
                "Termino": f"día {o.termino}",
                "Retraso (dias)": str(o.retraso),
                "Costo directo adicional": _monto(o.costo_directo_adicional),
                "Costo indirecto": _monto(o.costo_indirecto),
                "Penalizacion": _monto(o.penalizacion),
                "Punto de equilibrio": pe,
                "Nota": "; ".join(
                    f"{s['nombre']}: {s['valor']} ({s['naturaleza']})"
                    for s in supuestos_de_opcion(o)
                ),
            }
        )
    return filas


def filas_de_decisiones(sesion: Session, proyecto: str) -> list[dict[str, str]]:
    """Las decisiones de recuperación del proyecto."""
    return [
        {
            "Version": d.version,
            "Opcion": d.opcion,
            "Corte": f"{d.fecha_corte:%d/%m/%Y}",
            "Termino": f"{d.termino:%d/%m/%Y}",
            "Fuente": d.fuente,
            "Responsable": d.responsable,
        }
        for d in decisiones(sesion, proyecto)
    ]


def tablas_de_control(
    sesion: Session,
    proyecto: str,
    catalogo: Catalogo,
    *,
    precios: PreciosDelCorte | None = None,
) -> list[TablaExportable]:
    """Las hojas «Valuaciones», «Valor ganado» y «Decisiones» del Excel de la hoja (`hojas_extra`,
    SF-E4). Sin línea base de control (o sin valuaciones) no agrega ninguna: el Excel de la hoja
    conserva sus hojas y sale igual que antes."""
    try:
        corte = ultimo_corte(sesion, proyecto)  # nunca después de hoy
        resultado = calcular_control(
            sesion, proyecto, catalogo=catalogo, corte=corte, precios=precios
        )
    except (ValueError, LineaBaseInvalidada):
        return []
    anuladas = [
        v
        for v in valuaciones_registradas(sesion, proyecto, con_anuladas=True)
        if v.id not in {x.id for x in resultado.instantanea.valuaciones}
    ]
    valuaciones = tabla_valuaciones(
        resultado.instantanea.valuaciones,
        anuladas=anuladas,
        estados=estado_de_valuaciones(resultado),
    )
    filas = filas_de_indicadores(sesion, resultado) + alertas_en_filas(resultado)
    columnas = ("Indicador", "Valor", "En la otra moneda", "Nota")
    valor_ganado = TablaExportable(
        "Valor ganado",
        columnas,
        tuple(
            (
                f.get("Indicador") or f"{f['Alerta']} ({f['Severidad']})",
                f.get("Valor") or f.get("Observado", ""),
                f.get("En la otra moneda", ""),
                f.get("Nota") or f.get("Descripcion", ""),
            )
            for f in filas
        ),
    )
    decisiones_tabla = TablaExportable(
        "Decisiones",
        COLUMNAS_DECISIONES,
        tuple(
            tuple(f[c] for c in COLUMNAS_DECISIONES) for f in filas_de_decisiones(sesion, proyecto)
        ),
    )
    return [valuaciones, valor_ganado, decisiones_tabla]
