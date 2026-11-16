# Manual de usuario de Sílice

Este manual es para quien usa Sílice en la empresa: quien arma presupuestos, quien los revisa y quien
administra el programa. No hace falta saber de computación. Va en el orden en que se hacen las cosas.

Cómo leerlo:

- Lo que está entre comillas angulares, como «Guardar versión…», es el texto exacto de un botón, una
  pestaña o un mensaje en pantalla. Búsquelo tal cual.
- Las cifras van con **coma decimal y punto de miles**: 2,5 o 1.234,56. Sílice las pide así.
- **Ctrl+K** significa: mantenga apretada la tecla Ctrl y pulse la K.
- Los ejemplos son inventados («Obra ficticia», «Vía Ficticia El Ensayo», la versión «VIV-001»). Ninguno
  sale de una empresa ni de una obra de verdad.

Contenido:

1. Qué es Sílice y quién hace qué
2. Entrar por primera vez
3. Moverse por Sílice
4. Crear una obra y armar su presupuesto
5. La franja del paso: «Te falta» y «Siguiente paso»
6. Versiones y aprobación
7. Archivos y planos
8. Mercado
9. Precios de la empresa, índices del BCV y reajuste
10. Obras viales y producción
11. Control de obra
12. Auditar un presupuesto
13. El asistente de IA
14. Problemas frecuentes
15. Lo que cambió respecto del manual anterior

## 1. Qué es Sílice y quién hace qué

Sílice calcula cuánto cuesta una obra, partida por partida, con el análisis de precio unitario (APU) de
cada una. También revisa presupuestos hechos en Excel y dice lo que no cuadra. Todo se guarda en el
equipo donde está instalado; nada sale de ahí sin que usted lo envíe.

### 1.1 Instalar y abrir Sílice

Sílice se instala con el instalador de Windows `Silice-<versión>.exe` (o `Silice-<versión>-completo.exe`,
que trae además la búsqueda de partidas parecidas). Los pasos de la instalación, la red local, los
respaldos y la desinstalación están en el [manual de instalación](manual_instalacion.md). Este manual no
los repite.

Para abrir Sílice:

1. En el menú Inicio de Windows, haga clic en «Sílice».
2. Se abre la ventana de Sílice, con su ícono en la barra de tareas. Junto a ella queda una consola minimizada: es el
   servidor de Sílice y muestra el código de instalación la primera vez. No la cierre mientras trabaja.
3. Si Sílice ya estaba abierto, el acceso no abre otro: trae al frente la ventana que ya está.

Para cerrar Sílice, cierre la ventana de Sílice (o la consola minimizada, o use «Detener Sílice» del menú Inicio).

Si en vez de la ventana se abre el navegador, este equipo no puede mostrar la ventana (por ejemplo, porque le falta
WebView2 de Microsoft); la consola dice el motivo en una línea que empieza con «AVISO». Sílice funciona igual en el
navegador.

### 1.2 Los tres papeles: arma, revisa y administra

Cada cuenta tiene uno o más papeles (en pantalla, «roles»). En su Cuenta, sección «Cuentas y permisos»
(sección 3.9), se ven así:

| Papel | Cómo aparece en «Cuentas y permisos» | Para quién | Ejemplo en este manual |
|---|---|---|---|
| Arma | «arma presupuestos (arma)» | Quien arma los presupuestos de las obras | Ana |
| Revisa | «revisa paquetes (revisa)» | Quien revisa los presupuestos y da su dictamen | Rita |
| Administra | «administra la instalación (administrador)» | Quien crea las cuentas y cuida el programa | admin |

Una cuenta puede tener varios papeles. Si alguien trabaja solo, puede ser a la vez administrador y arma.

### 1.3 Qué ve cada papel

**En la barra de secciones de cada obra** (la franja de pestañas bajo el nombre de la obra; sección 3.6).
Algunas secciones tienen además vistas propias, que se eligen con un conmutador pequeño arriba de la
pantalla:

| Sección de la obra | Arma | Revisa | Administra |
|---|---|---|---|
| «Resumen» | Sí, con sus vistas «Resumen» y «Tablero» | Sí, con «Resumen» y «Tablero» | No |
| «Presupuesto» | Sí, y lo edita; vistas «Presupuesto» y «Componer» | Sí, en solo lectura y sin «Componer» | No |
| «Tramos» (solo con el módulo vial encendido) | Sí | No | No |
| «Archivos y planos» | Sí, y sube archivos | Sí, en solo lectura | No |
| «Versiones» | Sí, y restaura | Sí, en solo lectura | No |
| «Aprobaciones» | Sí; vistas «Aprobar» y «Entregar» | Sí; vistas «Aprobar» y «Revisar un paquete» | No |
| «Mercado» | Sí; vistas «Estudio» (las cuatro pestañas) y «Actualizar precios» | Sí; solo «Estudio», con «Histórico de precios» y «Cotizaciones de la obra» | No |
| «Control de obra» | Sí; vistas «Control», «Reajuste» y «Escenarios» | No | No |
| «Riesgo» (solo con el módulo de riesgo encendido) | Sí | Sí | No |

Quien solo administra no ve la zona «Obras» de la barra lateral: su trabajo está en «Costos y
producción» y en su Cuenta.

**Obras de todas las carpetas.** Quien arma y quien revisa ven en la zona «Obras», en el buscador y en
el Inicio las obras de todas las carpetas, no solo las de la carpeta activa. Al abrir una obra de otra
carpeta, Sílice cambia a esa carpeta solo en su sesión: la carpeta de las demás personas no cambia.
Quien revisa la ve en solo lectura y no puede crear ni subir carpetas.

**En el grupo «Costos y producción» de la barra lateral.** Cada entrada abre un espacio con sus propias
pestañas; cada quien ve solo las pestañas que puede usar:

| Entrada | Pestañas | Arma | Revisa | Administra |
|---|---|---|---|---|
| «Auditar un presupuesto» | «Subir y auditar Excel», «Libro de la empresa» e «Historial de auditorías» | Sí, las tres | Sí, las tres | Solo «Subir y auditar Excel», y no puede auditar |
| «Precios y catálogo» | «Precios de la empresa», «Catálogo de partidas e insumos», «Índices del BCV» y «Simulador de listas» | «Catálogo de partidas e insumos» y «Simulador de listas» | «Catálogo de partidas e insumos» | «Precios de la empresa» e «Índices del BCV» |
| «Costos de producción» (solo con el módulo de producción encendido) | «Resumen de arenera», «Existencias», «Costos del período», «Costo por tonelada», «Receta de la planta» y «Producir mezcla» | Sí | No | Sí |

**En su Cuenta** (el botón con su nombre, arriba a la derecha; sección 3.9):

| Sección de la Cuenta | Arma | Revisa | Administra |
|---|---|---|---|
| «Pantalla y tamaño de letra» | Sí | Sí | Sí |
| «Cuentas y permisos» | No | No | Sí |
| «Empresa y tema» | No | No | Sí |
| «Carpetas» | No | No | Sí |
| «Especialidades, IA e instalación» | No | No | Sí |
| «Ayuda y acerca de Sílice» | Sí | Sí | Sí |

**Solo lectura.** Quien revisa ve el Presupuesto, Archivos y planos, Versiones y Mercado sin los botones
que cambian algo. Esos botones no aparecen en gris: simplemente no están. En el Presupuesto se lee
«Está viendo este presupuesto en solo lectura.».

**El buscador.** Cada pantalla tiene su sitio en la barra lateral, en la barra de una obra o en la
Cuenta. Si no recuerda dónde está, búsquela por su nombre con Ctrl+K (sección 3.3): por ejemplo
«Entregar paquete», «Reajuste de precios» o «Riesgo de la obra».

«Simulador de listas» y «Escenarios» desaparecen si la instalación está en modo entrega (sección 14.3).

### 1.4 Los módulos que se encienden y se apagan

Hay cuatro partes del programa que el administrador puede apagar si la empresa no las usa: «Producción»,
«Vial», «Edificación» y «Riesgo». Vienen encendidas. Apagar una no borra nada: deja de ofrecerse y, al
encenderla otra vez, todo vuelve como estaba.

Si abre una pantalla de un módulo apagado verá «Apagada» y «Esta función está apagada en esta
instalación. Quien administra puede encenderla en la Cuenta, sección «Especialidades, IA e
instalación».». Cómo se encienden: sección 2.7.

## 2. Entrar por primera vez

### 2.1 Crear el primer administrador con el código de instalación

La primera vez que se abre Sílice no hay ninguna cuenta. Sílice muestra la pantalla «Bienvenida a
Sílice» y pide un código de un solo uso.

**Paso 1: busque su código de instalación.** Está en dos sitios:

- En el Bloc de notas que Sílice abrió solo la primera vez, y en la consola de Sílice (la ventana minimizada que
  acompaña a la ventana de Sílice; búsquela en la barra de tareas y busque la línea «Código de instalación»).
- En el archivo `%LOCALAPPDATA%\Silice\datos\codigo_instalacion.txt`.

El código tiene 20 caracteres en grupos de cuatro, como `XXXX-XXXX-XXXX-XXXX-XXXX`: letras de la A a la
Z y cifras del 2 al 7. Cópielo y péguelo tal cual.

Si no encuentra el archivo: cierre Sílice y ábralo otra vez; se crea un código nuevo al arrancar.

**Paso 2: cree la cuenta del administrador.** Llene, en este orden:

1. «Código de instalación»: pegue el código.
2. «Su nombre»: así aparecerá en lo que usted guarde.
3. «Usuario»: de 3 a 40 letras minúsculas, números, punto o guion. Por ejemplo `admin`.
4. «Contraseña» y «Repita la contraseña». Reglas, tal como las muestra el recuadro «Cómo debe ser la
   contraseña»:
   - De 10 a 128 caracteres. Una frase larga es mejor que una palabra con símbolos.
   - No puede ser igual a su usuario ni una contraseña muy conocida.
   - No hace falta mezclar mayúsculas, números o símbolos.
   - Sílice no puede recuperarla: si la olvida, un administrador tiene que restablecerla.
5. La casilla «Usaré esta cuenta también para armar presupuestos». Márquela si usted trabaja solo. Si
   no, deje la casilla vacía y después cree otra cuenta con el papel «arma».
6. Pulse «Crear la cuenta y entrar».

El código se borra al usarse y no sirve otra vez. Sílice entra con la cuenta nueva.

### 2.2 Las cuentas que crea el administrador

El administrador crea una cuenta para cada persona:

1. Pulse el botón con su nombre, arriba a la derecha, y elija la sección «Cuentas y permisos». El bloque
   «Cuentas» va primero.
2. En «Crear una cuenta» escriba:
   - «Usuario»: minúsculas, sin espacios, de 3 a 40 caracteres (por ejemplo `ana`).
   - «Nombre de la persona».
   - En «Qué puede hacer», marque los papeles: «arma presupuestos (arma)», «revisa paquetes (revisa)» o
     «administra la instalación (administrador)».
   - «Contraseña temporal»: de 10 a 128 caracteres. Anótela y entréguela en persona.
3. Pulse «Crear la cuenta». Verá «Cuenta creada. La persona deberá cambiar la contraseña al entrar.».

Si marca «arma» y «revisa» en la misma cuenta, Sílice avisa: «Esta cuenta podrá revisar paquetes que ella
misma armó; la vista de revisión lo indicará.».

En «Cambiar una cuenta» el administrador elige la cuenta en «Cuenta que va a cambiar» y puede:

- «Guardar roles»: cambia los papeles. Las sesiones de esa persona se cierran.
- «Desactivar» (o «Reactivar»): la persona deja de entrar; sus registros se conservan.
- «Desbloquear»: deja entrar de nuevo a una cuenta bloqueada por intentos fallidos.
- «Restablecer la contraseña»: escribe una «Contraseña temporal nueva» y la persona tendrá que cambiarla.

Siempre debe quedar un administrador activo. Si no, Sílice dice «Debe quedar al menos un administrador
activo.».

### 2.3 Entrar cada día

1. Abra Sílice. Verá la pantalla «Entrar».
2. Escriba su «Usuario» y su «Contraseña».
3. Pulse «Entrar».

Si se equivoca, verá «Usuario o contraseña incorrectos.». Tras cinco intentos fallidos la cuenta se
bloquea 15 minutos (sección 14).

Si la sesión vence mientras trabaja, Sílice vuelve a «Entrar» con el aviso «Su sesión venció. Entre de
nuevo para seguir.».

### 2.4 La primera entrada con una contraseña temporal

Si el administrador le dio una contraseña temporal, al entrar verá «Cambie su contraseña»:

1. «Contraseña actual»: la temporal.
2. «Contraseña nueva» y «Confirme la contraseña nueva»: la suya, con las reglas de la sección 2.1.
3. Pulse «Cambiar contraseña».

Hasta que la cambie, Sílice no deja hacer nada más. Hoy no hay un botón para cambiar la contraseña por
gusto: si quiere otra, pídale al administrador que la restablezca.

### 2.5 Si el administrador perdió el acceso

En la pantalla «Entrar», pulse «Perdí el acceso de administrador».

1. Pida el código nuevo: en el equipo donde está instalado Sílice, abra el acceso «Sílice: recuperar
   acceso de administrador» del menú Inicio. En su ventana aparece un código de restablecimiento. Sirve
   una sola vez y vence a las 24 horas.
2. Escriba el «Código de restablecimiento», «Su nombre», el «Usuario del administrador» y la «Contraseña
   nueva» dos veces.
3. Pulse «Restablecer y entrar».

Si el usuario ya existe, recupera su acceso; si no existe, se crea. Para volver sin hacer nada, pulse
«Volver a Entrar».

### 2.6 Para quien olvidó su contraseña (cuentas que no administran)

Sílice no recupera contraseñas. Pídale al administrador que use «Restablecer la contraseña» (sección
2.2). Entrará con la temporal y la cambiará (sección 2.4).

### 2.7 Lo que el administrador deja listo

Todo está en su Cuenta: pulse el botón con su nombre, arriba a la derecha (sección 3.9). Cada sección
apila sus bloques, uno debajo del otro:

- **«Empresa y tema»**:
  - **«Empresa y clave de firma».** Escriba «Nombre de la empresa», «RIF» y «Ciudad» y pulse «Guardar la
    empresa». Después, en «Generar la clave de firma», escriba una contraseña de 12 a 128 caracteres dos
    veces y pulse «Generar la clave». Guarde esa contraseña: sin ella no se pueden firmar los paquetes
    que se entregan al cliente (sección 6.10).
  - **«Empresas registradas»**: la clave de otra empresa que le envía paquetes. Se usa poco.
  - Si algún color de la empresa no se lee bien en pantalla, aquí aparece el aviso.
