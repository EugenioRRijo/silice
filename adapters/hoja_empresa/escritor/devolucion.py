"""`escribir_devolucion`: el libro calcado (spec 1.5, F-D3 a F-D10).

Pasos:

1. Abrir el libro recibido con openpyxl (estilos, fórmulas, imágenes; sin VBA ni vínculos).
2. Decidir qué sale: todas las hojas en su orden, salvo AUX y los APU que no están unidos a ninguna
   partida (plantillas), más AUDITORÍA, TRAZABILIDAD y ALERTAS USD-Bs al final.
3. APU unidos → maqueta uniforme (`apu`); PRESUPUESTO → mismas filas con fórmulas por nombre
   (`presupuesto`); el resto → copia celda a celda con las reglas de `derivadas`.
4. Sembrar los valores de Silice (componentes, P.U., cantidades y totales), sustituir por su valor
   las fórmulas que no se pueden conservar y calcular todas las demás (`calculos`).
5. Extender el cronograma si la obra lo necesita (`programacion`) y volcar con XlsxWriter
   (`salida`).

Todo cambio del calcado respecto del libro recibido (hojas omitidas, fórmulas sustituidas por su
valor, fórmulas peligrosas pasadas a valor, valores guardados conservados, filas añadidas, gráficos
omitidos, APU sin cálculo de Silice) se anota una vez en `LibroSalida.notas`: va a TRAZABILIDAD
("Transformaciones del calcado") y, como lista estructurada (`transformaciones_del_calcado`), a la
sección "Cambios del calcado" de AUDITORÍA.
"""

from __future__ import annotations

import io
import re
import unicodedata
import warnings
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from adapters.hoja_empresa.escritor.apu import (
    DatosApu,
    Kit,
    extraer_kit,
    generar_apu,
    mapa_filas,
    maqueta_del_libro,
)
from adapters.hoja_empresa.escritor.calculos import Err, Evaluador, NoSoportado
from adapters.hoja_empresa.escritor.contexto import ERRORES, Contexto
from adapters.hoja_empresa.escritor.copia import Aviso, aspecto_de_hoja, copiar_hoja
from adapters.hoja_empresa.escritor.derivadas import anotar_pendiente, transformar_hoja
from adapters.hoja_empresa.escritor.estilos import LectorEstilos
from adapters.hoja_empresa.escritor.formulas import letra, motivo_peligro
from adapters.hoja_empresa.escritor.graficos import leer_graficos
from adapters.hoja_empresa.escritor.hoja import NADA, Nota
from adapters.hoja_empresa.escritor.presupuesto import regenerar_presupuesto, sembrar_totales
from adapters.hoja_empresa.escritor.procura import ajustar_procura
from adapters.hoja_empresa.escritor.programacion import extender_semanas
from adapters.hoja_empresa.escritor.salida import escribir_xlsx, revisar_grafico
from adapters.hoja_empresa.escritor.silice import hoja_alertas, hoja_auditoria, hoja_trazabilidad
from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.modelo import ApuCalculado, ApuLeido, DatosDevolucion, Rotulo, clave
from adapters.hoja_empresa.perfil import Perfil, cargar_perfil

__all__ = [
    "CODIGOS_TRANSFORMACION",
    "TITULO_DEVUELTO",
    "escribir_devolucion",
    "transformaciones_del_calcado",
]

_CERO = Decimal(0)
#: Título del documento devuelto: no se conserva el del libro recibido (revisión de seguridad 1.5).
TITULO_DEVUELTO = "Libro devuelto por Silice"

#: Código corto de cada clase de transformación del calcado (el `dato` de la nota).
CODIGOS_TRANSFORMACION: dict[str, str] = {
    "Hoja que no sale en la devolución": "HOJA-OMITIDA",
    "APU sin cálculo de Silice": "APU-SIN-CALCULO",
    "Fórmula sustituida por su valor": "FORMULA-A-VALOR",
    "Fórmula peligrosa pasada a valor": "FORMULA-PELIGROSA",
    "Validación omitida": "VALIDACION-OMITIDA",
    "Formato condicional omitido": "FORMATO-OMITIDO",
    "Nombre definido omitido": "NOMBRE-OMITIDO",
    "Valor guardado conservado": "VALOR-CONSERVADO",
    "Filas añadidas a PROCURA": "FILAS-ANADIDAS",
    "Semanas del cronograma": "SEMANAS-ANADIDAS",
    "Semanas del cronograma no añadidas": "SEMANAS-NO-ANADIDAS",
    "Gráfico omitido": "GRAFICO-OMITIDO",
    "Paneles inmovilizados omitidos": "PANELES-OMITIDOS",
    "Partida sin APU unido": "PARTIDA-SIN-APU",
}
_MAX_DESCRIPCION = 500


