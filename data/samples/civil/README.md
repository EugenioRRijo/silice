# Muestra civil: `tanquillas_y_zanja.csv`

Entrada del adaptador tabular (`adapters/civil/tabular.py`, Sesión I3.2): dos filas que reproducen
la geometría del caso de estudio de la línea base (`tests/fixtures/apu_linea_base.py`,
`GEOMETRIA_TANQUILLA`, `N_TANQUILLAS`, `ZANJA`, `LONGITUD_TUBERIA_M`).

## Columnas

`id,tipo,a,h,e,n,sobreancho,espesor_fondo,longitud,ancho,profundidad,diametro,desperdicio,especificaciones`

- La cabecera **debe traer las 13 primeras columnas** (de `id` a `desperdicio`), aunque una fila
  deje vacías las que no le aplican; `especificaciones` es opcional. Si falta alguna de las 13, el
  adaptador rechaza el archivo con «el archivo '…' no es una fuente del dominio civil: faltan las
  columnas [...]» (así la muestra de otro dominio, que también trae `id` y `tipo`, no pasa por
  civil; INV‑089, fase C5). Una celda vacía o no numérica en una columna que la fila usa se rechaza
  nombrando el archivo, la fila (`id`) y la columna.
- `tipo` ∈ {`tanquilla`, `zanja`}. Una fila `tanquilla` solo llena `a,h,e,n,sobreancho,espesor_fondo`;
  una fila `zanja` solo llena `longitud,ancho,profundidad,diametro,desperdicio`. Las columnas que no
  aplican a la fila se dejan vacías.
- `a`, `h`, `e`: ancho exterior, altura y espesor de pared de la tanquilla (m).
- `sobreancho`: margen de excavación alrededor del foso de la tanquilla, más allá de `a` (m).
- `espesor_fondo`: espesor de la base de concreto bajo la tanquilla, sumado a `h` para la
  profundidad de excavación (m).
- `diametro`: diámetro de la tubería en metros, para calcular su volumen (`REGLA_VOLUMEN_TUBERIA`);
  distinto del `diametro` en pulgadas que pueda aparecer como texto en `especificaciones`.
- `especificaciones`: pares `clave=valor` separados por `;` (por ejemplo
  `diametro=4 pulg;material=PVC`), trazables hacia la regla R4. Describen el **elemento construido**
  del objeto y llegan **solo** a su partida: las de una fila `tanquilla`, al concreto (las paredes);
  las de una fila `zanja`, a la tubería. La excavación y el encofrado no las reciben (INV‑096, fase
  C5), así que R4 no las contrasta con esos APU; una especificación de la excavación o del
  encofrado (tipo de suelo, madera) no se puede dirigir hoy desde esta columna.

## Supuestos declarados

La memoria de cálculo de la línea base (`APUS_CLINICA.pdf`) no fija un sobreancho de excavación ni
un espesor de fondo bajo la tanquilla; son supuestos de esta muestra, necesarios para que
`REGLA_EXCAVACION_TANQUILLA` sea evaluable:

- **Sobreancho de excavación = 0,10 m** por lado, alrededor del foso.
- **Espesor de fondo = 0,10 m**, sumado a la altura de la tanquilla.

## Fila `T-01` (tanquillas)

`a=0.80, h=0.80, e=0.10, n=4, sobreancho=0.10, espesor_fondo=0.10` reproduce
`GEOMETRIA_TANQUILLA` y `N_TANQUILLAS` de la línea base: concreto 0,224 m3 y encofrado 4,48 m2 por
tanquilla (0,896 m3 y 17,92 m2 para las cuatro), los valores corregidos de `COMPUTO_CORREGIDO`.

## Fila `Z-01` (zanja)

`longitud=24.00, ancho=0.40, profundidad=0.80` reproduce `ZANJA` (volumen 7,68 m3) y
`LONGITUD_TUBERIA_M` de la línea base. `diametro=0.1016` (4 pulgadas en metros) y `desperdicio=0.05`
dan una tubería de 24 × 1,05 = 25,2 m.

## Relleno

Si el `codigos` del adaptador declara una clave `relleno`, `AdaptadorCivilTabular.extraer` emite un
item adicional que balancea la excavación total, el concreto total y el volumen de tubería derivado
de esta muestra (regla R5, Sesión I4).