- **«Especialidades, IA e instalación»**:
  - **«Especialidades».** Un interruptor por módulo («Producción», «Vial», «Edificación» y «Riesgo»),
    con «Apagada» o «Encendida».
  - **«Asistente de IA».** Ver la sección 13.
  - **«Claves de API»**: para conectar otros programas. Se usa poco.
  - **«Instalación».** «Crear respaldo ahora» guarda una copia de todo; se descarga con su botón
    «Descargar … (.zip)». Restaurar un respaldo se explica en el manual de instalación.
- **«Carpetas».** Una carpeta de trabajo guarda su catálogo, sus precios y sus obras en un solo archivo.
  Aquí se crea una («Crear», con su «Nombre de la carpeta» y su «Moneda de trabajo», que después no se
  cambia), se sube una copiada de otro equipo («Subir un archivo») o se abre la de demostración
  («Demostración»). La pestaña de demostración solo aparece si la cuenta también arma presupuestos.
- **«Cuentas y permisos»**: las cuentas (sección 2.2) y **«Accesos»**, el registro de entradas.

El logo y los colores de la empresa no se cambian desde la pantalla: son archivos (`tema.json` y
`logo.png`) en la carpeta `tema` dentro de la carpeta de datos de Sílice.

## 3. Moverse por Sílice

La pantalla tiene tres partes: la barra de arriba, la barra lateral a la izquierda y el contenido.

### 3.1 La barra de arriba

De izquierda a derecha:

1. **El logo de la empresa**, o la palabra «Sílice». Al pulsarlo vuelve a la Vista general (sección 3.4).
2. **La carpeta activa**: «Carpeta activa: …» con el nombre de la carpeta de trabajo en que está.
3. **El buscador**: el botón «Buscar una obra, sección o pantalla… (Ctrl+K)».
4. **Su cuenta**: un círculo con sus iniciales y su nombre. Al pulsarlo se abre su Cuenta (sección 3.9).
   Allí está «Salir de la sesión».

Si está viendo la carpeta de demostración aparece también el botón «Demostración», que avisa «Está viendo
datos inventados.» y ofrece «Volver a la carpeta de la empresa». Si tiene un recorrido guiado en curso y
plegó su columna, aparece el botón «Recorrido» para volver a mostrarla (sección 12.4).

La barra de arriba ya no dice dónde está ni tiene el tamaño de letra: cada pantalla dice su nombre en su
cabecera, y el tamaño de letra está en su Cuenta.

### 3.2 La barra lateral

Tiene tres zonas:

- **«Vista general»**, con un número: cuántas cosas esperan algo de usted. Lleva a la Vista general
  (sección 3.4).
- **«Obras»**: el botón «Nueva obra» y la lista de obras, por nombre. Si dos obras de carpetas distintas
  se llaman igual, junto al nombre se lee su carpeta. Cada obra con pendientes lleva su número. Al hacer
  clic en una obra se abre su «Resumen»; sus demás secciones están en la barra de la obra (sección 3.6).
- **«Costos y producción»**: «Auditar un presupuesto», «Precios y catálogo» y «Costos de producción»
  (solo las que su papel puede usar; sección 1.3). Cada una abre un espacio con su nombre arriba y sus
  pestañas debajo.

Con letra «Grande» o «Muy grande», el grupo «Costos y producción» se pliega para dejarle sitio a las
obras. Haga clic en «Costos y producción» para desplegarlo. Nada desaparece.

### 3.3 El buscador (Ctrl+K)

1. Pulse Ctrl+K o haga clic en «Buscar una obra, sección o pantalla… (Ctrl+K)».
2. Escriba parte de lo que busca: el nombre de una obra, de una sección («Mercado»), de una sección de su
   Cuenta («letra») o de una pantalla («Reajuste de precios»). No importan las tildes ni las
   mayúsculas.
3. Elija con las flechas y pulse Enter, o haga clic.
4. Esc cierra el buscador.

Muestra hasta 8 resultados. Si no hay ninguno, dice «Sin resultados».

Varias pantallas trabajan sobre la obra que tiene abierta. Abra primero la obra en la barra lateral y
después busque la pantalla.

### 3.4 La Vista general

Es la primera pantalla al entrar. Arriba dice «Vista general» y, debajo, hay dos pestañas: «Vista
general» y «Pendientes» (sección 3.5). La Vista general muestra, en este orden:

1. **«Lo que requiere atención»**: primero lo que bloquea. Un resumen como «2 bloquean · 3 avisos» y los
   cinco pendientes más urgentes, cada uno con su urgencia («Bloquea» o «Aviso»), su obra, qué pasa y un
   enlace al paso que lo resuelve. Debajo, «Ir a la bandeja de pendientes (…)» lleva a todos. Si no hay
   nada, dice «No tiene pendientes por hacer.».
2. **«Cartera por moneda»**: un recuadro por moneda, por ejemplo «Obras en Bs» y «Obras en USD», cada
   uno con «Total vigente», «Obras» y «En ejecución». Los bolívares y los dólares nunca se suman entre
   sí. Si todavía no hay obras, dice «Aún no hay obras» y, a quien arma, le ofrece «Nueva obra».
3. **«Obras y avance contra el plan»**: una fila por obra con «Obra», «Estado», «Total» y «Avance
   ejecutado vs. plan», por ejemplo «Real 40 % · Plan 55 %», con una barra llena para lo real y una
   barra con borde para lo planificado. Una obra sin avance registrado dice «Sin avance»; una sin
   versión guardada, «Sin versión» en el total. El nombre de la obra lleva a su Resumen.
4. **«Últimas auditorías»**: las cinco últimas, con «Archivo», «Tipo», «Fecha» y «Resultado». El enlace
   «Ir a Auditoría» abre «Auditar un presupuesto».
5. **«Arenera: lo que requiere atención»**: solo si su cuenta opera la arenera y el módulo de
   producción está encendido. Muestra los materiales que tienen poco o que dan existencia negativa; si
   no hay ninguno, dice «Todo sobre el mínimo».

La pantalla no calcula nada por su cuenta: muestra las cifras que ya guardó Sílice. Quien solo
administra ve «Lo que requiere atención» y, si opera la arenera, su bloque; la cartera, el avance y las
auditorías son de quien arma o revisa.

### 3.5 Pendientes

La pestaña «Pendientes», al lado de «Vista general», es la bandeja completa. A la izquierda, «Pendientes
por hacer», con un resumen como «2 bloquean · 3 avisos». Cada pendiente dice su obra y su urgencia:
«Bloquea» (hay que resolverlo para seguir) o «Aviso». Al elegir uno, a la derecha aparece el «Detalle del
pendiente» con un botón que lleva a donde se resuelve.

Ejemplos de pendientes: «VIV-002 espera dictamen», «VIV-001 devuelta: …», «Precios de hace 45 días (…)»,
«3 hallazgos de error o críticos en VIV-002».

El botón lleva directo a la pantalla del paso. Por ejemplo, un pendiente de «Actualizar precios» abre
«Mercado» › «Actualizar precios» de esa obra, y uno de «Entregar» abre «Aprobaciones» › «Entregar». Si
su papel no permite dar ese paso, en lugar del botón se lee «Su cuenta no puede dar este paso.».

Si no hay nada, verá «No tiene pendientes.» y «Cuando una obra necesite algo de usted, aparecerá aquí.».
Quien solo administra siempre ve esa frase.

### 3.6 La cabecera de la obra y su barra de secciones

Al abrir una obra, encima de cada sección aparece una franja con:

- el nombre de la obra;
- «Estado:» con una de estas palabras: «En elaboración», «En aprobación», «Aprobada», «En ejecución» o
  «Atrasada» (la única en color);
- «Versión: V-004», o «Versión abierta: V-003 (la vigente es V-004)» si abrió una versión anterior;
- debajo, la moneda y la lista de precios de la carpeta, por ejemplo «Moneda: USD · Lista para armar:
  Lista USD de la carpeta (ficticia) al 01/10/2026».

Justo debajo está la **barra de secciones de la obra**: «Resumen», «Presupuesto», «Tramos», «Archivos y
planos», «Versiones», «Aprobaciones», «Mercado», «Control de obra» y «Riesgo» (solo las que su papel
puede usar y cuyos módulos están encendidos; sección 1.3). La sección en la que está queda marcada.

Algunas secciones tienen varias vistas. Entonces, arriba de la pantalla aparece un conmutador pequeño
con sus nombres:

| Sección | Vistas del conmutador |
|---|---|
| «Resumen» | «Resumen» · «Tablero» |
| «Presupuesto» | «Presupuesto» · «Componer» |
| «Aprobaciones» | «Aprobar» · «Revisar un paquete» · «Entregar» |
| «Mercado» | «Estudio» · «Actualizar precios» |
| «Control de obra» | «Control» · «Reajuste» · «Escenarios» |

Solo ve las vistas que su papel puede usar. Si le queda una sola, el conmutador no aparece. Por ejemplo,
quien revisa ve en «Aprobaciones» solo «Aprobar» y «Revisar un paquete», y en «Presupuesto» no ve
conmutador.

No confunda el conmutador «Presupuesto | Componer» con las pestañas de dentro del Presupuesto
(«Partidas», «Análisis de precio (APU)» y las demás; sección 4.2): esas siguen igual.

### 3.7 El Resumen de la obra

La sección «Resumen» muestra la obra de un vistazo:

- arriba, la franja del paso (sección 5);
- las cifras «Total», «Avance real contra plan», «Versión de la línea base» (o «Versión vigente» si la obra aún no tiene línea base) y «Etapa»;
- «Pendientes de esta obra», cada uno con su botón.

### 3.8 Salir sin perder trabajo

Si tiene cambios sin guardar y elige otra obra o una entrada de «Costos y producción», Sílice pregunta
«Cambios sin guardar». Pulse «Quedarme» para volver, o «Salir» si está seguro. El texto le dice qué pasa
con los cambios.

Entre «Presupuesto», «Componer», «Archivos y planos» y «Versiones» de la misma obra puede moverse sin
miedo: comparten el mismo borrador y no preguntan.

Si abre otra obra en otra pestaña del navegador, la primera pestaña muestra «Esta obra se abrió en otra
pestaña». Pulse «Retomar» para seguir allí.

### 3.9 Su cuenta

Pulse el círculo con sus iniciales y su nombre, arriba a la derecha. Se abre su Cuenta. Arriba se leen
su nombre, su usuario y sus papeles, y el botón «Salir de la sesión». Debajo, las secciones que su papel
puede usar:

- **«Pantalla y tamaño de letra»**, para todas las cuentas. Es el único sitio donde se cambia el tamaño
  de letra: «Normal», «Grande» o «Muy grande» (100 %, 125 % y 150 %). Una frase de muestra deja ver al
  instante cómo queda. Sílice recuerda su elección en ese navegador. Debajo, «Datos de la cuenta»:
  «Nombre», «Usuario» y «Rol».
- **«Cuentas y permisos»**, **«Empresa y tema»**, **«Carpetas»** y **«Especialidades, IA e
  instalación»**, solo para quien administra (sección 2.7). «Carpetas» pide además poder crear y subir
  carpetas.
- **«Ayuda y acerca de Sílice»**, para todas las cuentas. Su título es el mismo, «Ayuda y acerca de Sílice».
  Primero va la ayuda: «Empieza aquí», «Guías por tarea» y «Glosario» (sección 3.10). Después, la versión del
  programa, el estado de las bases de datos y qué módulos están instalados. Al final, «Recorridos guiados»
  ofrece «Empezar el recorrido «Auditar un libro de la empresa»» (sección 12.4).

La Cuenta abre siempre en «Pantalla y tamaño de letra». Lo que antes era la pantalla «Administración»
está repartido en las cuatro secciones de quien administra.

### 3.10 La ayuda dentro de Sílice

Sílice trae su propia ayuda, en tres sitios:

- **«¿Qué es esto?» encima de cada pantalla.** En cada sección de la obra y en cada herramienta de
  «Auditar un presupuesto», «Precios y catálogo» y «Costos de producción», y en «Pendientes», un botón
  «¿Qué es esto?» va justo encima del título. Al pulsarlo se abre, debajo, para qué sirve la pantalla y
  cuándo usarla, con un enlace a su guía y a las palabras del glosario que usa; al pulsarlo otra vez, o con
  Esc, se pliega. En el «Presupuesto» no hay uno para toda la pantalla: cada pestaña tiene el suyo
  (sección 4.2). Si su cuenta no puede usar la pantalla, no aparece.
- **«Empieza aquí» en la Vista general**, solo la primera vez. Quien administra lo ve mientras su cuenta
  sea la única activa: le dice cómo crear las cuentas de las personas y poner los datos de la empresa.
  Quien arma lo ve mientras no tenga ninguna obra: crear la obra, armar el presupuesto y enviarlo a
  aprobación. Quien solo revisa, también sin obras: auditar un libro y dar su dictamen. Cuando ya no hace
  falta, desaparece solo; Sílice no guarda nada en el navegador para saberlo.
- **La Cuenta › «Ayuda y acerca de Sílice»**: arriba, «En esta ayuda» lleva a cada parte. «Empieza aquí»
  cuenta la primera vez (el código de instalación y la cuenta del administrador, sección 2.1) y lo primero
  de cada papel. «Guías por tarea» trae cuatro guías paso a paso: «Montar un presupuesto», «Enviarlo a
  aprobación», «Actualizar precios» y «Auditar un libro». «Glosario» explica las palabras del oficio que
  Sílice usa (APU, FCAS, línea base, lista para armar, valor ganado, reajuste, entre otras).

Los enlaces de «¿Qué es esto?» y de «Empieza aquí» abren la Ayuda justo en la guía o la palabra
elegida. Si tiene cambios sin guardar, Sílice pregunta antes de salir, como con cualquier enlace.

## 4. Crear una obra y armar su presupuesto

Esta sección es para quien arma. Sigue el camino completo: crear la obra, agregar partidas, ajustar
cantidades, revisar el APU, guardar la versión y ver el IVA.

### 4.1 Crear la obra

1. En la barra lateral, pulse «Nueva obra».
2. Llene el diálogo «Nueva obra»:
   - «Nombre de la obra» (hasta 120 caracteres; no puede repetirse en la carpeta).
   - Debajo se lee «Se creará en …» con el nombre de la carpeta de trabajo.
   - «Cliente (opcional)» y «Ubicación (opcional)».
   - «Tipo de obra»: «Sin especificar», «Obra civil», «Telecomunicaciones», «Industrial» o «Sistemas».
   - «Moneda»: «Bolívares (Bs)» o «Dólares estadounidenses (USD)». Si la carpeta ya tiene moneda, viene
     elegida. Si elige la otra, la ayuda dice que la obra se valorará convirtiendo los precios con la tasa
     del BCV del día.
