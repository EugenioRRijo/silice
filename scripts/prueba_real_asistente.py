"""Prueba manual declarada del asistente con la API REAL o con el modelo local (S4 §10.2).

    uv run python scripts/prueba_real_asistente.py --proveedor claude|ollama
        --tarea <tarea de desarrollo> --acepto-costo [--grabar <archivo.json>]

Corre UNA tarea de DESARROLLO (nunca una de evaluacion: esas no se ven antes de medir, §9.1), exige
`--acepto-costo` (el gasto lo autoriza una persona, nunca el plan), toma la clave del almacen de
credenciales (jamas de un argumento) e imprime fichas, `cache_read_input_tokens`, costo, modelo que
respondio y propuestas. Agrega una entrada a `docs/bitacora/2026-10-silice-090.md`. No corre en la
CI. `--grabar` guarda los turnos (texto, llamadas, fin, fichas y modelo; nunca la clave ni los
encabezados) en el JSON que reproduce `asistente.proveedores.guionado.guion_desde_archivo`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from asistente.experimento.banco import borrador_de_partida, cargar_banco  # noqa: E402
from asistente.orquestador import ResultadoSesion, Servicios, Topes, ejecutar  # noqa: E402
from asistente.proveedores.base import ProveedorIA, Tarifa, Turno  # noqa: E402

BITACORA = RAIZ / "docs" / "bitacora" / "2026-10-silice-090.md"


def resumen(resultado: ResultadoSesion, proveedor: ProveedorIA) -> list[str]:
    """Las lineas que se imprimen y se anotan en la bitacora (sin la clave ni encabezados)."""
    uso = resultado.uso
    return [
        f"proveedor: {proveedor.nombre}; modelo pedido: {proveedor.modelo}",
        f"modelo que respondio: {', '.join(resultado.modelos) or '-'}",
        f"fin: {resultado.motivo.value}; turnos: {resultado.turnos}; "
        f"llamadas: {resultado.llamadas}",
        f"fichas: entrada {uso.entrada}, salida {uso.salida}, "
        f"cache_read_input_tokens {uso.cache_lectura}, cache_creation {uso.cache_escritura}",
        f"costo estimado: {resultado.costo:.4f} USD",
        "propuestas: "
        + (", ".join(f"{p.id} ({p.tipo.value})" for p in resultado.propuestas) or "ninguna"),
        f"rechazos por causa: {dict(resultado.rechazos_por_causa) or 'ninguno'}",
    ]


def anotar(lineas: Sequence[str], tarea: str, hoy: date, ruta: Path = BITACORA) -> None:
    entrada = [
        f"\n## Prueba real {hoy.isoformat()}: {tarea}\n",
        *(f"- {linea}" for linea in lineas),
    ]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as archivo:
        archivo.write("\n".join(entrada) + "\n")


class ProveedorGrabador:
    """Envuelve un proveedor y guarda cada `Turno` que devuelve (para las grabaciones)."""

    def __init__(self, proveedor: ProveedorIA) -> None:
        self._proveedor = proveedor
        self.nombre, self.modelo = proveedor.nombre, proveedor.modelo
        self.envia_fuera_del_equipo = proveedor.envia_fuera_del_equipo
        self.turnos: list[Turno] = []

    def disponible(self):
        return self._proveedor.disponible()

    def turno(self, sistema, mensajes, herramientas) -> Turno:
        turno = self._proveedor.turno(sistema, mensajes, herramientas)
        self.turnos.append(turno)
        return turno

    def guardar(self, ruta: Path) -> None:
        datos = [
            {
                "texto": t.texto,
                "llamadas": [
                    {"id": c.id, "nombre": c.nombre, "argumentos": dict(c.argumentos)}
                    for c in t.llamadas
                ],
                "fin": t.fin.value,
                "uso": asdict(t.uso),
                "modelo": t.modelo_que_respondio,
            }
            for t in self.turnos
        ]
        ruta.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(datos, indent=1, ensure_ascii=False) + "\n"
        ruta.write_bytes(texto.encode("utf-8"))


def auditar(borrador):
    """El informe con que el asistente ve cada propuesta, como en el producto: R1 a R15 mas R17
    ligada al espacio del borrador que se audita (tarea 1.7, ruling 1.7-d)."""
    from dataclasses import replace

    from adapters.espacio.conexion import CODIGO_R17, reglas_conexion
    from ui import hoja

    otras = tuple(r for r in borrador.reglas_extra if r.codigo != CODIGO_R17)
    ligado = replace(borrador, reglas_extra=(*otras, *reglas_conexion(borrador.espacio)))
    return hoja.elaborar_borrador(ligado).elaboracion.informe


def correr(
    proveedor: ProveedorIA, tarea: str, tarifa: Tarifa, catalogo, composiciones, hoy: date
) -> ResultadoSesion:
    ficha = cargar_banco()[tarea]
    if ficha.conjunto != "desarrollo":
        raise SystemExit(
            f"{tarea} no es de desarrollo: las de evaluacion no se ven antes de medir."
        )
    from dataclasses import replace

    borrador = replace(borrador_de_partida(ficha, hoy), composiciones=composiciones)
    servicios = Servicios(
        catalogo=catalogo,
        tarifa=tarifa,
        auditar=auditar,
        responder=lambda _pregunta: None,
    )
    return ejecutar(proveedor, ficha.pedido, borrador, servicios, Topes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proveedor", choices=("claude", "ollama"), required=True)
    parser.add_argument("--tarea", required=True)
    parser.add_argument("--empresa", default="EMPRESA-PROPIA")
    parser.add_argument("--grabar", type=Path)
    parser.add_argument("--acepto-costo", action="store_true")
    args = parser.parse_args(argv)
    if not args.acepto_costo:
        print(
            "Falta --acepto-costo: la prueba real gasta dinero y la autoriza una persona.",
            file=sys.stderr,
        )
        return 2
    from scripts._experimento import contexto_del_experimento, proveedor_real

    protocolo = json.loads(
        (RAIZ / "asistente" / "experimento" / "protocolo.json").read_text(encoding="utf-8")
    )
    proveedor = proveedor_real(args.proveedor, protocolo, args.empresa)
    if args.grabar:
        proveedor = ProveedorGrabador(proveedor)
    disponibilidad = proveedor.disponible()
    if not disponibilidad.disponible:
        print(disponibilidad.motivo, file=sys.stderr)
        return 3
    from asistente.tarifas import tarifa_de

    _, composiciones, catalogo, _, _ = contexto_del_experimento()
    tarifa = tarifa_de(proveedor.modelo, local=args.proveedor == "ollama")
    resultado = correr(proveedor, args.tarea, tarifa, catalogo, composiciones, date.today())
    lineas = resumen(resultado, proveedor)
    print("\n".join(lineas))
    anotar(lineas, args.tarea, date.today())
    if args.grabar:
        proveedor.guardar(args.grabar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