def _codigo(dato: str) -> str:
    codigo = CODIGOS_TRANSFORMACION.get(dato)
    if codigo is not None:
        return codigo
    plano = unicodedata.normalize("NFKD", dato).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "-", plano.upper()).strip("-")[:24] or "OTRO"


def transformaciones_del_calcado(notas: Sequence[Nota]) -> list[tuple[str, str, str]]:
    """Las notas del calcado como (tipo, celda, descripción), en el orden en que se hicieron.

    `tipo` es el código corto (`CODIGOS_TRANSFORMACION`); `celda`, la celda u hoja de origen
    (HOJA!CELDA); `descripción`, qué se cambió y por qué, con el valor escrito si lo hay. Es lo que
    lista la sección "Cambios del calcado" de AUDITORÍA; TRAZABILIDAD lleva las mismas notas.
    """
    out: list[tuple[str, str, str]] = []
    for n in notas:
        desc = f"{n.dato}: {n.nota}"
        if n.valor and n.valor != n.origen:
            desc += f" (valor escrito: {n.valor})"
        if len(desc) > _MAX_DESCRIPCION:
            desc = desc[: _MAX_DESCRIPCION - 1] + "…"
        out.append((_codigo(n.dato), n.origen, desc))
    return out


def _anotar_avisos(ctx: Contexto, avisos: Sequence[Aviso]) -> None:
    """Lo que `copia` no copió tal cual (fórmulas peligrosas, validaciones, formatos condicionales,
    paneles), a las transformaciones."""
    for dato, ref, original, motivo in avisos:
        ctx.salida.anotar(dato, None, ref, f"{motivo}: {original[:300]}")


def _abrir(origen: bytes):  # noqa: ANN202 - openpyxl.Workbook
    import openpyxl

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return openpyxl.load_workbook(
                io.BytesIO(origen), data_only=False, keep_vba=False, keep_links=False
            )
    except Exception as exc:  # openpyxl lanza tipos muy variados ante un XML dañado
        raise ArchivoRechazado(
            "No se pudo abrir el libro recibido para escribir la devolución."
        ) from exc


def _calculado_de_respaldo(a: ApuLeido) -> tuple[ApuCalculado, list[str]]:
    """El APU con los valores guardados en el libro, y los rótulos que no tenían valor (van a 0).

    Solo se usa cuando Silice no trae el cálculo de ese APU; quien lo llama lo anota en las
    transformaciones del calcado (nunca es silencioso).
    """
    g = a.guardados
    faltan: list[str] = []

    def v(r: Rotulo) -> Decimal:
        if r not in g:
            faltan.append(r.value)
        return g.get(r, _CERO)

    calc = ApuCalculado(
        hoja=a.hoja,
        materiales=v(Rotulo.MAT),
        mano_obra=v(Rotulo.MO),
        equipos=v(Rotulo.EQ),
        transporte=v(Rotulo.TR),
        costo_directo=v(Rotulo.CD),
        administracion=v(Rotulo.ADM),
        subtotal=v(Rotulo.SUB),
        utilidad=v(Rotulo.UTI),
        precio_unitario=v(Rotulo.PU),
        base_mo_dia=v(Rotulo.BASE_MO),
        equipos_dia=v(Rotulo.EQ_DIA),
        herramientas=v(Rotulo.HERR),
    )
    return calc, faltan