3. Pulse «Crear obra».

Sílice abre el «Resumen» de la obra nueva. La franja dice «Siguiente paso: Agregue la primera partida»,
con el botón «Agregue la primera partida», que lleva al Presupuesto.

### 4.2 La pantalla «Presupuesto», de arriba abajo

Haga clic en «Presupuesto» en la barra de la obra. Verá, en este orden:

1. **Una línea de estado** bajo el título: «Versión V-004 · 2 cambios sin guardar» (o «Borrador en blanco ·
   …»), «Aprobación:» con el estado de la versión y el «Total» en la moneda de la obra. Si tiene cambios,
   aparece «Descartar cambios».
2. **La franja del paso** («Te falta:» o «Siguiente paso:»), con el único botón principal de la pantalla, y a
   su lado **«Descargar Excel»**, que baja el presupuesto en un libro de Excel, y **«Descargar PDF»**, que
   lo baja en un PDF para imprimir o enviar: la obra, la versión, la fecha y la moneda; cada partida con su
   unidad, cantidad, precio unitario y total; el subtotal, el IVA y el total con IVA; y después el APU de cada
   partida en su página (materiales, equipos y mano de obra y el cierre hasta el precio unitario). Si la obra
   tiene frentes (12.6), las partidas salen por frente, cada uno con su subtotal. Sale lo
   que se ve en la pantalla, también lo que aún no se guardó (el PDF lo dice), con coma decimal y punto de
   miles.
3. **Las pestañas**: «Partidas», «Análisis de precio (APU)», «Plan y equilibrio», «Precios», «Revisión» y
   «Ajustes de costo». En una obra de edificación con espacio aparece además, delante, «Espacio y
   metrajes».

Cada pestaña tiene un botón «¿Qué es esto?» que despliega su explicación. Quien edita ve además, siempre
a la vista: «Escriba los decimales con coma: 2,5; el punto separa los miles: 1.234,56.». En «Partidas»,
«Agregar partida», ese aviso y «¿Qué es esto?» van en una sola fila sobre la tabla, para que las partidas
se vean sin bajar la pantalla.

**Borrador.** Lo que usted cambia se aplica al borrador de la obra cuando deja de escribir. El borrador
no es una versión: para que quede guardado hay que pulsar «Guardar versión…» (sección 4.8). Si cierra
Sílice con cambios, al volver verá «Retomar borrador» con dos botones: «Retomar borrador de … (n
cambios)» para seguir, o «Descartar y abrir de nuevo».

### 4.3 Agregar partidas: una sola puerta, tres caminos

Pulse «Agregar partida» en la pestaña «Partidas» (o «Agregar la primera partida» en la franja). Se abre
el diálogo «Agregar partida». Ahí hay tres maneras de elegir la partida.

**Camino 1: buscarla en el catálogo.**

1. En «Partida», escriba al menos 2 letras del código o de la descripción. Por ejemplo «bloque».
2. Aparece la lista «Partidas del catálogo». Cada opción muestra la descripción y, debajo, el código, la
   unidad, el tipo de obra y si tiene composición.
3. Elija con las flechas y Enter, o con un clic. Si hay muchas, pulse «Ver más resultados» o escriba más
   letras.

Si no la encuentra, Sílice dice «No encontramos «…».» y le sugiere los otros dos caminos.

**Camino 2: «Buscar parecidas».**

Úselo cuando sabe cómo se describe la partida, pero no su código.

1. Escriba en «Partida» cómo se describe. Por ejemplo «pared de bloques de arcilla de 15 cm».
2. Pulse «Buscar parecidas».
3. Sílice muestra las propuestas «de mayor a menor similitud». Cada una trae su puntaje, su código y su
   descripción. Con «Ver el análisis de …» ve sus materiales, equipos y mano de obra.
4. Pulse «Usar esta partida» en la que le sirva.

Si ninguna se parece lo suficiente, verá «Ninguna partida del catalogo supera el umbral de similitud: la
partida se crearia desde cero.». Entonces use el camino 3. Esta búsqueda necesita el instalador completo;
si falta, Sílice lo dice (sección 14).

**Camino 3: «Componer una partida».**

Úselo cuando la partida no existe en el catálogo. Al final de la lista de sugerencias está la opción
«Componer una partida nueva con el código «…»». Se abre el panel «Componer una partida».

La misma composición, como pantalla propia, está en la vista «Componer» del conmutador «Presupuesto |
Componer» (sección 3.6). Pasar de una vista a la otra no cierra el borrador ni pregunta por los cambios.

Antes de empezar, lea el aviso: «Esto cambia el catálogo de la empresa: la partida queda para todas las
obras.».

1. **«Cabecera de la partida»**: «Código», «Descripción», «Unidad», «Dominio» y «Fecha». Si el código ya
   existe, sus tablas se cargan solas.
2. **«Partidas similares del catálogo»**: aparecen al escribir la descripción. Son solo sugerencias: copie
   a mano lo que le sirva.
3. **«Rendimiento»**: las unidades por día y, obligatorio, «Condiciones del rendimiento» (en qué
   condiciones se obtuvo).
4. **«Insumos»**: tres tablas, materiales, equipos y mano de obra. Para cada una puede buscar en la
   referencia MaPreX y pulsar «Usar esta fila», o pulsar «Agregar fila» y escribir a mano.
   - Materiales: «Descripción», «Unidad», «Consumo por unidad», «Desperdicio (%)» (opcional, sección
     4.11), «Precio».
   - Equipos: «Descripción», «Cantidad», «Precio», «Depreciación».
   - Mano de obra: «Descripción», «Cantidad», «Sueldo», «Modalidad».
5. **«Desglose en vivo»**: Sílice calcula mientras escribe «Materiales», «Equipos», «Mano de obra»,
   «Costo directo», «Con administración» y «Precio unitario». Si algo se aparta de lo normal, aparece
   una advertencia (por ejemplo «Rendimiento atípico» o «Precio atípico»).
6. Pulse «Guardar composición». Si un precio difiere del de la lista, Sílice pregunta en «Precios
   distintos a los de la lista»; pulse «Guardar así» o «Volver».

Al guardar, el panel se cierra y el diálogo «Agregar partida» vuelve con la partida nueva elegida.

Para guardar hace falta que la carpeta tenga su lista de precios para armar. Si no la tiene, el panel lo
avisa en «Sin lista de precios para armar» y ofrece «Crear la lista a partir de MaPreX». Si la empresa ya tiene
una lista de precios en la moneda de la carpeta (sección 9.2), ofrece primero «Usar la lista de la empresa «…»», con
el nombre de esa lista: la copia tal cual, en su moneda, y no necesita tasa del BCV. Es la salida cuando la carpeta
está en USD y no hay una tasa del BCV de los últimos 7 días para convertir MaPreX. Creada la lista, el panel dice
«Lista para armar creada: …» y la cabecera de la obra la muestra.

Cuidado: si cierra el panel sin guardar, lo compuesto se pierde sin preguntar.

**Después de elegir la partida, por cualquiera de los tres caminos:**

1. «Cantidad (…)»: la cantidad, con coma decimal. Por ejemplo 210 o 12,5.
2. «Cálculo (opcional)»: cómo sale la cantidad, por ejemplo `6*3-2` o `2,5*4`. Admite números, `+`, `-`,
   `*`, `×`, `/` y paréntesis. Si escribe el cálculo y deja la cantidad vacía, Sílice la toma del cálculo.
   Si escribe los dos y no coinciden, le pide corregir uno.
3. «Nota de medición (opcional)»: por ejemplo «6 m × 35 m de muro, menos vanos».
4. Pulse «Agregar al presupuesto».

En la pestaña se lee «Se agregó … al presupuesto.».

### 4.4 Cambiar o quitar una partida

La tabla de «Partidas» tiene las columnas «Partida», «Descripción», «Unidad», «Cantidad», «Cómo se
midió», «Precio unitario», «Objetivo de mercado», «Total», «Estado» y «Quitar».

- **Cambiar la cantidad:** escriba en la celda «Cantidad». Enter o la flecha abajo pasan a la fila
  siguiente; Esc devuelve el último valor aceptado.
- **Cantidad escrita a mano:** si la partida tenía una cantidad calculada, la celda dice «(calculada: …)» y
  ofrece «Volver a la calculada».
- **Cantidad sin cálculo:** Sílice lo advierte en la columna «Estado». Escriba cómo se obtuvo si quiere que
  la pueda verificar.
- **Quitar:** pulse «Quitar» en la fila y confirme. Mientras no guarde la versión, puede descartar el
  cambio.
- **Filas en amarillo:** una fila con un hallazgo crítico, de error o de advertencia lleva fondo amarillo
  claro. La columna «Estado» dice cuál es; «Ver en Revisión» lleva al detalle.
- **«Pendiente»** en «Precio unitario» o «Total»: la partida no tiene APU en el catálogo y no suma.

Debajo de la tabla se lee «Total del presupuesto …» y el IVA (sección 4.9).

### 4.5 El APU en el panel lateral

En «Partidas», el código de cada fila con precio es un botón. Al pulsarlo se abre a la derecha el panel
«APU de MOV-01 · Movilización y desmovilización de equipos (ficticia) · unidad» (con el código y la
descripción de su partida). La tabla sigue a la vista.

En el panel:

- un bloque por rubro («Materiales · 1 línea(s)», «Equipos», «Mano de obra») con su subtotal;
- «Rendimiento (unidades por día)»;
- «Cierre de partida»: costo directo, administración, utilidad y precio unitario.

Quien edita puede:

- cambiar la cantidad de cada línea y el rendimiento;
- «Agregar línea»: elija «Tipo de línea» (material, equipo o mano de obra), busque el «Insumo» en la
  lista de la versión o escriba uno nuevo, ponga la «Cantidad» y pulse «Agregar al APU»;
- «Cambiar»: cambia el insumo de una línea y conserva su cantidad;
- «Quitar»: quita una línea.

Estos cambios se hacen en la copia de esta versión: el catálogo de la empresa no cambia. Agregar,
cambiar y quitar líneas solo se puede en una versión guardada.

Cierre el panel con «Cerrar» o con Esc. Si la pantalla es estrecha, el panel se pone encima de la tabla.

La pestaña «Análisis de precio (APU)» muestra lo mismo, con una lista de partidas a la izquierda y el
buscador «Buscar partida».

### 4.6 Las demás pestañas del Presupuesto

- **«Plan y equilibrio».** Reparte cada partida entre los períodos del plan; cada fila debe sumar
  exactamente 1. Con «Plan desde los rendimientos», Sílice arma el plan con la cantidad y el rendimiento
  de cada partida (elija «Cuadrillas», «En paralelo con la anterior» y los «Períodos del plan»: «Días
  hábiles», «Semanas (5 días hábiles)» o «Meses (20 días hábiles)»). Las cuadrillas se ponen también
  cuando todavía no hay plan. Un plan armado por semanas o por meses se abre con esa unidad marcada.
  Debajo, la «Curva de inversión» y el «Punto de equilibrio», que no se editan.
- **«Precios».** De dónde sale cada precio: lista, fecha, moneda, referencia y cotización. «Detalle»
  muestra el resto. «Sin referencia ni cotización: el precio no tiene fuente» sale solo si el precio no
  trae referencia, ni cotización, ni una fuente declarada para él (la de su fila en la lista de la
  empresa o la de un precio tecleado); el nombre de la lista de la que se copió no cuenta como fuente. «Buscar variaciones atípicas de precio» señala los insumos que cambiaron demasiado.
  Muestra la versión guardada, no los cambios sin guardar. El enlace «Registrar una cotización en
  Mercado» lleva a la sección 8.4.
- **«Revisión».** El informe de auditoría del borrador, con todas las reglas: «Presupuesto … · Hallazgos:
  … · Resultado: …» y la tabla «Hallazgos» con regla, severidad, partida y descripción. Si llegó desde
  «Ver en Revisión», solo se ven los de esa fila; «Quitar filtro» muestra todos.
- **«Ajustes de costo».** Cuatro parámetros: FCAS, bono de alimentación, administración y utilidad.
  Cambiarlos recalcula todos los APU y el total. Aquí está también «Convertir la moneda…» (sección 9.6).
- **«Espacio y metrajes»** (obras de edificación). Se describe el espacio en tablas («Orígenes de medida»,
  «Ambientes», «Fuentes», «Puntos», «Vértices de recorridos») y Sílice deriva las cantidades. Ojo: en
  «Vértices» la coma separa las coordenadas y el decimal va con punto, por ejemplo `0,0,0; 2.5,0,0`. Lo
  más cómodo es importar un plano (sección 7).

### 4.7 Cargar el cómputo desde un archivo CSV

Si ya tiene el cómputo en un archivo, no hace falta agregar partida por partida.

1. Vaya a «Archivos y planos» de la obra.
2. Pulse «Subir plano o cómputo» (o «Cargar cómputo» si la edificación está apagada).
3. Suelte el archivo `.csv` en la zona, o haga clic para elegirlo. Se abre «Cargar cómputo».
4. Elija «Tipo de obra del archivo»: «Civil» (viene elegido), «Telecomunicaciones», «Industrial» o
   «Sistemas».
5. En civil, elija en «Códigos de partida (civil)» las partidas de «Concreto», «Encofrado», «Excavación» y
   «Tubería». Marque «Incluir relleno (balance R5)» si lo necesita y elija el «Relleno».
6. Pulse «Extraer cómputo». Aparece la tabla «Cómputo extraído».
7. Pulse «Llevar al presupuesto». Sílice valora primero cada partida:
   - Si a una partida le falta el rendimiento, aparece «Rendimientos por declarar». Elija «estimado» o
     «medido», pulse «Registrar el rendimiento» y vuelva a pulsar «Llevar al presupuesto».
   - Si un ítem no tiene partida en el catálogo, aparece «Pendientes» con propuestas. Pulse «Aplicar la
     propuesta» y vuelva a llevar, o pulse «Llevar sin los pendientes».
8. Verá «Se llevaron 18 partidas al presupuesto.» (o el número que corresponda) y el enlace «Ver en
   Partidas».

Las partidas quedan en el borrador. Falta guardar la versión (sección 4.8).

