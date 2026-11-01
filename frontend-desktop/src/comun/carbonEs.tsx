// Componentes de Carbon con sus textos por defecto en español (hallazgo 14 del recorrido del 01-11-2026).
// Carbon trae en inglés los textos que no se le pasan: «Scroll left/right» de las pestañas, «Clear search input» del
// buscador, «close notification» y «error icon» de los avisos, «loading» de la carga, «Show password», la paginación y
// «Click to sort rows by…» de las cabeceras ordenables. Aquí se fijan una sola vez; quien usa el componente puede pisar
// cualquiera con su propio prop. La regla `no-restricted-imports` de eslint.config.js obliga a importarlos de aquí.
import {
  InlineLoading as CarbonInlineLoading,
  InlineNotification as CarbonInlineNotification,
  Pagination as CarbonPagination,
  PasswordInput as CarbonPasswordInput,
  Search as CarbonSearch,
  TableHeader as CarbonTableHeader,
  TabList as CarbonTabList,
} from "@carbon/react";
import { forwardRef } from "react";
import type { ComponentProps, ComponentPropsWithoutRef, ElementRef, ReactNode } from "react";

// --- Pestañas ------------------------------------------------------------------------------------------------------

export const DESPLAZAR_IZQUIERDA = "Desplazar las pestañas a la izquierda";
export const DESPLAZAR_DERECHA = "Desplazar las pestañas a la derecha";

export function TabList({ leftOverflowButtonProps, rightOverflowButtonProps, ...props }: ComponentProps<typeof CarbonTabList>) {
  return (
    <CarbonTabList
      {...props}
      leftOverflowButtonProps={{
        ...leftOverflowButtonProps,
        "aria-label": leftOverflowButtonProps?.["aria-label"] ?? DESPLAZAR_IZQUIERDA,
      }}
      rightOverflowButtonProps={{
        ...rightOverflowButtonProps,
        "aria-label": rightOverflowButtonProps?.["aria-label"] ?? DESPLAZAR_DERECHA,
      }}
    />
  );
}

// --- Buscador ------------------------------------------------------------------------------------------------------

export const BORRAR_BUSQUEDA = "Borrar la búsqueda";

export const Search = forwardRef<ElementRef<typeof CarbonSearch>, ComponentPropsWithoutRef<typeof CarbonSearch>>(
  function Search({ closeButtonLabelText = BORRAR_BUSQUEDA, placeholder = "Buscar", ...props }, ref) {
    return <CarbonSearch ref={ref} closeButtonLabelText={closeButtonLabelText} placeholder={placeholder} {...props} />;
  },
);

// --- Avisos --------------------------------------------------------------------------------------------------------

export const CERRAR_AVISO = "Cerrar el aviso";

// El nombre del ícono de estado de cada clase de aviso (Carbon pone «error icon», «warning icon»…).
export const ICONO_DEL_AVISO: Record<string, string> = {
  error: "Error",
  info: "Información",
  "info-square": "Información",
  success: "Hecho",
  warning: "Advertencia",
  "warning-alt": "Advertencia",
};

export function InlineNotification({
  kind = "error",
  statusIconDescription,
  "aria-label": ariaLabel = CERRAR_AVISO,
  ...props
}: ComponentProps<typeof CarbonInlineNotification>) {
  return (
    <CarbonInlineNotification
      {...props}
      kind={kind}
      aria-label={ariaLabel}
      statusIconDescription={statusIconDescription ?? ICONO_DEL_AVISO[kind] ?? "Aviso"}
    />
  );
}

// --- Carga en línea ------------------------------------------------------------------------------------------------

const ICONO_DE_CARGA: Record<string, string> = { active: "Cargando", finished: "Terminado", error: "Error" };

export function InlineLoading({ status = "active", iconDescription, ...props }: ComponentProps<typeof CarbonInlineLoading>) {
  return <CarbonInlineLoading {...props} status={status} iconDescription={iconDescription ?? ICONO_DE_CARGA[status]} />;
}

// --- Contraseña ----------------------------------------------------------------------------------------------------

export const MOSTRAR_CONTRASENA = "Mostrar la contraseña";
export const OCULTAR_CONTRASENA = "Ocultar la contraseña";

export const PasswordInput = forwardRef<ElementRef<typeof CarbonPasswordInput>, ComponentPropsWithoutRef<typeof CarbonPasswordInput>>(
  function PasswordInput({ showPasswordLabel = MOSTRAR_CONTRASENA, hidePasswordLabel = OCULTAR_CONTRASENA, ...props }, ref) {
    return <CarbonPasswordInput ref={ref} showPasswordLabel={showPasswordLabel} hidePasswordLabel={hidePasswordLabel} {...props} />;
  },
);

// --- Paginación ----------------------------------------------------------------------------------------------------

const paginas = (total: number) => `${total} ${total === 1 ? "página" : "páginas"}`;

export const Pagination = forwardRef<ElementRef<typeof CarbonPagination>, ComponentPropsWithoutRef<typeof CarbonPagination>>(
  function Pagination(props, ref) {
    return (
      <CarbonPagination
        ref={ref}
        backwardText="Página anterior"
        forwardText="Página siguiente"
        itemsPerPageText="Filas por página"
        itemRangeText={(min: number, max: number, total: number) => `${min}–${max} de ${total}`}
        itemText={(min: number, max: number) => `${min}–${max}`}
        pageRangeText={(_actual: number, total: number) => `de ${paginas(total)}`}
        pageText={(pagina: number) => `página ${pagina}`}
        pageSelectLabelText={(total: number) => `Página, de ${paginas(total)}`}
        {...props}
      />
    );
  },
);

// --- Cabeceras ordenables ------------------------------------------------------------------------------------------

interface ArgsDeOrden {
  header?: ReactNode;
  sortDirection?: string;
  isSortHeader?: boolean;
}

// La descripción accesible del botón de orden de una cabecera (Carbon: «Click to sort rows by … header in …»).
export function textoDeOrden(id: string, args?: ArgsDeOrden): string {
  if (id !== "carbon.table.header.icon.description" || !args) return "";
  const columna = typeof args.header === "string" ? `«${args.header}»` : "esta columna";
  if (args.isSortHeader && args.sortDirection === "ASC") return `Pulse para ordenar las filas por ${columna} de mayor a menor`;
  if (args.isSortHeader && args.sortDirection === "DESC") return `Pulse para quitar el orden por ${columna}`;
  return `Pulse para ordenar las filas por ${columna} de menor a mayor`;
}

export const TableHeader = forwardRef<ElementRef<typeof CarbonTableHeader>, ComponentPropsWithoutRef<typeof CarbonTableHeader>>(
  function TableHeader({ translateWithId = textoDeOrden, ...props }, ref) {
    return <CarbonTableHeader ref={ref} translateWithId={translateWithId} {...props} />;
  },
);