def _kit(ctx: Contexto) -> Kit:
    for hoja in ctx.unidos:
        a = ctx.apu(hoja)
        if a is None:
            continue
        ws = ctx.wb[hoja]
        anchos, impresion = aspecto_de_hoja(ws)
        return extraer_kit(ws, a, ctx.perfil, ctx.estilos, impresion, anchos)
    kit = Kit()
    p = ctx.perfil.paleta
    from adapters.hoja_empresa.escritor.estilos import Estilo

    base = Estilo(fuente=ctx.perfil.fuente, tamano=9, color=p.get("texto"))
    kit.base = base
    kit.estilos["titulo"] = {
        c: base.con(negrita=True, color=p.get("blanco"), patron=1, fondo=p.get("titulo"))
        for c in range(1, 9)
    }
    kit.estilos["enc_mat"] = {
        c: base.con(negrita=True, color=p.get("blanco"), patron=1, fondo=p.get("encabezado"))
        for c in range(1, 9)
    }
    kit.estilos["sub_mat"] = {
        c: base.con(negrita=True, color=p.get("titulo"), patron=1, fondo=p.get("subtotal"))
        for c in range(1, 9)
    }
    kit.estilos["nota"] = {c: base.con(color=p.get("texto_secundario")) for c in range(1, 9)}
    return kit


def _nota_original(ctx: Contexto, a: ApuLeido) -> str | None:
    """El primer texto de la columna de rótulos debajo del P.U. del APU original (su nota)."""
    celda = a.rotulos.get(Rotulo.PU)
    if celda is None:
        return None
    fila_pu = int("".join(ch for ch in celda.ref if ch.isdigit()))
    col = ctx.perfil.columna_rotulos_apu
    for f in range(fila_pu + 1, fila_pu + 8):
        v = ctx.libro.valores.get(clave(a.hoja, f"{col}{f}"))
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _construir(ctx: Contexto, kit: Kit) -> None:
    datos = ctx.datos
    salida = ctx.salida
    nombres_definidos = frozenset(k.rpartition("!")[2] for k in ctx.nombres)
    primero = next(iter(ctx.idents.values()), "APU_01")
    for nombre in ctx.wb.sheetnames:
        if nombre in ctx.quitadas:
            salida.anotar(
                "Hoja que no sale en la devolución",
                nombre,
                nombre,
                "AUX: la reemplazan referencias directas a los APU uniformes"
                if ctx.es(nombre, "AUX")
                else "APU sin partida unida (plantilla o ejemplo)",
            )
            continue
        if nombre in ctx.unidos:
            a = ctx.apu(nombre)
            assert a is not None and ctx.maqueta is not None
            calc = datos.apus.get(nombre)
            if calc is None:
                calc, faltan = _calculado_de_respaldo(a)
                nota = f"APU {nombre}: sin cálculo de Silice; se conservan los valores del libro"
                if faltan:
                    nota += f" (sin valor guardado, se escribe 0: {', '.join(faltan)})"
                salida.anotar("APU sin cálculo de Silice", None, nombre, nota)
            p = ctx.unidos[nombre]
            h = generar_apu(
                DatosApu(
                    apu=a,
                    calculado=calc,
                    fila_presupuesto=p.fila,
                    hoja_presupuesto=ctx.hoja_presupuesto,
                    parametros=ctx.libro.parametros,
                    nombres=nombres_definidos,
                    libro=ctx.libro,
                    perfil=ctx.perfil,
                    nota_extra=f"{primero}_PU, {primero}_REND",
                    nota_original=_nota_original(ctx, a),
                ),
                ctx.maqueta,
                kit,
            )
            salida.agregar(h)
            continue
        ws = ctx.wb[nombre]
        avisos: list[Aviso] = []
        h = copiar_hoja(ws, ctx.estilos, ctx.libro.valores, avisos=avisos)
        _anotar_avisos(ctx, avisos)
        resueltas: set[tuple[int, int]] = set()
        if nombre == ctx.hoja_presupuesto:
            resueltas = regenerar_presupuesto(ctx, h)
        salida.agregar(h)
        transformar_hoja(ctx, h, resueltas)