**Atención con el formato del archivo de cómputo.** A diferencia de la pantalla, este archivo usa la
**coma para separar columnas** y el **punto para los decimales** (`0.80`, no `0,80`). La primera fila
lleva los nombres de las columnas y el texto va en UTF-8. Para obra civil:

```
id,tipo,a,h,e,n,sobreancho,espesor_fondo,longitud,ancho,profundidad,diametro,desperdicio,especificaciones
T-01,tanquilla,0.80,0.80,0.10,4,0.10,0.10,,,,,,material=concreto
Z-01,zanja,,,,,,,24.00,0.40,0.80,0.1016,0.05,diametro=4 pulg;material=PVC
```

`tipo` es `tanquilla` o `zanja`. Una tanquilla llena `a`, `h`, `e`, `n`, `sobreancho` y `espesor_fondo`; una
zanja, `longitud`, `ancho`, `profundidad`, `diametro` y `desperdicio`. La última columna es opcional.

Las columnas mínimas de los otros tipos:

- Telecomunicaciones: `tipo,id,descripcion,codigo_partida,unidad` (`tipo` es `nodo` o `enlace`).
- Industrial: `id_activo,descripcion,codigo_partida,unidad,frecuencia_anual,horizonte_anios`.
- Sistemas: `id,modulo,caso_de_uso,codigo_partida,entradas,salidas,consultas,archivos,interfaces`.

### 4.8 Guardar la versión

Cuando el borrador tiene cambios, la franja dice «Siguiente paso: Hay 3 cambios sin guardar» con el botón
«Guardar versión…» (o «Guardar primera versión…» si la obra no tiene ninguna).

1. Pulse el botón. Se abre «Guardar versión».
2. Lea el resumen: cuántos cambios, de qué versión sale y el total. Abajo está la lista «Cambios (n)» con lo
   que había antes y lo que queda después.
3. Escriba el motivo, hasta 300 caracteres:
   - en la primera versión, «Fuente de la medida (de dónde salen los datos)», por ejemplo «Planos de
     planta, revisión B»;
   - en las siguientes, «Fuente del cambio (por qué y con qué respaldo)».
4. El «Responsable» es usted; no se cambia.
5. Pulse «Guardar versión».

Verá «Versión guardada» y, por ejemplo, «Se guardó la versión V-005 con 3 cambios registrados.».

**La primera versión de una obra larga.** Al guardar la primera versión, Sílice arma el plan de trabajo desde los
rendimientos. El plan admite hasta 500 períodos: si por días no cabe, lo arma por semanas (de 5 días hábiles) y, si
tampoco, por meses (de 20 días hábiles), y el mensaje de guardado lo dice, por ejemplo «El plan por días tendría 700
períodos y la matriz admite 500: se armó por semanas (140 períodos). Puede rehacerlo con cuadrillas en «Plan y
equilibrio».». La versión se guarda igual; si quiere el plan en otra unidad o con más cuadrillas, rehágalo en «Plan y
equilibrio». Si ni en meses cabe, no se guarda y Sílice le pide, en «Plan y equilibrio», asignar más cuadrillas a las
partidas largas, hacer el plan desde los rendimientos por meses y volver a guardar: la tabla de cuadrillas está ahí
aunque todavía no haya plan.

Si alguien guardó otra versión mientras usted trabajaba, Sílice avisa «Hay una versión más nueva» y le deja
elegir entre «Guardar de todos modos» y «Abrir la versión …».

### 4.9 El IVA

Debajo de «Total del presupuesto», en la pestaña «Partidas», se leen tres líneas:

- «Subtotal»
- «IVA (16 %)»
- «Total con IVA»

El IVA no se escribe: Sílice usa la alícuota general del 16 %, con su fuente legal en «¿Qué es esto?». Se
calcula sobre el total del presupuesto, nunca dentro del APU: el precio unitario y el total del
presupuesto van sin IVA.

### 4.10 Si quiere empezar de nuevo

- **«Descartar cambios»** (en «Estado del borrador»): borra lo que no guardó. Sílice pregunta antes; los
  cambios descartados no se recuperan.
- **Abrir otra versión**: desde «Versiones» (sección 6.1).

### 4.11 El desperdicio de un material en Componer

Algunos APU cobran el material que se pierde en obra (el asfalto que queda en el camión, el cemento que
se riega). En Componer se declara así, sin hacer la cuenta a mano:

1. En la tabla «Materiales», escriba en «Consumo por unidad» la cantidad **neta**, la que queda en la
   obra. Por ejemplo `0,50`.
2. En «Desperdicio (%)» escriba el porcentaje: `4` es 4 %. Debe estar entre 0 y 100. Vacío o `0`, el
   material no lleva desperdicio.
3. En «Desglose en vivo» aparece la lista «Materiales con desperdicio», una línea por material, por
   ejemplo «Emulsión asfáltica (fila 1): consume 0,52 (0,50 + 4 %)». La cantidad con desperdicio la
   calcula Sílice (neta × (1 + porcentaje ÷ 100)) y es la que entra en el precio unitario.
4. Pulse «Guardar composición». Sílice guarda la neta y el porcentaje: al abrir de nuevo la partida en
   Componer vuelven tal como los escribió.

Si el porcentaje está mal escrito, el desglose muestra un «Aviso», por ejemplo «En Materiales, fila 1
(«Emulsión asfáltica»), el desperdicio «150» debe estar entre 0 y 100 (es un porcentaje: 4 es 4 %).».
Por ahora la Hoja no muestra la neta ni el porcentaje: para verlos o cambiarlos, abra la partida en
Componer.

### 4.12 Los parámetros del precio unitario en Componer

El bloque «Parámetros del precio unitario», encima de «Desglose en vivo», trae los cuatro parámetros con
que Sílice calcula el precio unitario: FCAS, bono de alimentación, administración y utilidad.

- Si Componer está abierto dentro de una obra («Presupuesto › Componer» o el panel de «Agregar
  partida»), son los de la pestaña «Ajustes de costo» de esa obra: el precio unitario de Componer es el
  mismo que tendrá la partida en el presupuesto.
- Sin obra abierta, son los de omisión de Sílice (FCAS 6,00, bono 1,00, administración 0,15 y
  utilidad 0,10), y el bloque lo dice.

Puede cambiarlos para ensayar, por ejemplo una utilidad de `0,12`: el desglose se recalcula. Ese cambio
**solo vale para este cálculo**: no cambia la obra ni se guarda con la partida (la partida es del
catálogo y sirve a todas las obras). Para cambiarlos en el presupuesto, use «Ajustes de costo».
«Volver a los de la obra» (o «Volver a los de omisión») deshace lo escrito. Si escribe una cifra con
punto decimal o negativa, el campo queda marcado con el motivo y el desglose espera a que la corrija.

En las tablas de insumos, un precio de la lista con más de dos decimales (por ejemplo uno convertido
de bolívares) se lee con dos, como en Excel; al entrar en la celda se ve y se edita el número completo,
que es el que se guarda. Lo que usted escribe se ve siempre tal cual.

## 5. La franja del paso: «Te falta» y «Siguiente paso»

Arriba de cada sección, Sílice dice **un solo** paso a la vez. Hay dos tipos:

- **«Te falta:»**, con fondo amarillo claro y un ícono de aviso: falta algo antes de seguir.
- **«Siguiente paso:»**, entre dos rayas finas: solo orienta.

Su botón es el principal de la pantalla. Si su papel no puede dar ese paso, la franja solo informa, sin
botón.

### 5.1 En el Presupuesto

Sílice revisa en este orden y muestra la primera que se cumple:

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| «Te falta: Agregue la primera partida» | La obra no tiene partidas | Pulse «Agregar la primera partida» (sección 4.3) |
| «Siguiente paso: Hay 3 cambios sin guardar» | Cambió algo y no lo guardó | Pulse «Guardar versión…» o «Guardar primera versión…» (sección 4.8) |
| «Te falta: Hay 2 hallazgos graves: revíselos antes de enviar» | La auditoría encontró errores o hallazgos críticos | Pulse «Ir a Revisión», corrija y guarde |
| «Te falta: La versión V-004 fue devuelta: corrija lo observado» | Quien revisa la devolvió | Pulse «Hacer una versión nueva», corrija y guarde (sección 6.7) |
| «Siguiente paso: La versión V-004 espera dictamen» | Ya la envió | Nada: espere el dictamen |
| «Siguiente paso: Envíe la versión V-004 a aprobación» | Todo listo | Pulse «Enviar a aprobación…» (sección 6.5) |

Si la versión ya está aprobada, o si abrió una versión que no es la vigente, no hay franja.

### 5.2 En el Resumen

El Resumen dice el paso según la etapa de la obra:

| Etapa | Botón |
|---|---|
| En elaboración | «Abrir el presupuesto» |
| En aprobación | «Ver el envío» |
| Aprobada | «Declarar la línea base» |
| En ejecución | «Registrar el avance» |
| Atrasada | «Ver las alertas» |

Si falta algo, dice «Te falta:» y la razón, por ejemplo «Sin avance registrado» o «Atrasada 5 días
hábiles (SPI 0,92)».

### 5.3 En otras secciones

- **Archivos y planos:** «Te falta: subir el plano o describir el espacio», con el botón «Subir plano o
  cómputo». Aparece si pidió describir el espacio y todavía está vacío.
- **Cargar cómputo:** «Te falta: la carpeta no tiene lista de precios para armar». No tiene botón: hay que
  crear la lista (sección 4.3, camino 3, o sección 9.2).
- **Versiones:** repite «Hay 3 cambios sin guardar» o «La versión V-004 espera dictamen».

## 6. Versiones y aprobación

Cada vez que guarda, nace una versión nueva. Las anteriores no se borran nunca.

### 6.1 La sección «Versiones»

Arriba está la «Cadena de sellos» (sección 6.9). Debajo, la tabla «Versiones de la obra» con:
«Versión», «Fecha», «Motivo», «Sale de», «Cambios», «Estado de aprobación», «Vigente» y «Acciones».

- La versión **vigente** dice «Sí» en «Vigente»: es la última guardada que no se descartó.
- La que tiene abierta dice «(abierta)» junto a su código.
- Una **descartada** dice «(descartada)». Se descarta desde «Actualizar precios» (sección 9.3). Sigue
  guardada, con su historia, pero deja de ser la vigente.

Botones de cada fila:

- **«Abrir»**: lleva al Presupuesto con esa versión. No aparece en una descartada.
- **«Ver cambios»**: abre a la derecha el «Registro de cambios de la versión …», con fecha, responsable,
  qué cambió, antes, después y fuente.
- **«Restaurar…»**: ver la sección 6.3.

### 6.2 Abrir una versión anterior

Pulse «Abrir» en su fila. La cabecera dirá «Versión abierta: V-002 (la vigente es V-004)». Puede mirarla
y, si la edita y guarda, nace una versión nueva que sale de ella.

### 6.3 Restaurar una versión

Restaurar crea una versión nueva, copia de la elegida. Nada se borra. Sirve también para volver a una
versión descartada.

1. Guarde o descarte antes los cambios pendientes. Si hay cambios, el botón no aparece y Sílice dice
   «Guarde o descarte los cambios pendientes antes de restaurar otra versión.».
2. Pulse «Restaurar…» en la fila de la versión.
3. En el diálogo «Restaurar una versión», revise «Versión a restaurar» (viene la de la fila; puede elegir
   cualquiera, descartadas incluidas).
4. Escriba la «Fuente (por qué se restaura)».
5. Pulse «Restaurar».

Verá «La versión V-002 se restauró como la versión V-005 (la vigente).».

### 6.4 Quién aprueba

Quien revisa da el dictamen. Quien arma también puede hacerlo; en ese caso el dictamen queda rotulado
«aprobada por quien la armó» o «devuelta por quien la armó», para que se sepa.

Solo puede haber un envío pendiente por obra. Si envía otra versión, la anterior se retira de la
aprobación.

### 6.5 Enviar a aprobación (quien arma)

1. Guarde la versión y corrija los hallazgos graves. La franja dirá «Siguiente paso: Envíe la versión
   V-004 a aprobación».
2. Pulse «Enviar a aprobación…».
3. Si quiere, escriba una «Nota para quien revisa (opcional)», hasta 2.000 caracteres.
4. Pulse «Enviar a aprobación».

Verá «Se envió V-004 a aprobación.». La línea «Aprobación:» dice «En aprobación» y la franja, «La versión
V-004 espera dictamen». La versión enviada no se edita: si guarda cambios, sale una versión nueva.

### 6.6 Dar el dictamen (quien revisa)

1. Entre a «Aprobaciones» de la obra, o use el botón «Ver el envío» de su pendiente.
2. Sílice abre el envío: «Carpeta», «Total», «Estado», «Enviada por» y la nota. Debajo, la tabla
   «Partidas de V-004» y el informe de auditoría.
3. En el panel «Dictamen», elija en «Su dictamen»:
   - «Aprobada»;
   - «Aprobada con observaciones»;
   - «Devuelta».
4. Escriba las «Notas». Son obligatorias para devolver o aprobar con observaciones.
5. Pulse «Registrar el dictamen…» y confirme con «Registrar el dictamen». El dictamen no se cambia después.

Si la obra no tiene envíos, verá la lista «Versiones que esperan dictamen en esta carpeta» con «Abrir el
envío», o «No hay versiones esperando dictamen.».

### 6.7 Si la versión vuelve devuelta (quien arma)

1. La franja del Presupuesto dice «Te falta: La versión V-004 fue devuelta: corrija lo observado».
2. Lea las notas debajo de «Aprobación:» («Notas de …: …»).
3. Pulse «Hacer una versión nueva». Sílice lo lleva a «Partidas» y dice «Corrija y guarde: será una
   versión nueva.».
4. Corrija, guarde la versión (sección 4.8) y envíe **la nueva**. La devuelta no se vuelve a enviar.

### 6.8 El rastro de aprobaciones

Debajo del envío, «Rastro de la obra» resume la historia, por ejemplo «VIV-001 devuelta → VIV-002
aprobada», y la tabla «Movimientos de aprobación» dice cada envío, dictamen y retiro, con quién, cuándo y
sus notas.

### 6.9 La cadena de sellos

Cada versión guardada queda sellada con una huella. La «Cadena de sellos», arriba de «Versiones», dice si
alguien cambió la base de datos por fuera de Sílice:

- **«Integridad verificada»** y «Cadena íntegra: 5 versiones»: todo bien.
- **«Se rompió en la versión V-003»**, con el motivo: alguien cambió la base fuera del sistema.

Con la cadena rota no se puede enviar a aprobación ni aprobar; solo devolver. Qué hacer: avise al
administrador. Él puede restaurar la base desde un respaldo (manual de instalación, «Restaurar»).

