import { useEffect, useState } from "react";
import type { JSX } from "react";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { CarpetaRespuesta } from "../api/tipos";
import { fechaEsVe } from "../indicadores/formatoEsVe";

// E2E-3: la cabecera se leía solo al montarse y, tras crear la lista para armar en Componer, seguía diciendo que la carpeta
// no la tenía hasta recargar. Quien cambia la lista de la carpeta lo avisa con `avisarCambioDeLaCarpeta` (un evento de la
// ventana, sin estado compartido) y la cabecera la vuelve a leer.
const CAMBIO_DE_LA_CARPETA = "silice:cambio-de-la-carpeta";

export function avisarCambioDeLaCarpeta(): void {
  window.dispatchEvent(new Event(CAMBIO_DE_LA_CARPETA));
}

// «{nombre}, al {dd/mm/aaaa}», sin repetir la fecha cuando el nombre ya termina con ella: las listas derivadas se
// llaman «… al 26/10/2026» (o «… al 26/10/2026 (2)»). Decision por defecto del orquestador, por ratificar de Eugenio.
export function nombreConFecha(lista: { nombre: string; fecha: string }): string {
  const fecha = fechaEsVe(lista.fecha);
  const final = / al (\d{2}\/\d{2}\/\d{4})(?: \(\d+\))?$/.exec(lista.nombre);
  return final?.[1] === fecha ? lista.nombre : `${lista.nombre}, al ${fecha}`;
}

// «La carpeta dice lo que tiene» (diseno de montar §5.1, O-1; D-MP1): en la cabecera de la obra abierta (marco nuevo,
// Tarea 8; la especificacion pide alli la lista de precios), la moneda de su carpeta (la de la obra) y su lista para armar
// (`GET /v1/carpeta`, T2), o por que no la tiene. Se lee al montarse: cada vez que se entra en una obra.
export function ListaDeLaCarpeta(props: { alExpirar: () => void; monedaDeLaObra: string | null | undefined }): JSX.Element {
  const { alExpirar, monedaDeLaObra } = props;
  const [carpeta, setCarpeta] = useState<CarpetaRespuesta | null>(null);
  const [fallo, setFallo] = useState(false);
  const [lecturas, setLecturas] = useState(0);

  useEffect(() => {
    const releer = () => setLecturas((n) => n + 1);
    window.addEventListener(CAMBIO_DE_LA_CARPETA, releer);
    return () => window.removeEventListener(CAMBIO_DE_LA_CARPETA, releer);
  }, []);

  useEffect(() => {
    let vigente = true;
    pedir<CarpetaRespuesta>("/v1/carpeta")
      .then((r) => {
        if (!vigente) return;
        setCarpeta(r);
        setFallo(false);
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        else setFallo(true);
      });
    return () => {
      vigente = false;
    };
  }, [alExpirar, lecturas]);

  let texto: string;
  if (fallo) texto = "No se pudo leer la moneda de la carpeta.";
  else if (carpeta === null) texto = "Leyendo la moneda de la carpeta…";
  else if (carpeta.moneda === null) {
    // La carpeta no declaró moneda ni tiene lista: la moneda es la de la obra abierta, y solo sin ella se dice que falta.
    if (monedaDeLaObra === undefined) texto = "Leyendo la moneda de la carpeta…";
    else if (monedaDeLaObra !== null) texto = `Moneda: ${monedaDeLaObra} · ${carpeta.aviso ?? "Sin lista para armar"}`;
    else texto = "Carpeta sin moneda declarada";
  } else if (carpeta.aviso !== null || carpeta.lista === null)
    texto = `Moneda: ${carpeta.moneda} · ${carpeta.aviso ?? "Sin lista para armar"}`;
  else
    texto = `Moneda: ${carpeta.moneda} · Lista para armar: ${nombreConFecha(carpeta.lista)}`;

  return <p className="silice-obra-abierta__lista cds--type-helper-text-01">{texto}</p>;
}
