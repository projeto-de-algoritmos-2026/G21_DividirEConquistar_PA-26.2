import { api } from "./core.js";

let pending = null;

/** Catálogo de algoritmos, cenários e limites (carregado uma vez). */
export function getCatalog() {
  if (!pending) {
    pending = api("/api/lab/catalog").catch((error) => {
      pending = null;
      throw error;
    });
  }
  return pending;
}

export function algorithmById(catalog, id) {
  return catalog.algorithms.find((algorithm) => algorithm.id === id);
}