### 6.10 Entregar el paquete al cliente (quien arma)

1. Abra la obra y, en «Aprobaciones», elija la vista «Entregar» (o busque «Entregar paquete» con
   Ctrl+K). Si un pendiente le pide entregar, su botón lo lleva ahí.
2. Elija «Obra» y «Versión». Viene elegida la última aprobada.
3. Revise los datos: «Total», «Hallazgos», «Cadena».
4. Escriba «Para quién es (opcional)» y la «Contraseña de la clave de firma» (la del administrador,
   sección 2.7).
5. Pulse «Generar paquete» y después «Descargar el paquete».

Si la versión no está aprobada, el paquete sale rotulado «Versión NO aprobada», con la fecha. Si no hay
clave de firma, sale sin firma y quien lo reciba lo verá como «no verificado».

### 6.11 Revisar un paquete recibido (quien revisa)

1. Abra la obra y, en «Aprobaciones», elija la vista «Revisar un paquete» (o búsquela con Ctrl+K).
2. En la pestaña «Paquete .silice», suelte el archivo `.silice` que recibió.
3. Lea el aviso:
   - «Verificado: emitido por … No se alteró desde que se firmó.»: el paquete es confiable.
   - «No verificado: …»: no se pudo comprobar quién lo emitió; se audita igual.
   - «Alterado: … No confíe en este paquete; pida uno nuevo.»
4. Revise el «Total recalculado», las diferencias de precio y los hallazgos.
5. Elija el dictamen («conforme», «con observaciones» o «rechazado»), escriba las «Notas» y pulse
   «Guardar dictamen».

La pestaña «Presupuesto en Excel» revisa un presupuesto en Excel de otra empresa: descargue la plantilla
con «Descargar la plantilla del formato» y suelte el `.xlsx`.

## 7. Archivos y planos

La sección «Archivos y planos» de la obra tiene el botón «Subir plano o cómputo» y la tabla «Registro de
importaciones».

### 7.1 Subir un plano DXF o IFC

Necesita el módulo de edificación encendido.

1. Pulse «Subir plano o cómputo».
2. Suelte el plano `.dxf` o `.ifc` en la zona, o haga clic para elegirlo. Máximo: 8 MiB un DXF y 20 MiB
   un IFC.
3. Pulse «Leer plano».
4. Si el plano no dice su unidad, verá «Falta la unidad del dibujo». Elija la «Unidad del dibujo» (m, cm,
   mm, dm, in o ft) y pulse «Continuar con esta unidad».
5. Lea el «Informe de la importación de …»: qué importó, qué no reconoció, qué aproximó y qué queda
   pendiente.
6. **«Alturas pendientes»**: si el plano no trae la altura de algún ambiente, escríbala en metros (por
   ejemplo 2,50) y pulse «Cargar alturas».
7. **«Circuitos por declarar»**: confirme o corrija los conductores y los puntos de cada circuito y pulse
   «Declarar circuitos».
8. Pulse «Fusionar con el espacio del borrador». Si no quiere usar el plano, pulse «Descartar la
   importación».

Si fusiona sin cargar las alturas, esos ambientes entran con 2,5 m provisionales, y los circuitos
supuestos quedan marcados en la auditoría. Puede corregirlos después en «Espacio y metrajes».

Las filas entran al borrador para que las revise: falta guardar la versión.

Si no tiene plano, el enlace «Describir el espacio a mano» lleva a «Espacio y metrajes».

### 7.2 Cargar el cómputo

Un archivo `.csv` en la misma zona abre «Cargar cómputo». Los pasos y el formato están en la sección 4.7.

### 7.3 El registro de importaciones

La tabla «Registro de importaciones» guarda cada archivo importado en la obra, con «Nombre», «Tipo»
(«Plano .dxf», «Plano .ifc» o «Cómputo .csv»), «Fecha y hora», «Quién», «Qué produjo» (por ejemplo «34
filas en el espacio; 2 sin reconocer» o «18 partidas llevadas») y «Versión» (el código, o «sin guardar»).

Haga clic en el nombre del archivo para ver su informe en el panel lateral.

Quien revisa ve el registro, pero no sube archivos.

### 7.4 Con la edificación apagada

La sección sigue. El botón se llama «Cargar cómputo» y solo acepta `.csv`. No hay planos ni «Espacio y
metrajes».

## 8. Mercado

La sección «Mercado» de la obra abre «Estudio de mercado». Tiene cuatro pestañas. Quien revisa ve solo
las dos últimas.

### 8.1 «Lo que compramos» (los insumos)

1. En «Insumo», escriba parte del nombre o el código, por ejemplo «cemento», y elíjalo.
2. Si quiere, cambie «Días hacia atrás» (de 1 a 3.650; normalmente 90) y pulse «Ver estos días».
3. Lea las cifras: «Observaciones», «Mínimo», «Primer cuartil», «Mediana», «Promedio» y «Máximo».
4. En «Su precio», Sílice propone uno («Propuesta de Sílice: …») y explica por qué. Usted decide.
5. Escriba «Su precio». Si quiere, elija la «Observación que respalda el precio».
6. Si la obra está en ejecución y quiere que Control de obra use ese precio, marque «Declararlo precio del
   corte de la obra …».
7. Pulse «Usar este precio», lea lo que va a cambiar y pulse «Confirmar».

El precio entra en la lista para armar de la carpeta con la fecha de hoy. Las versiones ya guardadas no
cambian.

**Anotar lo que ve en el mercado.** En «Anotar una observación», llene «De dónde sale» («Proveedor»,
«Competidor», «Cotización», «MaPreX» o «Compra hecha»), «Fuente», «Fecha» (no puede ser futura), «Precio»
y, si quiere, «Nota». Pulse «Anotar observación». La observación toma la moneda de la carpeta. Para
quitar una, pulse «Anular» en su fila: sale de las cifras y queda constancia.

### 8.2 «Lo que cobramos» (las partidas)

Igual que la anterior, pero con partidas («Partida», por ejemplo «friso»). Las cifras añaden «Su costo
(piso)» y «Precio con utilidad». Al pulsar «Usar este precio» queda guardado como **objetivo de mercado**:
el Presupuesto lo muestra junto al precio del APU, en la columna «Objetivo de mercado».

### 8.3 «Histórico de precios»

Cada fila es un insumo que cambió de precio en una actualización de la lista. Filtre por «Insumo»,
«Desde» y «Hasta» y pulse «Filtrar». Las columnas son «Fecha», «Insumo», «Precio anterior», «Precio
nuevo» y «Variación».

### 8.4 «Cotizaciones de la obra»

Una cotización vale solo para esta obra. Se lee de la versión vigente.

**Registrar una cotización** (quien arma):

1. Guarde o descarte antes los cambios del Presupuesto. Si hay cambios, verá «Hay cambios sin guardar».
2. Pulse «Registrar una cotización…».
3. Elija el «Insumo» y escriba el «Precio cotizado», el «Proveedor», el «Número de la cotización», la
   «Fecha de la cotización» y, si quiere, la «Evidencia».
4. Pulse «Cotizar».

Sílice crea una versión nueva desde la vigente y avisa «Se creó la versión V-006 con la cotización.» con
el enlace «Abrirla en el Presupuesto». El precio cotizado debe ser distinto del de la lista.

**Retirar una cotización:** pulse «Retirar una cotización…», elija el «Insumo cotizado», escriba «Por qué
se retira» y pulse «Retirar cotización». También crea una versión nueva, que vuelve al precio de la lista.

**El rastro de la moneda.** La tabla muestra, por insumo: «Código», «Insumo», «Cotización», «Moneda
original», «Precio original», «Tasa», «Fecha de la tasa» y «Fuente de la tasa». Si el precio de la lista
se convirtió de otra moneda, esas columnas dicen de qué precio salió, con qué tasa, de qué día y de qué
publicación del BCV. El diálogo de cotizar no pide moneda: la cotización va en la moneda de la obra.

### 8.5 La conversión de moneda con la tasa del BCV del día exacto

En Mercado, cuando un precio está en otra moneda que la obra:

- **Una observación** se convierte con la tasa del BCV **del mismo día de la observación**. En la tabla de
  observaciones, la columna «En las cifras» dice «Sí, convertida: …», o «No: sin tasa del BCV del
  dd/mm/aaaa» si falta la tasa de ese día.
- **El precio del corte** se convierte con la tasa del BCV del mismo día. Si falta, no se guarda nada y
  Sílice dice: «No hay tasa del BCV del dd/mm/aaaa (hace falta la del mismo día) para convertir este precio
  a … Cárguela en Índices y vuelva a intentarlo.».

Cada conversión deja su rastro en una línea, por ejemplo:

«31,50 USD × 36,50 Bs/USD (BCV, publicación del 20/10/2026) = 1.149,75 Bs»

Es decir: el precio original, la tasa, la fecha y la fuente, y el resultado. Al pasar el ratón se ve el
resultado exacto. Las tasas las carga el administrador en «Índices del BCV» (sección 9.4).

## 9. Precios de la empresa, índices del BCV y reajuste

### 9.1 El catálogo

«Precios y catálogo», en la barra lateral, tiene la pestaña «Catálogo de partidas e insumos». Es de
solo lectura.
Escriba en «Buscar en el catálogo» y cambie entre las pestañas «Partidas» e «Insumos». Los insumos traen
su «Precio vigente».

### 9.2 Precios de la empresa (quien administra)

En «Precios y catálogo», pestaña «Precios de la empresa» (es la primera que ve quien administra). Es
la lista de precios propia de la empresa: una copia de la
lista base con sus precios encima, cada uno con su fecha y su fuente.

1. **«1. La referencia MaPreX en bolívares»**: pulse «Cargar la referencia MaPreX en Bs».
2. **«2. La lista de la empresa»**: llene «Empresa (nombre)», «RIF», «Lista base», «Moneda de la lista»,
   «Fecha de la lista» y «Fuente de la lista (de dónde salen estos precios)»; si quiere, «Nombre de la lista
   (opcional)». Suelte el archivo de precios (CSV o XLSX) y pulse «Crear la lista de la empresa».
3. **«3. Precios vencidos o fuera de rango (R11 y R12)»**: elija la «Lista» y la «Fecha de evaluación». Con
   una lista elegida aparece «Buscar variaciones atípicas de precio».
4. **«FCAS por componentes»**: «Abrir la calculadora del FCAS».

El archivo de precios lleva las columnas `tipo`, `insumo`, `unidad` y `precio` (y, si quiere, `fecha`,
`fuente`, `referencia`, `moneda`, `tasa`, `fecha_tasa` y `fuente_tasa`). En este archivo el decimal va con
**punto**. Una fila sin `fecha` o sin `fuente` toma la «Fecha de la lista» y la «Fuente de la lista» del formulario.

**Al soltar el archivo, Sílice lo revisa sin guardar nada** («Revisando el archivo...») y dice:

- cuántas filas reconoce el catálogo, por ejemplo «El catálogo reconoce 2 filas del archivo.»;
- si trae insumos que el catálogo no tiene, la tabla «Insumos nuevos del archivo» (insumo, tipo, unidad y precio)
  y la casilla «Dar de alta en el catálogo los insumos nuevos al crear la lista». Sin marcarla, esos insumos no
  entran a la lista; marcada, se dan de alta al pulsar «Crear la lista de la empresa» y entran con su precio. Si el
  archivo trae dos veces el mismo insumo nuevo con precios distintos, no se crea nada y Sílice le pide dejar una
  sola fila;
- en «Otra unidad», cada fila cuya descripción el catálogo ya conoce pero con otra unidad, por ejemplo «“Arena de
  prueba” viene en saco y el catálogo lo tiene en m3: no entró; escriba en el archivo la unidad del catálogo.».
  Esas filas nunca se dan de alta (serían otro insumo con el mismo nombre): corrija la unidad en el archivo y
  vuelva a soltarlo.

Con la lista creada, «Lista creada» dice cuántos precios entraron y, si los hubo, la tabla «Insumos dados de alta en
el catálogo». Debajo, a quien también arma presupuestos (el papel de quien arma) le aparece «Usarla como lista para
armar»: la copia tal cual, en su moneda y sin tasa del BCV, como lista para armar de la carpeta, si la carpeta está
en esa moneda. Si la carpeta ya tenía una, la nueva pasa a ser la vigente (la de fecha más reciente): así se renuevan
los precios con la lista de la empresa del mes. A quien solo administra, Sílice le dice «La lista para armar la crea quien
arma el presupuesto, desde Componer.» (sección 4.3, camino 3).

### 9.3 Actualizar precios de un presupuesto (quien arma)

Abra la obra y, en «Mercado», elija la vista «Actualizar precios» (o búsquela con Ctrl+K). Un
pendiente de «Actualizar precios» también lo lleva ahí. Sirve para revalorar un presupuesto guardado
con una lista de
precios nueva.

1. Elija el «Presupuesto base».
2. Escriba el «Código de la versión nueva», la «Fecha de vigencia», la «Moneda» y el «Nombre de la lista».
3. Suelte la lista de precios (`.csv` o `.xlsx`, con las columnas `tipo`, `insumo`, `unidad` y `precio`).
4. Pulse «Revalorar presupuesto».
5. Revise el «Comparativo por partida». Puede «Exportar a Excel» y ver el informe de auditoría de la
   versión nueva.

Si no le sirve la versión nueva, pulse «Descartar versión» y confirme. La versión sigue guardada, con su
historia, pero deja de ser la vigente. Para recuperarla, restáurela (sección 6.3).

### 9.4 Índices del BCV (quien administra)

En «Precios y catálogo», pestaña «Índices del BCV». Aquí se cargan la tasa del dólar y el INPC.

1. En «Qué archivo es», elija: «Tasa de referencia del USD (.xls trimestral)», «INPC (.xls mensual)» o «Una
   serie en CSV canonico (serie, fecha, valor, provisional, fuente)».
2. Escriba la «Dirección de la página del BCV de donde lo bajó» y la «Fecha de descarga».
3. Suelte el archivo (`.xls`, `.xlsx` o `.csv`).
4. Pulse «Leer». Sílice muestra el «Informe previo (todavía no se guardó nada)»: filas leídas, rechazadas y
   provisionales.
5. Si está bien, pulse «Confirmar la importación».

Cargar el mismo archivo dos veces no duplica nada.

