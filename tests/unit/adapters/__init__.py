"""Pruebas del adaptador del BCV (spec S1 §7): archivo real contra `FUENTE.md` y cuadrículas.

Tres pruebas abren los `.xls` reales de `tests/fixtures/bcv/` y por eso necesitan `xlrd` (extra
`bcv`): `test_el_libro_real_abre_con_su_huella` (test_bcv_libro), `test_el_archivo_real_da_n_hojas_
y_coincide_con_la_transcripcion_a_mano` (test_bcv_tasa) y `test_el_archivo_real_coincide_con_la_
transcripcion_a_mano` (test_bcv_inpc). Corren donde `xlrd` está instalado (la CI, con `uv sync
--all-extras`; en local, `uv sync --extra bcv`). Donde falta fallan con `ModuleNotFoundError`: a
propósito NO llevan `skip`, `xfail` ni `importorskip`, para que una omisión silenciosa no esconda
el caso real. La lógica del lector (tope de hojas y de celdas, dimensiones) se prueba en cualquier
equipo con el `xlrd` falso de `tests/unit/test_bcv_libro_xls.py`.
"""