def _adjuntar_graficos(ctx: Contexto, origen: bytes) -> None:
    salen = set(ctx.salida.hojas) - set(ctx.unidos)
    for hoja, graficos in leer_graficos(origen).items():
        h = ctx.salida.hojas.get(hoja)
        for g in graficos:
            if h is None or hoja in ctx.unidos:
                continue
            if g.hojas - salen:
                ctx.salida.anotar(
                    "Gráfico omitido",
                    g.titulo or g.tipo,
                    hoja,
                    f"lee hojas que no salen o cambian de forma: {sorted(g.hojas - salen)}",
                )
                continue
            h.graficos.append(g)


def _revisar_graficos(ctx: Contexto) -> None:
    """Un gráfico que no se puede escribir (serie peligrosa, XlsxWriter lo rechaza) se omite y se
    anota; se revisa después de extender el cronograma, que cambia sus series."""
    for h in ctx.salida.hojas.values():
        quedan = []
        for g in h.graficos:
            motivo = revisar_grafico(h, g)
            if motivo is None:
                quedan.append(g)
            else:
                ctx.salida.anotar("Gráfico omitido", g.titulo or g.tipo, h.nombre, motivo)
        h.graficos = quedan


def _peligrosas_a_valor(ctx: Contexto) -> None:
    """Barrera antes de escribir: ninguna fórmula que la lista negra rechaza llega a la salida
    (las del libro recibido ya las convirtió `copia`; esto cubre cualquier otra vía)."""
    for h in ctx.salida.hojas.values():
        for (f, c), cel in h.celdas.items():
            motivo = motivo_peligro(cel.formula) if cel.formula else None
            if motivo is None or cel.formula is None:
                continue
            valor = cel.fijo if cel.fijo is not NADA else cel.calculado
            valor = cel.respaldo if valor is NADA or isinstance(valor, Err) else valor
            ctx.salida.anotar(
                "Fórmula peligrosa pasada a valor",
                valor,
                clave(h.nombre, f"{letra(c)}{f}"),
                f"{motivo}: {cel.formula[:300]}",
            )
            cel.formula, cel.valor, cel.fijo = None, valor, NADA


def _resolver_pendientes(ctx: Contexto, ev: Evaluador) -> None:
    for hoja, f, c, original, motivo in ctx.pendientes:
        cel = ctx.salida.hojas[hoja].celdas[(f, c)]
        resp = cel.respaldo
        if resp is not None and not (isinstance(resp, str) and resp.strip() in ERRORES):
            valor: object = resp
        else:
            ev.rota_blanca = True
            try:
                valor = ev.formula(original, hoja, f, c)
            except (NoSoportado, RecursionError):
                valor = None
            finally:
                ev.rota_blanca = False
            if isinstance(valor, Err):
                valor = None
        cel.valor = valor
        anotar_pendiente(ctx, hoja, f, c, valor, f"{motivo}: {original}")
    ev.olvidar()


def _orden_evaluacion(ctx: Contexto) -> list[str]:
    primero = [n for n in ctx.salida.orden if ctx.es(n, "INSUMOS")]
    primero += [n for n in ctx.salida.orden if ctx.es(n, "PORTADA") or ctx.es(n, "MEDICIONES")]
    primero += [n for n in ctx.salida.orden if n in ctx.unidos]
    primero += [n for n in ctx.salida.orden if n == ctx.hoja_presupuesto]
    return primero + [n for n in ctx.salida.orden if n not in primero]


def _evaluar(ctx: Contexto, ev: Evaluador, hojas: list[str]) -> None:
    """Calcula cada fórmula. `Evaluador.celda` no deja escapar `RecursionError`: una cadena de
    referencias demasiado profunda conserva el valor guardado y queda anotada en `ev.respaldos`."""
    for nombre in hojas:
        h = ctx.salida.hojas[nombre]
        for (f, c), cel in sorted(h.celdas.items()):
            if cel.formula:
                cel.calculado = ev.celda(nombre, f, c)


#: Excel no abre un libro con una fórmula de más de 8 192 caracteres.
_MAX_FORMULA = 8000