**Un índice en USD** (para el reajuste de un contrato en dólares). Debajo está «Un índice en USD». Pulse
«Expresar un índice en USD», elija el «Índice en bolívares» (por ejemplo, el INPC) y la «Tasa del BCV»
(venta, salvo que el contrato diga compra) y pulse «Revisar»: Sílice divide el valor de cada mes entre el
promedio de la tasa del BCV de los días de ese mes (cada día con la última tasa publicada, que no puede tener
más de 7 días) y muestra la cuenta del primer y del último mes y los meses a los que les faltan tasas. Si está
bien, pulse «Guardar la serie en USD»: queda como una serie más (por ejemplo, «BCV-INPC-GENERAL-USD») que se
cita en la cláusula del reajuste (sección 9.5). Si después se importa una revisión del índice o más tasas,
revise y guarde otra vez.

### 9.5 Reajuste de precios (quien arma)

Abra la obra y, en «Control de obra», elija la vista «Reajuste» (o busque «Reajuste de precios» con
Ctrl+K). Calcula el reajuste del contrato con una fórmula
de tres componentes (materiales, equipos y mano de obra) y los índices. El resultado es un indicio que se
debe cotejar con la Gaceta.

1. Elija la «Versión del contrato».
2. Pestaña «1. La cláusula»: «Inicio del contrato», «Duración (meses)», «Periodicidad», «Mecanismo»
   («Escalatoria», «Comprobación directa» o ambos), «Estructura», «R (fracción no reajustable)» con su
   fuente, y la serie y el peso de cada componente.
3. Pestaña «2. Períodos y lo ejecutado»: los períodos y lo ejecutado, o la casilla para tomarlo de las
   valuaciones registradas.
4. Pulse «Calcular». Puede «Guardar estudio» y «Descargar Excel».

Si la obra está en USD y un componente cita un índice en bolívares, el resultado lo advierte: ese índice
cuenta dos veces la devaluación. Exprese el índice en USD en «Índices del BCV» (sección 9.4) y cite la serie
en USD en la cláusula.

### 9.6 Convertir la moneda de una versión (quien arma)

En el Presupuesto, pestaña «Ajustes de costo», pulse «Convertir la moneda…». Elija la «Moneda destino», la
«Tasa del BCV» («Venta» o «Compra») y escriba «Por qué se cambia la moneda (fuente)». Pulse «Convertir la
versión». Se crea una versión convertida; la actual no cambia. Antes, guarde o descarte los cambios.

### 9.7 Simulador de listas y escenarios de sensibilidad

Son herramientas de investigación, para quien arma. «Simulador de listas» es una pestaña de «Precios y
catálogo»; «Escenarios», una vista de «Control de obra» en la obra abierta (también las encuentra con
Ctrl+K). «Simulador de listas» genera listas de prueba: no son una
fuente de mercado. «Escenarios de sensibilidad» recalcula un presupuesto guardado cambiando FCAS, bono,
administración, utilidad o precios, sin alterar el original y sin guardar nada. No aparecen en el modo
entrega.

## 10. Obras viales y producción

Esta sección necesita el módulo «Vial» encendido; la planta, el módulo «Producción»; el riesgo, el módulo
«Riesgo».

### 10.1 Tramos de la vía (quien arma)

Haga clic en «Tramos» dentro de la obra. La pantalla se llama «Tramos de la vía». Los tramos se cargan
desde un archivo CSV, uno por versión.

1. Guarde antes una versión del presupuesto. Sin versión, Sílice dice «Esta obra aún
   no tiene versiones guardadas. Guarde una en la Hoja para cargar sus tramos.».
2. Elija la «Versión». Solo se editan los tramos de la versión más reciente que no esté enviada ni
   aprobada.
3. Suelte el archivo `.csv` de la vía en la zona. Verá «Tramos importados: 2 tramos de via.csv.».
4. Revise cada bloque «Tramo T1»: «De 0 a 1,2 km · ancho 7,3 m · planta a 15 km» y la tabla «Partida»,
   «Unidad», «Cantidad». Sílice calcula las cantidades.
5. Pulse «Llevar al presupuesto». Verá «Se llevaron 12 renglones de V-001 a la Hoja de la obra.» y el
   enlace «Abrir la Hoja de la obra», que lleva al Presupuesto.
6. En el Presupuesto, guarde la versión.

Llevar otra vez actualiza los renglones que vinieron de los tramos.

Llevar es todo o nada: si a una partida que sale de los tramos le falta su APU, no se lleva ninguna y
Sílice dice cuáles faltan. Si la que falta es un ligante cuyo APU de riego ya lo trae, o la línea y la
pintura de una línea donde solo se ponen ojos de gato, el mensaje dice cómo declararlo en el archivo
(`suministro` = `sí`, o la demarcación `captafaros`) para que esa partida no salga.

**El archivo de la vía.** Texto UTF-8, columnas separadas por punto y coma. Aquí **sí** se usa coma
decimal (`1,2`); también se acepta punto sin miles (`1234.5`). Máximo 2 MiB. Si una fila está mal, no se
importa nada y Sílice dice cuál.

Columnas obligatorias: `tramo`, `progresiva_ini_km`, `progresiva_fin_km`, `ancho_m`, `distancia_planta_km`,
`elemento`, `tipo`, `espesor_m`, `densidad_t_m3`, `dosis_l_m2` y `lineas`. Opcionales (un archivo sin ellas
se lee igual): `asfalto_pct` (el porcentaje de asfalto de la mezcla de la carpeta o del bacheo),
`esponjamiento` (del fresado, 1 o más: sin él no se calcula el transporte del fresado), `limpieza` (`sí` o
`no`, en la imprimación y el riego), `medicion` (`m2` en el fresado o `t` en la carpeta: la otra unidad de la
partida), `area_m2` (el área de cada elemento de una demarcación `superficie`), `captafaros` (los ojos de gato
de una línea o de una demarcación `captafaros`), `suministro` (`sí` en la imprimación o el riego si su APU ya trae
el ligante: entonces no se calcula el ligante aparte y la dosis es opcional) y `transporte` (vacía, el transporte de la mezcla en t·km; `banda`, en toneladas, con la
distancia como banda en la descripción de la partida). El detalle de cada una está en
`data/samples/vial/README.md`. Una fila por capa o por línea de demarcación; los datos del tramo, también
`transporte`, van en su primera fila. Ejemplo ficticio:

```
tramo;progresiva_ini_km;progresiva_fin_km;ancho_m;distancia_planta_km;elemento;tipo;espesor_m;densidad_t_m3;dosis_l_m2;lineas
T1;0;1,2;7,30;15;capa;fresado;0,05;;;
T1;;;;;capa;riego_adherencia;;;0,40;
T1;;;;;capa;carpeta;0,05;2,35;;
T1;;;;;demarcacion;continua;;;;2
T1;;;;;demarcacion;discontinua;;;;1
T2;1,2;2,0;6,50;18;capa;subbase_granular;0,25;;;
```

`elemento` es `capa` o `demarcacion`. Las capas pueden ser `fresado`, `base_granular`, `subbase_granular`,
`imprimacion`, `riego_adherencia`, `carpeta` o `bacheo`; la demarcación, `continua`, `discontinua` o
`superficie` (pasos peatonales y líneas de pare: `lineas` es el número de elementos iguales y `area_m2` el
área de cada uno); o `captafaros`, ojos de gato solos sobre una línea que la obra no pinta: el número va
en `captafaros`, `lineas` queda vacía y no se calculan la línea ni su pintura).

**Qué calcula Sílice:** volumen de fresado, base y sub-base; área y litros de ligante de imprimación y
riego; área y toneladas de mezcla de la carpeta; toneladas por kilómetro de transporte hasta la planta
(o toneladas, si el tramo dice `banda`); metros de demarcación y litros de pintura. Si el archivo trae
las columnas opcionales, también la limpieza de la superficie, el transporte del fresado, el fresado en
m² y la colocación de la carpeta en toneladas, el área de la demarcación de superficie y los ojos de
gato.

### 10.2 Las reglas viales VR

Cuando la versión tiene tramos, la pestaña «Revisión» del Presupuesto añade las reglas viales. Cada
hallazgo dice su severidad: «Crítico», «Error», «Advertencia» o «Información».

| Regla | Qué revisa | Severidad |
|---|---|---|
| VR1 | Las toneladas de carpeta del presupuesto contra área × espesor × densidad (tolerancia 0,5 %) | Error |
| VR2 | El porcentaje de asfalto del tramo contra la fórmula de trabajo de la receta de la planta (±0,5 puntos) | Advertencia; Información si no hay con qué comparar |
| VR3 | El ligante residual de imprimación o riego dentro de su rango | Advertencia |
| VR4 | Las toneladas por kilómetro del transporte contra toneladas × distancia (tolerancia 0,5 %). Si el tramo mide el transporte por `banda`: las toneladas (error si no cuadran) y si la distancia del tramo cae dentro de la banda de la partida, que Sílice lee de la descripción de su APU (por ejemplo «mayor de 8 km y hasta 10 km»; también «mayores de» o «más de») y dice de dónde la leyó | Error; Advertencia si la distancia cae fuera de la banda; Información si falta la banda o la distancia |
| VR5 | Los litros de pintura por kilómetro de línea, entre 29 y 44 | Advertencia |
| VR6 | Solapes entre tramos (error) y huecos entre progresivas (advertencia) | Error o Advertencia |
| VR7 | Que cada partida sea la que produce esa capa o línea, y en su unidad | Error |
| VR8 | Que una partida que sale de los tramos no esté también escrita a mano (o traída de otro cómputo): se sumarían las dos. Si es la misma obra, quite el renglón que sobra; si es obra distinta, el aviso no aplica | Advertencia |

Para VR2, Sílice busca la receta vigente de la mezcla y su ligante (sección 10.4). Si dice «no se sabe
cuál es el ligante», marque «Es el ligante» en la receta.

### 10.3 Reportes de la vía

En «Tramos», bajo «Reportes en Excel», hay tres descargas: «Cómputos por tramo», «APU con origen y
conciliación» y «Resumen con IVA». Cada libro empieza con una portada que dice de dónde sale cada cifra.

### 10.4 Producción: la arenera y la planta

«Costos de producción», en la barra lateral, abre un espacio con seis pestañas: «Resumen de arenera»,
«Existencias», «Costos del período», «Costo por tonelada», «Receta de la planta» y «Producir mezcla».
La pestaña «Existencias» abre la pantalla «Existencias de la arenera».

**Existencias.** Cuatro pestañas:

- «Existencias»: cuánto hay de cada material, con su «Estado» («Normal», «Queda poco» o «Existencia
  negativa: falta registrar producción o conteo»).
- «Registrar»: «Entrada», «Despacho», «Conteo físico» y «Material nuevo».
- «Importar báscula»: suelte el archivo de pesajes (`.csv` o `.xlsx`) y pulse «Importar».
- «Pesajes sospechosos»: los pesajes que no cuadran; «Revisar» cada uno y resolverlo o descartarlo.

**Receta de la planta.** Dice qué lleva una tonelada de cada mezcla.

1. Para ver una: escriba el «Producto (código)» y la «Fecha» y pulse «Ver la receta vigente». La tabla
   trae «Código», «Cantidad por t», «Unidad», «Tipo» y «Ligante».
2. Para registrar una nueva, pulse «Registrar una receta nueva»:
   - «Producto (código)», «Vigente desde» y «Fuente (dosificación)».
   - Un bloque por componente: «Código», «Cantidad por t», «Unidad» («Toneladas (t)» o «Litros (l)») y
     «Tipo» («Propio (sale del inventario)» o «Comprado (precio de la lista)»).
   - **«Es el ligante»**: marque esta casilla en el asfalto de la mezcla. Con él compara la auditoría de
     los tramos la fórmula de trabajo (regla VR2). Solo un componente puede ser el ligante, y debe ir en
     toneladas. La marca no cambia el costo de la mezcla ni lo que sale del inventario.
   - «Agregar un componente» para el siguiente.
   - La línea «Suma de masa» debe dar entre 0,98 y 1,02 t por t de mezcla (los litros no cuentan). Si no,
     «Registrar receta» no se activa.
3. Pulse «Registrar receta».

Una receta nueva no cambia las anteriores: rige desde la fecha que indique. Una receta ya registrada no
se edita: para marcar el ligante en una vieja, registre otra con la misma dosificación.

Ejemplo ficticio: la mezcla MZ-C lleva 0,55 t de PC-19 (propio), 0,40 t de AR-01 (propio), 0,05 t de
CA-30 (comprado, **es el ligante**) y 8 l de GO (comprado). La fórmula de trabajo es 5 %.

**Producir mezcla.** Elija la «Fecha de la producción», la «Mezcla a producir» y las «Toneladas
producidas». Sílice muestra lo que «Consumirá del inventario». Pulse «Registrar producción».

**Costos del período.** Elija el «Mes» y pulse «Registrar un costo»: «Centro» (Cantera o Planta),
«Concepto», «Monto», «Moneda», «Fecha» y «Fuente (factura o recibo)». Un costo mal anotado se anula con
«Anular» y su motivo.

### 10.5 El costo por tonelada

1. Abra la pestaña «Costo por tonelada» de «Costos de producción».
2. Elija el «Mes» (viene el anterior) y la «Moneda del cálculo» (no tiene valor por defecto).
3. Si quiere, marque «Repartir la cantera por pesos» y ponga el porcentaje de cada agregado (deben sumar
   100 %).
4. Pulse «Calcular costo por tonelada».

El resultado, «Cálculo n.º 3», trae el costo por tonelada de cada agregado y de cada mezcla, el total de
la cantera y de la planta, y lo que pasa al mes siguiente. Cada cálculo se guarda; si vuelve a calcular,
se crea otro.

El administrador puede pulsar «Publicar como precio propio»: el cálculo pasa a una lista «Costo propio
AAAA-MM, cálculo n.º N» que los APU pueden usar. «Descargar el reporte de costo de producción (Excel)»
baja el informe del mes.

### 10.6 Riesgo de la obra

Abra la obra y elija la sección «Riesgo» en su barra (o busque «Riesgo de la obra» con Ctrl+K). Dice
cuánto puede subir el presupuesto si los
precios se mueven como en los meses pasados.

1. Elija la «Versión».
2. En «Plazo y simulación», revise «Fecha de inicio», «Meses del plazo» (6), «Trayectorias» (2.000),
   «Semilla» (1) y «Meses de historia» (36).
3. En «Serie que mueve cada insumo», elija la serie de los insumos que la necesiten.
4. Pulse «Proyectar». Verá «Total base», «P50», «P80» y «Reserva para cubrir el P80», y los tres insumos
   que más empujan. «Descargar el informe de riesgo» lo baja en Excel.
5. «Comprobar hacia atrás» mide cuántas veces acertó esa cuenta en el pasado (tarda cerca de medio
   minuto). La cobertura es un indicador, no una probabilidad.

