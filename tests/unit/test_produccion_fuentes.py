"""Registro de constantes de `produccion/` (RF-136): ninguna cifra de calculo sin fuente."""

from produccion.fuentes import CONSTANTES, Constante, EstadoDato


def test_ninguna_constante_de_calculo_es_a_cotejar_ni_sin_fuente():
    assert CONSTANTES, "el registro no puede estar vacio"
    malas = [
        c.nombre
        for c in CONSTANTES
        if c.usada_en_calculo and c.estado in (EstadoDato.A_COTEJAR, EstadoDato.SIN_FUENTE)
    ]
    assert not malas


def test_el_registro_trae_las_constantes_del_plan_con_su_estado():
    por_nombre = {c.nombre: c for c in CONSTANTES}
    esperadas = {
        "MAX_FILAS": "100000",
        "MAX_COLUMNAS": "60",
        "FILAS_DE_ENCABEZADO": "30",
        "TOLERANCIA_NETO_T": "0",
    }
    assert {n: por_nombre[n].valor for n in esperadas} == esperadas
    assert all(por_nombre[n].estado is EstadoDato.CONSTRUIDO for n in esperadas)
    assert len({c.nombre for c in CONSTANTES}) == len(CONSTANTES)


def test_una_constante_a_cotejar_usada_en_calculo_seria_detectada():
    mala = Constante("X", "1", EstadoDato.A_COTEJAR, "F-1", usada_en_calculo=True)
    assert mala.estado in (EstadoDato.A_COTEJAR, EstadoDato.SIN_FUENTE) and mala.usada_en_calculo