def _largas_a_valor(ctx: Contexto) -> None:
    """Una fórmula demasiado larga para Excel (la explosión de PROCURA de un libro con muchísimos
    APU) se escribe como su valor y queda anotada."""
    for h in ctx.salida.hojas.values():
        for (f, c), cel in h.celdas.items():
            if cel.formula and len(cel.formula) > _MAX_FORMULA:
                valor = cel.fijo if cel.fijo is not NADA else cel.calculado
                ctx.salida.anotar(
                    "Fórmula sustituida por su valor",
                    valor,
                    clave(h.nombre, f"{letra(c)}{f}"),
                    f"la fórmula tiene {len(cel.formula)} caracteres y Excel admite 8 192",
                )
                cel.formula, cel.valor, cel.fijo = None, valor, NADA


def _fecha_creacion(texto: str) -> datetime:
    """La fecha de la devolución como fecha de creación del documento: la misma entrada da los
    mismos bytes (XlsxWriter pondría la hora del reloj)."""
    try:
        return datetime.fromisoformat(texto[:10])
    except ValueError:
        return datetime(2000, 1, 1)


def escribir_devolucion(
    origen: bytes, datos: DatosDevolucion, perfil: Perfil | None = None
) -> bytes:
    """Devuelve los bytes del `.xlsx` calcado con los valores de Silice y las tres hojas nuevas."""
    perfil = perfil or cargar_perfil(datos.libro.perfil)
    wb = _abrir(origen)
    try:
        estilos = LectorEstilos(getattr(wb, "loaded_theme", None))
        ctx = Contexto(datos=datos, perfil=perfil, wb=wb, estilos=estilos)
        ctx.preparar()
        unidos = [a for h in ctx.unidos if (a := ctx.apu(h)) is not None]
        ctx.maqueta = maqueta_del_libro(unidos)
        for a in unidos:
            ctx.mapas[a.hoja] = mapa_filas(wb[a.hoja], a, perfil, ctx.maqueta)
        ctx.preparar_nombres()
        kit = _kit(ctx)
        _construir(ctx, kit)
        _adjuntar_graficos(ctx, origen)
        ajustar_procura(ctx)
        sembrar_totales(ctx)

        ev = Evaluador(ctx.salida, ctx.nombres)
        _resolver_pendientes(ctx, ev)
        orden = _orden_evaluacion(ctx)
        _evaluar(ctx, ev, orden)
        if extender_semanas(ctx, ev):
            ev.olvidar()
            for h in ctx.salida.hojas.values():
                for cel in h.celdas.values():
                    cel.calculado = NADA
            _evaluar(ctx, ev, orden)
        _largas_a_valor(ctx)
        _peligrosas_a_valor(ctx)
        _revisar_graficos(ctx)
        for hoja, f, c, motivo in ev.respaldos:
            ctx.salida.anotar(
                "Valor guardado conservado",
                ctx.salida.hojas[hoja].celdas[(f, c)].respaldo,
                clave(hoja, f"{letra(c)}{f}"),
                f"el calculador de Silice no evalúa esta fórmula ({motivo})",
            )

        nuevas = (
            hoja_auditoria(
                datos, kit, transformaciones=transformaciones_del_calcado(ctx.salida.notas)
            ),
            hoja_trazabilidad(datos, ctx.salida.notas, kit),
            hoja_alertas(datos, kit),
        )
        for h in nuevas:
            nombre = h.nombre
            while nombre in ctx.salida.hojas:
                nombre = (nombre[:28] + " (S)")[:31]
            h.nombre = nombre
            ctx.salida.agregar(h)
        _evaluar(ctx, ev, [h.nombre for h in nuevas])

        meta = datos.metadatos
        ctx.salida.propiedades = {
            "created": _fecha_creacion(meta.get("fecha", "")),
            "title": TITULO_DEVUELTO,
            "author": "Silice",
            "company": "Silice",
            "comments": "Libro calcado por Silice: valores recalculados, hojas AUDITORÍA, "
            "TRAZABILIDAD y ALERTAS USD-Bs.",
        }
        ctx.salida.propiedades_extra = {
            "silice_sha256_origen": meta.get("sha256_origen") or datos.libro.sha256,
            "silice_version": meta.get("version", ""),
            "silice_fecha": meta.get("fecha", ""),
        }
        ctx.salida.nombres = dict(ctx.nombres)
    finally:
        wb.close()
    return escribir_xlsx(ctx.salida)