Al pie, «Mejora de la estimación» compara, al terminar la obra, el costo final con el presupuesto
original y con la estimación de Sílice. Pulse «Calcular la mejora» y, si quiere, «Descargar el informe
de mejora (Excel)».

## 11. Control de obra

«Control de obra», en la barra de la obra, es para quien arma. Su conmutador tiene tres vistas:
«Control» (lo que se explica aquí), «Reajuste» (sección 9.5) y «Escenarios» (sección 9.7).

La vista «Control» compara lo avanzado con lo planificado. Tiene seis pestañas, en este orden de uso:

1. **«Línea base».** Abra «Declarar una línea base» y llene «Versión del contrato» (propone la última
   aprobada), «Vigente desde», «Perspectiva», «Inicio de obra», «Días hábiles por período», «Feriados»
   (fechas como 25/12/2026, separadas por comas) y «Fuente de la línea base». Pulse «Declarar línea
   base». «Días hábiles por período» se llena solo desde el plan de la versión: 1 si va por días, 5 por
   semanas y 20 por meses; si el plan no dice su unidad, propone 20 (un mes) y lo avisa. Puede
   cambiarlo; si lo deja vacío, Sílice lo toma del plan al declarar.
2. **«Valuaciones».** En «Registrar una valuación» escriba «Número», «Período desde», «Período hasta»,
   «Fecha de la valuación» e «Inspector», y una línea por partida medida («Partida», «Cantidad», «Fecha
   de medición», «Observación» y, si hubo, «Causa del retraso»). Pulse «Registrar y controlar». Si el
   contrato repite un código en varios renglones (el mismo trabajo en dos frentes), «Partida» ofrece cada
   renglón con su número («renglón 3 del presupuesto»); al elegirlo se escribe el código y, si la
   observación está vacía, «Renglón 3». La valuación se revisa por código, con la suma de sus renglones. También
   puede «Importar valuaciones de un XLSX», «Anular una valuación» o «Anotar un costo incurrido». La tabla
   muestra el subtotal, el IVA al 16 % y el total con IVA de cada valuación.
3. **«Procura».** «Alertas de compra» y «Materiales de la obra»: cuánto se necesita, cuándo y a más
   tardar cuándo pedirlo. Pulse «Pedida hoy» al hacer el pedido y «Recibida…» al recibirlo (con fecha,
   cantidad, precio y, si quiere, «Declararlo precio del corte»). «Cambiar» ajusta el plazo de entrega.
4. **«Valor ganado».** Elija la «Fecha de corte» y los «Precios del corte» y pulse «Calcular al corte».
   Verá los indicadores y la curva «PV, EV y AC al cierre de cada período».
5. **«Alertas y reproyección».** Las alertas, el atraso por partida, el término, el costo final y el plan
   reproyectado.
6. **«Recuperación».** Si la obra va atrasada, escriba el «Día hábil objetivo» y pulse «Calcular
   opciones». Elija una en «Opción a aplicar» y pulse «Elegir y crear la versión».

Sin línea base, las demás pestañas piden «Declare primero la línea base de control».

## 12. Auditar un presupuesto

«Auditar un presupuesto», en la barra lateral, abre un espacio con tres pestañas: «Subir y auditar
Excel» (la pantalla «Inicio de auditoría»), «Libro de la empresa» e «Historial de auditorías». Sirve
para revisar un
presupuesto en Excel, propio o de terceros. El archivo no se guarda: solo quedan el resumen y los
hallazgos.

### 12.1 Auditar un libro

1. Suelte el `.xlsx` en «Suelte aquí el libro .xlsx del presupuesto, o haga clic para elegirlo».
2. Pulse «Auditar por mi cuenta», o «Auditar con recorrido guiado» si es la primera vez (sección 12.4).
3. Se abre «Libro de la empresa». Mientras trabaja dice «Leyendo el libro y auditándolo…».

Los topes de seguridad de la sección 12.5 (filas, columnas y celdas del libro entero) valen para todo libro
que se audita o se abre en el visor: si el libro los pasa, Sílice lo rechaza con el mismo aviso y le dice la hoja.

### 12.2 Leer el resultado

- **Arriba, tres indicadores:** «Subtotal sin IVA», «IVA» y «Total general». Cada uno trae la cifra del
  libro, «Según Sílice …» y la diferencia con la palabra «favorable» o «desfavorable».
- **Libro contra Sílice.** Si el libro dice **menos** que Sílice, sale «favorable» en verde, pero con la
  nota «Libro menor»: un libro que olvidó partidas o costos también sale menor. Lea la nota completa en
  «Total general» y revise antes de aceptar.
- **A la izquierda, la hoja del libro**, tal como está, con las celdas marcadas. Hay botones para acercar
  y alejar.
- **A la derecha, «Hallazgos (n)»**, con filtros «Crítico», «Error», «Advertencia» e «Información». Haga
  clic en un hallazgo para ir a su celda. Los que caen en filas ocultas o fuera del libro van en grupos
  aparte.

Si no hay nada que objetar, verá «La auditoría terminó y el libro no tiene hallazgos.».

### 12.3 El historial

Abra la pestaña «Historial de auditorías» de «Auditar un presupuesto». Filtre por fechas, tipo y
resultado. «Ver el detalle»
muestra quién la hizo, los totales, los hallazgos y la huella del archivo.

Las últimas auditorías también aparecen en «Inicio de auditoría», bajo «Últimas auditorías guardadas».

### 12.4 El recorrido guiado

Con «Auditar con recorrido guiado» aparece a la derecha la columna «Recorrido», con tres pasos: «Suba el
libro», «Lea el resumen y los hallazgos» y «Compruebe que quedó guardada». Cada paso dice qué hacer y
cuándo terminó. «Ocultar» la pliega y «Terminar recorrido» la quita. Si la plegó, el botón «Recorrido» de
la barra de arriba la vuelve a mostrar.

El recorrido también se empieza desde su Cuenta, sección «Ayuda y acerca de Sílice», con «Empezar el
recorrido «Auditar un libro de la empresa»».

Quien solo administra entra a esta pantalla pero no puede auditar: Sílice le pide que lo haga alguien que
arma o revisa.

### 12.5 Auditar un libro con un APU por hoja

Algunos programas de APU exportan un libro con **una hoja por partida** (solo valores, sin fórmulas) y,
aparte, el libro del presupuesto. Ese libro no es el de la plantilla de la sección 12.1: se audita en su
propio bloque, «Libro con un APU por hoja», más abajo en «Inicio de auditoría».

1. En «Perfil del libro», elija cómo se lee el libro. Cada opción dice qué hoja del presupuesto compara y
   de dónde viene: «apu_por_hoja · lee la hoja PRESUPUESTO (del paquete)», o «(de esta instalación)» si
   quien administra puso un perfil propio. Con un presupuesto de varios frentes (una hoja por frente),
   las hojas se eligen al soltar el presupuesto (ver «Un presupuesto con una hoja por frente», abajo). Un
   perfil mal escrito sale con «no se puede usar:» y el motivo, y
   no se puede elegir. Si la lista no se pudo leer, dice «No se pudo leer la lista de perfiles: se audita
   con apu_por_hoja.».
2. Suelte el `.xlsx` de los APU en «Suelte aquí el .xlsx de los APU (una hoja por partida), o haga clic
   para elegirlo».
3. Si tiene el del presupuesto, suéltelo en «Opcional: suelte aquí el .xlsx del presupuesto, o haga clic
   para elegirlo». Debajo se lee lo elegido: «Libro de APU: … · Presupuesto: …».
4. Pulse «Auditar el libro de APU». Mientras trabaja dice «Recalculando cada hoja...».

**El resultado.**

- Arriba, el perfil con que se leyó y los archivos: «Perfil apu_por_hoja (del paquete) · …», o «(de esta
  instalación)» si quien administra puso un perfil propio; al final, «· con …» y la hoja que se leyó
  («(hoja PRESUPUESTO)»), o «· sin libro de presupuesto».
- Si la hoja del presupuesto parece de otra obra (casi ningún renglón tiene la cantidad de su hoja de
  APU), un aviso «La hoja del presupuesto parece de otra obra» lo dice arriba de las tablas: revise el
  perfil elegido.
- La tabla «Precio unitario de cada hoja»: «Hoja», «Código», «Partida», «P.U. impreso» y «P.U. de
  Sílice». Sílice no cree el precio impreso: recalcula cada hoja con sus renglones. «No evaluable» quiere
  decir que esa hoja trae algo que Sílice no reproduce (lo explica un hallazgo).
- La tabla «Hallazgos del libro»: «Severidad», «Regla», «Celda» y «Qué dice». La celda es la del libro,
  por ejemplo `APU 2!G29`. Si no hay nada, dice «Sin hallazgos: cada hoja cuadra con lo impreso.».
- Si algún material trae desperdicio, la lista «Materiales con desperdicio» dice, por cada uno, la
  cantidad que resulta, la neta y el porcentaje, por ejemplo «Emulsión asfáltica: 0,52 l (0,5 + 4 %)».

| Regla | Qué dice | Severidad |
|---|---|---|
| AH1 | El precio unitario impreso no es el que recalcula Sílice. Si la diferencia sale solo de redondear cada renglón a dos decimales, lo explica | Error; Información si es solo redondeo |
| AH2 | La mano de obra trae un bono por renglón: la hoja no se evalúa | Información |
| AH3 | La hoja tiene financiamiento: no se evalúa | Información |
| AH4 | La hoja suma un impuesto dentro del APU (el IVA va sobre el total): su precio no se compara | Advertencia |
| AH5 | El precio unitario del presupuesto no es el que imprime su hoja | Error |
| AH6 | La cantidad del presupuesto no es la de la cabecera de su hoja | Advertencia |
| AH7 | Un renglón del presupuesto sin hoja, o una hoja sin renglón | Advertencia |
| AH8 | Una unidad del libro leída como otra («lt» como «l»): la traducción queda dicha | Información |
| AH9 | La banda de distancia del transporte, leída de la descripción («mayor de 8 km y hasta 10 km») | Información |
| AH10 | Dos hojas con el mismo número de renglón: el presupuesto se enlaza con la primera | Advertencia |
| AH11 | La hoja del presupuesto parece de otra obra: de los renglones enlazados (dos o más), menos de la mitad tienen la cantidad de su hoja. Suele ser un perfil que lee la hoja de otro frente | Advertencia |

Cada renglón del presupuesto se enlaza con la hoja que tiene su número («Partida N°» en la cabecera de la
hoja). Con el perfil del paquete, Sílice lee solo las hojas cuyo nombre empieza por «APU» y, del
presupuesto, la hoja «PRESUPUESTO»; las demás no las lee.

Si una hoja no trae lo que hace falta para recalcularla, sale «No se auditó el libro» con la hoja y lo
que falta. Si trae un valor imposible (un precio negativo, un rendimiento cero), dice también la celda, por
ejemplo «APU 9!F9: el precio
de «Cemento» es -1 y no puede ser negativo: Sílice no recalcula la hoja «APU 9».». Corrija esa celda en
el libro y vuelva a auditar.

Por seguridad, Sílice lee de cada hoja hasta 20.000 filas y 100 columnas (de la A a la CV), y del libro
entero hasta 4.000.000 de celdas. Cuentan también las celdas que solo tienen formato (un color, un borde, un
alto de fila), aunque estén vacías: si el aviso dice que una fila tiene «celdas con datos o con formato»
más allá de la CV y usted no ve nada escrito, seleccione esas columnas o filas sobrantes, bórrelas (no solo
su contenido) y guarde el libro de nuevo.

Nada se guarda: ni los libros ni el informe, y esta auditoría no entra en «Historial de auditorías».

**Un presupuesto con una hoja por frente** (una estación, un tramo, un sector). Al soltar el libro del
presupuesto, Sílice lee los nombres de sus hojas y los ofrece en «Hojas del presupuesto que se comparan», con
marcadas las que lee el perfil. Marque las del frente de este libro de APU (o varias, si el libro de APU sirve a
todos los frentes). Si el perfil lee una hoja que el libro no tiene, lo dice: «El perfil lee la hoja PRESUPUESTO,
que este libro no tiene: marque las hojas que quiere comparar.». Con varias hojas, el precio de cada renglón se
compara en cada hoja (AH5 dice «hoja FRENTE B») y la cantidad del APU con la **suma** de las hojas («las hojas
FRENTE A y FRENTE B del presupuesto suman una cantidad de 450 y su APU dice 500»). Dos reglas más:

| Regla | Qué dice | Severidad |
|---|---|---|
| AH12 | Hojas del libro de APU que no empiezan por el prefijo del perfil y no se leyeron (las nombra, hasta diez). Si alguna es un APU, revise el prefijo del perfil | Información |

Si el perfil declara «Otros impuestos», esa segunda fila del pie se suma al impuesto de la hoja y AH4 dice las dos
partes («un impuesto del 18 % (16 % y otros impuestos del 2 %)»).

**Poner el perfil de un libro de la empresa.** Quien administra lo hace en «Cuenta › Empresa», bloque «Perfiles de
los libros de la empresa»: suelte el `.json` del perfil y pulse «Poner el perfil». Sílice lo revisa entero antes de
guardarlo y dice el motivo si está mal escrito; si ya hay uno con ese nombre, pide marcar «Reemplazar el que ya
está con ese nombre» (un archivo de otro tipo de perfil con ese nombre no se pisa nunca: póngale otro nombre). El patrón de la banda de distancia (`patron_banda`) no puede pasar de 300 caracteres, y Sílice rechaza las formas que con algunos textos tardarían sin fin: una repetición dentro de otra sin un separador fijo que marque dónde acaba cada vuelta («(a+)+», «(?:a?a)+», «(?:\d+\.?)+»; en cambio «(?:\.\d{3})*», las cifras con punto de miles, sí se acepta, porque el punto separa), una alternativa repetida («(a|aa)+»), una referencia hacia atrás y más de una parte variable que pueda quedarse con los mismos caracteres («.*de.*km», varios «[0-9]*» seguidos). Es un control de la forma, no una garantía: acepta las bandas bien escritas («de 1.000 a 1.250 km», «mayores de 8 km y hasta 10 km», «entre 8 y 10 kms») y, si rechaza la suya, el mensaje dice qué parte cambiar (un «.*» o un «.*?» al principio sobra: la banda se busca en cualquier parte de la descripción). Al terminar dice qué hojas del presupuesto lee: «Perfil «obra_local» puesto en esta
instalación: lee las hojas FRENTE A y FRENTE B.». El perfil se guarda solo en esta instalación.

