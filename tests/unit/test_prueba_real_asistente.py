"""La prueba manual con la API real, SIN la red (S4 §10.2; plan 0.9.0, tarea 13).

`scripts/prueba_real_asistente.py` es una prueba MANUAL que gasta dinero: llama a la API de pago
solo con `--acepto-costo` y la autorizacion de gasto de Eugenio (bitacora 0.9.0: nunca se corrio).
Aqui se prueba todo lo que no depende de la red: la negativa sin `--acepto-costo`, que una tarea
de evaluacion no se corre antes de medir, el resumen (costo calculado a mano), la anotacion en la
bitacora, el grabador y su reproduccion, `main` completo con un proveedor guionado en lugar del
real, y `scripts/_experimento.py` (el contexto y la clave tomada del almacen, nunca de argv ni del
entorno). La llamada real a la API queda FUERA de la CI por diseno: no aplica.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from asistente.clave import SERVICIO
from asistente.proveedores.base import FinTurno, LlamadaHerramienta, Tarifa, Turno, Uso
from asistente.proveedores.guionado import ProveedorGuionado, guion_desde_archivo
from scripts import _experimento
from scripts import prueba_real_asistente as script
from scripts.prueba_real_asistente import ProveedorGrabador, anotar, correr, main, resumen
from tests.fixtures import caso_of001, caso_ti001
from tests.fixtures.asistente_banco import catalogo_del_experimento
from tests.fixtures.asistente_clave import AlmacenFalso

HOY = date(2026, 10, 11)


def guion() -> ProveedorGuionado:
    llamadas = (LlamadaHerramienta("t", "terminar", {"notas": ["nada que proponer"]}),)
    uso = Uso(entrada=1000, salida=200, cache_lectura=600)
    turno = Turno("", llamadas, FinTurno.HERRAMIENTAS, uso, "claude-opus-5-5")
    return ProveedorGuionado([turno], nombre="claude", modelo="claude-opus-5-5")


def test_sin_acepto_costo_se_niega_y_no_toca_la_red(capsys, monkeypatch):
    def no_debe_llamarse(*args, **kwargs):
        raise AssertionError("sin --acepto-costo no se construye el proveedor real")

    monkeypatch.setattr(_experimento, "proveedor_real", no_debe_llamarse)
    assert main(["--proveedor", "claude", "--tarea", "dev-agua-01"]) == 2
    assert "--acepto-costo" in capsys.readouterr().err


def test_un_proveedor_desconocido_lo_rechaza_argparse(capsys):
    with pytest.raises(SystemExit) as salida:
        main(["--proveedor", "otro", "--tarea", "dev-agua-01", "--acepto-costo"])
    assert salida.value.code == 2


def test_una_tarea_de_evaluacion_no_se_corre_antes_de_medir():
    proveedor = guion()
    tarifa = Tarifa(Decimal(1), Decimal(1))
    with pytest.raises(SystemExit, match="no es de desarrollo"):
        correr(proveedor, "ev-agua-01", tarifa, catalogo_del_experimento(), {}, HOY)
    assert proveedor.recibidos == []  # ni un turno


def test_el_resumen_trae_fichas_cache_costo_modelo_y_se_anota_en_la_bitacora(tmp_path):
    tarifa = Tarifa(entrada=Decimal(4), salida=Decimal(20), cache_lectura=Decimal("0.2"))
    proveedor = guion()
    resultado = correr(
        proveedor,
        "dev-agua-01",
        tarifa,
        catalogo_del_experimento(),
        caso_of001.COMPOSICIONES,
        HOY,
    )
    lineas = resumen(resultado, proveedor)
    assert lineas[0] == "proveedor: claude; modelo pedido: claude-opus-5-5"
    assert lineas[1] == "modelo que respondio: claude-opus-5-5"
    assert lineas[2] == "fin: terminar; turnos: 1; llamadas: 1"
    assert lineas[3] == (
        "fichas: entrada 1000, salida 200, cache_read_input_tokens 600, cache_creation 0"
    )
    # 1000*4/1e6 + 200*20/1e6 + 600*0,2/1e6 = 0,004 + 0,004 + 0,00012 = 0,00812 -> 0.0081
    assert lineas[4] == "costo estimado: 0.0081 USD"
    assert lineas[5] == "propuestas: ninguna"
    assert lineas[6] == "rechazos por causa: ninguno"
    bitacora = tmp_path / "bitacora.md"
    anotar(lineas, "dev-agua-01", HOY, bitacora)
    anotar(lineas, "dev-agua-01", HOY, bitacora)  # se AGREGA, no se reemplaza
    texto = bitacora.read_text(encoding="utf-8")
    assert texto.count("## Prueba real 2026-10-11: dev-agua-01") == 2
    assert "- costo estimado: 0.0081 USD" in texto and "sk-ant" not in texto


def test_el_grabador_guarda_los_turnos_y_el_guionado_los_reproduce_igual(tmp_path):
    grabador = ProveedorGrabador(guion())
    original = grabador.turno("sistema", [], [])
    ruta = tmp_path / "grabaciones" / "claude.json"
    grabador.guardar(ruta)
    (reproducido,) = guion_desde_archivo(ruta)
    assert (reproducido.llamadas, reproducido.fin, reproducido.uso) == (
        original.llamadas,
        original.fin,
        original.uso,
    )
    assert reproducido.modelo_que_respondio == "claude-opus-5-5"
    assert grabador.nombre == "claude" and grabador.disponible().disponible
    assert "sk-ant" not in ruta.read_text(encoding="utf-8")


def test_main_con_acepto_costo_corre_anota_y_graba_con_un_proveedor_guionado(
    tmp_path, monkeypatch, capsys
):
    """Todo `main` sin red: el proveedor «real» es un guionado y la bitacora, temporal."""
    pedidos = []

    def proveedor_falso(nombre, protocolo, empresa):
        pedidos.append((nombre, protocolo["modelo_claude"], protocolo["esfuerzo"], empresa))
        return guion()

    anotadas = []
    monkeypatch.setattr(_experimento, "proveedor_real", proveedor_falso)
    monkeypatch.setattr(
        script, "anotar", lambda lineas, tarea, hoy: anotadas.append((tuple(lineas), tarea))
    )
    grabacion = tmp_path / "grabado.json"
    argv = ["--proveedor", "claude", "--tarea", "dev-agua-01", "--acepto-costo"]
    assert main([*argv, "--grabar", str(grabacion)]) == 0
    assert pedidos == [("claude", "claude-opus-5-5", "high", "EMPRESA-PROPIA")]
    salida = capsys.readouterr().out
    assert "costo estimado: 0.0081 USD" in salida  # la tarifa real de Opus 5.5 (4/20/0,20)
    assert [t for _, t in anotadas] == ["dev-agua-01"]
    assert [t.fin for t in guion_desde_archivo(grabacion)] == [FinTurno.HERRAMIENTAS]


def test_main_con_el_proveedor_no_disponible_sale_con_3(monkeypatch, capsys):
    class NoDisponible(ProveedorGuionado):
        def disponible(self):
            from asistente.proveedores.base import Disponibilidad

            return Disponibilidad(False, "Falta registrar la clave de IA de la empresa.")

    monkeypatch.setattr(_experimento, "proveedor_real", lambda *a: NoDisponible([]))
    argv = ["--proveedor", "claude", "--tarea", "dev-agua-01", "--acepto-costo"]
    assert main(argv) == 3
    assert "Falta registrar la clave" in capsys.readouterr().err


# --- scripts/_experimento.py -----------------------------------------------------------------


def test_el_contexto_del_experimento_une_of001_y_ti001():
    banco, composiciones, catalogo, codigos, referencia_de = _experimento.contexto_del_experimento()
    assert len(banco) == 16  # 4 de desarrollo + 12 de evaluacion (bitacora T2)
    assert sum(f.conjunto == "desarrollo" for f in banco.values()) == 4
    assert len(composiciones) == 30 + 10  # OF-001 y TI-001, sin codigos repetidos
    assert set(composiciones) == set(caso_of001.COMPOSICIONES) | set(caso_ti001.COMPOSICIONES)
    assert len(codigos) == 40 and all(unidad for _, unidad in codigos)
    assert catalogo.partida(next(iter(caso_ti001.COMPOSICIONES))) is not None
    assert callable(referencia_de)


def test_el_proveedor_real_de_claude_toma_la_clave_del_almacen_sin_respaldo(monkeypatch):
    """Sin red: el proveedor se construye pero no se llama. La clave sale del almacen (nunca de
    un argumento ni del entorno) y el respaldo del servidor va DESACTIVADO (RS4-7)."""
    almacen = AlmacenFalso()
    almacen.set_password(SERVICIO, "EMP", "sk-ant-api03-DEL-ALMACEN-4321")
    monkeypatch.setattr("asistente.clave.almacen_del_sistema", lambda: almacen)

    def sin_contrasena(*args, **kwargs):
        raise AssertionError("sin respaldo cifrado no se pide contrasena")

    monkeypatch.setattr("getpass.getpass", sin_contrasena)
    protocolo = {"modelo_claude": "claude-opus-5-5", "esfuerzo": "high"}
    proveedor = _experimento.proveedor_real("claude", protocolo, "EMP")
    assert proveedor.nombre == "claude" and proveedor.modelo == "claude-opus-5-5"
    assert proveedor._con_respaldo is False and proveedor._esfuerzo == "high"
    assert proveedor._clave == "sk-ant-api03-DEL-ALMACEN-4321"


def test_el_proveedor_real_sin_clave_registrada_falla_antes_de_la_red(monkeypatch):
    from asistente.clave import ClaveNoRegistrable

    monkeypatch.setattr("asistente.clave.almacen_del_sistema", lambda: AlmacenFalso())
    with pytest.raises(ClaveNoRegistrable, match="No hay una clave"):
        _experimento.proveedor_real("claude", {"modelo_claude": "m", "esfuerzo": "high"}, "EMP")


def test_el_proveedor_real_local_usa_la_version_minima_del_repositorio():
    proveedor = _experimento.proveedor_real("ollama", {"modelo_local": "muse-glimmer"}, "EMP")
    assert proveedor.nombre == "ollama" and proveedor.modelo == "muse-glimmer"
    assert proveedor._version_minima == (0, 35, 0)
