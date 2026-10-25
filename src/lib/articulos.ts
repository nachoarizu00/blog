// Única capa de acceso a los textos. Cuando llegue Sanity, solo cambia este archivo.
import { getCollection, type CollectionEntry } from 'astro:content';

export type Articulo = CollectionEntry<'articulos'>;

export async function todosLosArticulos(): Promise<Articulo[]> {
  const todos = await getCollection('articulos');
  return todos.sort((a, b) => b.data.fecha.getTime() - a.data.fecha.getTime());
}

export function minutosDeLectura(articulo: Articulo): number {
  const palabras = (articulo.body ?? '').split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(palabras / 210));
}

export function fechaLarga(fecha: Date): string {
  return fecha.toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
}

export function fechaCorta(fecha: Date): string {
  return fecha.toLocaleDateString('es-AR', { day: '2-digit', month: 'short', timeZone: 'UTC' }).replace('.', '');
}

// Parte un título alrededor de la palabra intervenida.
export function partirTitulo(titulo: string, enfasis?: string): [string, string, string] {
  const i = enfasis ? titulo.indexOf(enfasis) : -1;
  if (!enfasis || i < 0) return [titulo, '', ''];
  return [titulo.slice(0, i), enfasis, titulo.slice(i + enfasis.length)];
}

export const rutaArticulo = (a: Articulo) => `/articulo/${a.id}/`;
