// Contrato de /v1/revision (api/rutas/revision.py). Los montos llegan como texto: el exacto y, en `*_texto`, como los
// escribe la pantalla clasica (dos decimales; cuatro en lo declarado y lo recalculado). La interfaz no calcula.

export interface HallazgoRevision {
  regla: string;
  severidad: string;
  descripcion: string;
}

export interface LoteDeHallazgos {
  titulo: string;
  hallazgos: HallazgoRevision[];
}

export interface DiferenciaDePrecio {
  codigo_partida: string;
  campo: string;
  declarado: string;
  declarado_texto: string;
  recalculado: string;
  recalculado_texto: string;
  monto: string;
  monto_texto: string;
}

export interface PartidaDiferente {
  codigo_partida: string;
  descripcion: string;
  estado: string;
  desvio_cantidad: string;
  desvio_cantidad_texto: string;
  desvio_precio: string;
  desvio_precio_texto: string;
  desvio_total: string;
  desvio_total_texto: string;
}

export interface TablaDeDiferencia {
  titulo: string;
  total_antes: string;
  total_antes_texto: string;
  total_despues: string;
  total_despues_texto: string;
  diferencia: string;
  diferencia_texto: string;
  desvio_cantidad: string;
  desvio_cantidad_texto: string;
  desvio_precio: string;
  desvio_precio_texto: string;
  partidas: PartidaDiferente[];
}

export interface ReauditoriaRevision {
  termino: boolean;
  avisos: string[];
  total_recalculado: string | null;
  total_recalculado_texto: string | null;
  reglas: string | null;
  precios_coinciden: boolean;
  mensaje_precios: string | null;
  diferencias: DiferenciaDePrecio[];
  hallazgos: LoteDeHallazgos[];
}

export interface ListaDelCaso {
  id: number;
  nombre: string;
}

export interface ContraLista {
  lista_id: number;
  diferencia: TablaDeDiferencia;
  no_contrastables: string | null;
}

export interface DictamenAnterior {
  resultado: string;
  usuario: string;
  fecha: string;
  estado_verificacion: string;
  texto: string;
}

export interface Revision {
  sha256: string;
  estado: string;
  motivo: string;
  color: string;
  banner: string;
  legible: boolean;
  banner_version: string | null;
  ayuda_registro: string | null;
  avisos: string[];
  retroactiva: string | null;
  aviso_armo: string | null;
  reauditoria: ReauditoriaRevision | null;
  entrega_anterior: TablaDeDiferencia | null;
  sin_entrega_anterior: string | null;
  listas: ListaDelCaso[];
  sin_listas: string | null;
  contra_lista: ContraLista | null;
  cambios_titulo: string;
  cambios: Record<string, string>[];
  dictamenes: DictamenAnterior[];
  resultados: string[];
  // Un paquete que no quedo registrado (alterado sin cadena) no admite dictamen: la API dice por que.
  admite_dictamen: boolean;
  sin_dictamen: string | null;
  nota_excel: string;
}

export interface DictamenGuardado {
  mensaje: string;
  dictamenes: DictamenAnterior[];
}

export interface ExcelExterno {
  aviso: string;
  total: string;
  total_texto: string;
  hallazgos: HallazgoRevision[];
}