### 12.6 Llevar el libro a la Hoja y el presupuesto por frente

Después de auditar el libro, quien arma lo lleva a la Hoja de la obra elegida en la barra de arriba, sin teclear:

1. En «Llevar el libro a la Hoja», elija la «Moneda de los precios del libro» (Bs o USD): Sílice no la adivina y no
   cambia la moneda de ningún precio. Sin presupuesto, puede escribir el «Frente de los renglones».
2. Pulse «Llevar el libro a la Hoja de «…»». Cada APU entra al catálogo con sus materiales, equipos y mano de obra,
   su rendimiento y sus precios (cada precio con su fuente: el libro y la celda, que se ve en la pestaña Precios), y
   cada renglón del presupuesto entra a la Hoja con su cantidad y su frente (la hoja del presupuesto de donde
   salió). Los porcentajes del libro (prestaciones, administración y utilidad) pasan a la Hoja.
3. Sale «Se llevaron 10 renglones a la Hoja de «…», sin guardar: ábrala para revisarlos y guardar la versión.» y la
   tabla «Partidas llevadas a la Hoja»: el código en Sílice, la hoja del libro, el P.U. del libro, el de la Hoja y
   si «Casa» (hasta un centavo) o «No casa». Una hoja con financiamiento o con bono por renglón no casa: la
   auditoría ya lo dijo (AH2, AH3). Debajo, los renglones que no se llevaron (sin hoja de APU o sin cantidad).

El libro se lleva a una **obra sin versiones** (cree una obra nueva para el libro), para que sus precios sean los
del libro, y su moneda debe ser la de la carpeta y la de la obra (una obra en USD no recibe un libro en Bs: Sílice no convierte sus precios). Si el código de un APU ya está en el catálogo con otro APU (otro
frente con otro precio), entra como variante «…-B». Llevar el mismo libro otra vez no duplica nada: reemplaza los
renglones de esas hojas.

**El presupuesto por frente.** En la pestaña Presupuesto de la Hoja, debajo del total, pulse «Ver el presupuesto
por frente»: la tabla «Presupuesto por frente» da cada frente, sus renglones (y cuántos están pendientes) y su
subtotal, y debajo el «Total general». Las cifras las calcula Sílice; los renglones sin frente van al final, en
«(sin frente)», como en el PDF. Para poner el frente de un renglón a mano, elíjalo en «Renglón», escriba el «Frente» y
pulse «Poner el frente» (vacío lo quita). Un frente no puede llamarse «Sin frente» ni «(sin frente)», para que no se
confunda con ese grupo: ni a mano ni desde el libro (a una hoja del presupuesto con ese nombre, cámbiele el nombre). El frente se guarda con la versión.

## 13. El asistente de IA

Hoy la interfaz de Sílice **no tiene** una ventana para conversar con el asistente de IA. No hay botón ni
panel del asistente en el Presupuesto ni en otra sección.

Lo único que existe es su configuración, para quien administra, en su Cuenta, sección «Especialidades,
IA e instalación», bloque «Asistente de IA»:

- **«Configuración del asistente»**: la casilla «Activar el asistente de IA (viene apagado)», el «Proveedor
  por defecto» («Claude (en la nube, con la clave de la empresa)» u «Ollama (local, en este equipo)»), los
  modelos, la «Dirección de Ollama» y el «Tope de costo por sesión (USD)». Botón «Guardar la
  configuración».
- **«Clave de IA de la empresa»**: «Registrar la clave», «Reactivar la clave» u «Olvidar la clave». La
  clave se registra solo desde el equipo donde está instalado Sílice, se guarda en el almacén de
  credenciales de Windows y no viaja en los respaldos.

El aviso «Asistente en la nube» explica qué saldría del equipo si se usa la nube: el pedido y un resumen
del borrador, sin precios, montos ni nombres de obra, empresa o personas.

Dejar esto configurado no agrega todavía ninguna pantalla. Cuando el asistente llegue a la interfaz, este
manual lo explicará.

## 14. Problemas frecuentes

### 14.1 Al entrar

| Mensaje | Qué pasa | Qué hacer |
|---|---|---|
| «El código de instalación no es válido o ya se usó.» | El código está mal copiado, ya se usó o no existe | Cópielo otra vez del archivo `codigo_instalacion.txt`. Si ya se usó, entre con la cuenta creada |
| «Usuario o contraseña incorrectos.» | Uno de los dos está mal | Revise mayúsculas y el teclado. Si la olvidó, pida al administrador que la restablezca |
| «Demasiados intentos fallidos. Espere 15 minutos o pida al administrador que desbloquee la cuenta.» | La cuenta se bloqueó | Espere, o que el administrador pulse «Desbloquear» |
| «Demasiados intentos fallidos en este equipo. Espere unos segundos y vuelva a probar.» | Muchos intentos seguidos | Espere los segundos que indica el botón |
| «Esa contraseña es demasiado común; elija otra.» | La contraseña es muy conocida | Use una frase larga |
| «Su contraseña es temporal: elija una propia antes de seguir.» | Entró con la contraseña temporal | Cámbiela (sección 2.4) |
| «Su sesión venció. Entre de nuevo para seguir.» | Pasó mucho tiempo sin actividad | Entre otra vez |
| «No se pudo hablar con el programa de Sílice. Compruebe que esté encendido.» | La consola de Sílice está cerrada | Cierre la ventana de Sílice y abra «Sílice» desde el menú Inicio |
| «Sílice se detuvo» (en la ventana) | El servidor de Sílice terminó con la ventana abierta | Cierre la ventana y abra «Sílice» otra vez; si se repite, envíe el archivo de la carpeta `%LOCALAPPDATA%\Silice\registros` |

### 14.2 Mientras trabaja

| Mensaje | Qué pasa | Qué hacer |
|---|---|---|
| «Sin permiso» / «Su cuenta no tiene permiso para esta pantalla o acción.» | Su papel no incluye esa pantalla | Pídale al administrador el papel que corresponda |
| «Apagada» / «Esta función está apagada en esta instalación…» | El módulo está apagado | El administrador lo enciende en su Cuenta, «Especialidades, IA e instalación» › «Especialidades» |
| «Esa obra ya no existe» | La obra se borró o su carpeta no está | Pulse «Volver a Pendientes»: lo lleva a la bandeja de Pendientes |
| «Ya existe una obra llamada «…»: elija otro nombre o abra esa.» | El nombre está repetido en la carpeta | Use otro nombre |
| «Escriba un número. Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.» | La cifra se escribió con punto decimal (2.5) o con otro formato | Escriba 2,5 o 1.234,56 |
| «Elija la partida de la lista de sugerencias.» | Escribió en «Partida» pero no eligió | Elija una opción de la lista |
| «La partida «…» no está en el catálogo: compóngala primero en Componer.» | La partida no existe | Use «Componer una partida» (sección 4.3) |
| «El cálculo da … y la cantidad es …: corrija uno de los dos.» | El cálculo y la cantidad no coinciden | Corrija uno de los dos |
| «El borrador cambió en otra ventana: vuelva a cargarlo.» | Tiene la obra abierta en dos pestañas | Pulse «Recargar el borrador» y trabaje en una sola pestaña |
| «Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó)…» | Sílice se reinició con cambios sin guardar | Pulse «Abrir de nuevo»; lo no guardado se perdió |
| «Otra persona guardó la versión … después de que usted abrió la …» | Alguien guardó antes que usted | Lea el aviso y elija «Guardar de todos modos» o «Abrir la versión …» |
| «Escriba la fuente del cambio: por qué se cambia y con qué respaldo.» | Falta el motivo al guardar | Escríbalo en el diálogo de guardar |
| «No hay cambios para guardar: edite alguna celda primero.» | No hay nada nuevo que guardar | Nada que hacer |
| «La versión V-004 fue devuelta: corríjala en una versión nueva y envíe esa.» | Intentó reenviar una devuelta | Haga una versión nueva (sección 6.7) |
| «Escriba las notas: son obligatorias para devolver o aprobar con observaciones.» | Faltan las notas del dictamen | Escríbalas |
| «No se puede enviar …: la cadena de versiones de esta obra está rota en la versión …» | La base se cambió por fuera de Sílice | Avise al administrador (sección 6.9) |
| «No hay tasa del BCV del dd/mm/aaaa (hace falta la del mismo día)…» | Falta la tasa de ese día | El administrador la carga en «Índices del BCV» (sección 9.4) |
| «Esta carpeta de trabajo aún no tiene moneda: declárela o cree su lista para armar antes de estudiar el mercado.» | La carpeta no tiene moneda ni lista | Cree la lista para armar (sección 4.3, camino 3) |
| «Las propuestas no están disponibles» | Falta el módulo de partidas parecidas | Instale con `Silice-<versión>-completo.exe`; sus datos se conservan |
| «Solo se aceptan archivos .dxf o .ifc o .csv.» | El archivo tiene otra extensión | Use un plano DXF o IFC, o un cómputo CSV |
| «el archivo '…' es ilegible: no es un CSV de texto en UTF-8» | El CSV se guardó en otra codificación | En Excel use «Guardar como» y elija «CSV UTF-8» |
| «el archivo '…', fila '…': la columna '…' esta vacia o no es numerica» | En el cómputo, una cifra lleva coma decimal o está vacía | En el cómputo use punto decimal (sección 4.7) |
| «El plano … pesa más de … MiB…» | El plano es muy grande | Purgue capas y bloques que no use, o divídalo por plantas |
| «Esta versión no se puede guardar: alguna partida ya no tiene composición vigente en el catálogo.» | Una partida perdió su composición | Revise el catálogo; quien arma la compone de nuevo |
| «La pantalla no cargó. Vuelva a cargar Sílice (F5)…» | Falló una pantalla | Pulse F5; si sigue, avise al administrador |

### 14.3 Para quien administra el equipo

- **La carpeta de la empresa.** Al arrancar, el lanzador de Sílice fija la carpeta de trabajo de la
  empresa con la variable `SILICE_CASO`, y el modo entrega con `SILICE_MODO_ENTREGA=1` (que oculta el
  Simulador de listas y los Escenarios de sensibilidad). Los nombres anteriores, `ARENIA_CASO` y
  `ARENIA_MODO_ENTREGA`, ya no se aceptan desde la 0.7.0. Los detalles están en el [manual
  técnico](manual_tecnico.md).
- **La instalación nueva no muestra «Bienvenida a Sílice».** Ya hay una cuenta creada: use «Entrar», o
  «Perdí el acceso de administrador» (sección 2.5).
- **Una persona no ve sus obras.** Revise sus papeles en su Cuenta, «Cuentas y permisos»: para ver
  obras necesita «arma» o «revisa».

## 15. Lo que cambió respecto del manual anterior

El manual anterior describía la interfaz de Streamlit y la primera interfaz nueva. Estas pantallas ya no
existen; su función está ahora en otro lugar:

| Antes | Ahora |
|---|---|
| «Inicio» con la lista de casos y los recorridos | La «Vista general» al entrar (sección 3.4); las carpetas de trabajo en la Cuenta › «Carpetas»; el recorrido guiado en «Auditar un presupuesto» y en la Cuenta › «Ayuda y acerca de Sílice» |
| La barra de herramientas («Proyecto», «Guardar version», «Exportar Excel»…) | La barra lateral con las obras; las secciones en la barra de cada obra; «Nueva obra»; guardar en la franja del paso; «Descargar Excel» en el Presupuesto |
| «Pendientes» como primera pantalla | La «Vista general»; la bandeja «Pendientes» es su segunda pestaña (sección 3.5) |
| Las secciones de la obra desplegadas en la barra lateral | La barra de secciones bajo el nombre de la obra; la barra lateral solo lista las obras (sección 3.6) |
| La zona «Empresa» de la barra lateral | El grupo «Costos y producción»; «Empresa y personas» y «Ayuda» pasaron a la Cuenta |
| La pantalla «Administración», con siete pestañas | Cuatro secciones de la Cuenta: «Cuentas y permisos», «Empresa y tema», «Carpetas» y «Especialidades, IA e instalación» (sección 2.7) |
| Las migas («Mis obras / … / Presupuesto») y el tamaño de letra en la barra de arriba | La barra de arriba muestra la carpeta activa; el tamaño de letra está solo en la Cuenta › «Pantalla y tamaño de letra» |
| «Salir» en el menú de la cuenta | «Salir de la sesión», arriba de su Cuenta (sección 3.9) |
| «Tablero del proyecto», «Componer una partida», «Entregar paquete», «Revisar un paquete», «Actualizar precios», «Reajuste de precios», «Escenarios de sensibilidad» y «Riesgo de la obra» solo con Ctrl+K | Vistas y secciones de la obra (secciones 1.3 y 3.6); Ctrl+K las sigue encontrando |
| «Precios de la empresa», «Índices del BCV», «Libro de la empresa», «Historial de auditorías» y las pantallas de producción solo con Ctrl+K | Pestañas de «Precios y catálogo», «Auditar un presupuesto» y «Costos de producción» |
| «Elaborar un presupuesto» | «Archivos y planos» › «Subir plano o cómputo» › «Cargar cómputo» |
| «Partidas similares» | «Agregar partida» › «Buscar parecidas», dentro del Presupuesto |
| «Histórico de precios» como pantalla suelta | La pestaña «Histórico de precios» de «Mercado» |
| «Hoja del proyecto» u «Hoja de la obra», con nueve pestañas | «Presupuesto», con seis pestañas (siete con «Espacio y metrajes») |
| La pestaña «Parámetros» | La pestaña «Ajustes de costo» |
| La pestaña «Trazabilidad» y el selector «Versión» de la hoja | La sección «Versiones» de la obra |
| El APU en tres paneles | El APU en el panel lateral, al pulsar el código de la partida |
| Componer solo en su pantalla | También en el panel «Componer una partida», sin salir de la obra |
| La herramienta «Importar plano» | «Archivos y planos» › «Subir plano o cómputo» |
| El panel de chat del asistente de IA | No existe en la interfaz actual; solo su configuración (sección 13) |
| El Visor 3D del modelo | Retirado |
| La creación del primer administrador, pendiente | La pantalla «Bienvenida a Sílice» con el código de instalación |
| Las guías de cada tarea solo en este manual | También dentro de Sílice: «¿Qué es esto?» en cada pantalla, «Empieza aquí» en la Vista general la primera vez, y guías y glosario en la Cuenta › «Ayuda y acerca de Sílice» (sección 3.10) |
| Un presupuesto se podía valorar y auditar fuera de una obra | Todo presupuesto vive en una obra; para revisar un Excel suelto use «Auditar un presupuesto» |
