"""Lectura sin conexion de los archivos del BCV (spec S1 §7): `libro` da la cuadricula neutra;
`tasa`, `inpc` y `csv_canonico` la interpretan; `informe` tiene los tipos propios y `formatos` lo
que S1-0 verifico en los archivos reales. No implementa `AdaptadorDominio` ni importa `core`
(S1 §4.1). Este paquete no importa sus modulos: `xlrd` y `openpyxl` se cargan solo al leer."""
