// Tipos de `patronesDeSilabeo.mjs` para `vite.config.ts` (tsconfig.node.json no admite JavaScript).
export declare const IDIOMAS_CONSERVADOS: ReadonlySet<string>;
export declare function esCargadorDePatrones(id: string): boolean;
export declare function podarPatrones(codigo: string, conservar?: ReadonlySet<string>): string;
