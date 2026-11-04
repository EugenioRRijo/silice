import { useCallback, useId, useState } from "react";
import { cifrasEnTextoEsVe } from "../../indicadores/formatoEsVe";
import { pedir } from "../../api/cliente";
import { useAplicacion } from "../../shell/contexto";
import { AvisoDeEdicion, AvisoDeEnvio } from "./AvisoDeEdicion";
import { AyudaDePestana } from "./AyudaDePestana";
import { CampoDeCelda } from "./CampoDeCelda";
import { ConvertirMoneda } from "./ConvertirMoneda";
import type { AlCrearVersion } from "./logicaVersiones";
import { VistaCarga } from "./VistaCarga";
import { rutaDeVista } from "./logica";
import type { BaseAbierta, Resumen, VistaParametros } from "./logica";
import { FRASES_DE_RECHAZO, cuerpoDeParametros, rutaDeParametros, sembrarParametros, ubicarErrorDeParametro } from "./logicaSecciones";
import type { UbicacionDeParametro, ValoresDeParametros } from "./logicaSecciones";
import { useEdicionDeSeccion } from "./useEdicionDeSeccion";
import { usePuedeEditarLaHoja } from "./puedeEditar";

interface Props {
  id: string;
  // El `rev` del borrador según la página.
  rev: number;
  alAusente: () => void;
  // El servidor aceptó una edición: su resumen pasa a la barra de estado de la página.
  alAceptar: (resumen: Resumen) => void;
  alRecargarBorrador: () => Promise<void>;
  // Descarta lo que se ve y abre otro borrador de la versión (cuando recargar no sirve).
  alReabrir: () => void;
  // La base del borrador: con `solo_lectura` (o sin permiso de edición) no se pinta nada que escriba (F4 2b).
  base?: Pick<BaseAbierta, "solo_lectura">;
}

// Lo que hace falta para convertir la moneda (S5): la versión guardada abierta, los cambios sin guardar y qué hacer al crearse
// una versión.
export interface Conversion {
  proyecto: string;
  version: string | null;
  cambios: number;
  alCrearVersion: AlCrearVersion;
}

interface PropsContenido extends Props {
  conversion?: Conversion;
  vista: VistaParametros;
  alRelectura: () => void;
}

function ContenidoParametros({ id, rev, vista, alAusente, alAceptar, alRecargarBorrador, alReabrir, alRelectura, conversion, base }: PropsContenido) {
  const { alExpirar, sesion } = useAplicacion();
  const puedeEditar = usePuedeEditarLaHoja(base ?? null);
  const idDelError = useId();
  const edicion = useEdicionDeSeccion<ValoresDeParametros, UbicacionDeParametro>({
    borrador: id,
    inicial: sembrarParametros(vista.campos),
    rev,
    peticion: (r, valores) => ({ ruta: rutaDeParametros(id), metodo: "PUT", cuerpo: cuerpoDeParametros(r, valores) }),
    ubicar: ubicarErrorDeParametro,
    frase: FRASES_DE_RECHAZO.parametros,
    leerFresca: async () => sembrarParametros((await pedir<VistaParametros>(rutaDeVista(id, "parametros"))).campos),
    alAceptar,
    alRelectura,
    alRecargarBorrador,
    alAusente,
    alExpirar,
  });
  const { error } = edicion;
  const ubicacion = error?.ubicacion ?? null;

  return (
    <div className="silice-hoja__pestana">
      <AyudaDePestana id="ajustes" puedeEditar={puedeEditar} />
      <AvisoDeEnvio envio={edicion.envio} />
      {error !== null && <AvisoDeEdicion error={error} id={idDelError} alRecargar={() => void edicion.recargar()} alReabrir={alReabrir} />}
      <div className="silice-hoja__campos">
        {vista.campos.map((c) => (
          <CampoDeCelda
            soloLectura={!puedeEditar}
            key={c.clave}
            id={`hoja-parametro-${c.clave}`}
            etiqueta={cifrasEnTextoEsVe(c.rotulo)}
            etiquetaVisible
            valor={edicion.estado[c.clave] ?? ""}
            invalido={ubicacion !== null && ubicacion.campo === c.clave}
            textoInvalido={ubicacion?.texto}
            descripcionId={idDelError}
            alCambiar={(valor) => edicion.cambiar((previo) => ({ ...previo, [c.clave]: valor }))}
            alRestaurar={() => edicion.cambiar((previo) => ({ ...previo, [c.clave]: edicion.aceptado()[c.clave] ?? "" }))}
          />
        ))}
      </div>
      {/* Convertir crea una versión desde la GUARDADA: su regla es solo el permiso (`convertir_y_reajustar`, y el
          `puede_convertir` que da la API), no la base del borrador (Eugenio, 2026-10-31). */}
      {conversion !== undefined && sesion.acciones.includes("convertir_y_reajustar") && (
        <ConvertirMoneda
          proyecto={conversion.proyecto}
          version={conversion.version}
          monedaActual={vista.moneda_proyecto}
          puedeConvertir={vista.puede_convertir}
          cambios={conversion.cambios}
          alCrearVersion={conversion.alCrearVersion}
        />
      )}
    </div>
  );
}

// Pestaña «Parámetros»: los cuatro se editan como texto (rebanada 3c-2) y se aplican al borrador del servidor; convertir la
// moneda crea una versión nueva desde la guardada (3d-2).
export function PestanaParametros(props: Props & { conversion: Conversion }) {
  // Sube cada vez que hay que volver a leer la vista tras una edición: la anterior sigue a la vista mientras llega.
  const [lecturas, setLecturas] = useState(0);
  const alRelectura = useCallback(() => setLecturas((n) => n + 1), []);
  return (
    <VistaCarga<VistaParametros> ruta={rutaDeVista(props.id, "parametros")} etiqueta="Parámetros" alAusente={props.alAusente} recarga={lecturas}>
      {(vista) => <ContenidoParametros {...props} vista={vista} alRelectura={alRelectura} />}
    </VistaCarga>
  );
}
