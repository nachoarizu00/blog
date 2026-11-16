// Única capa de acceso a los textos. Lee de Sanity; si todavía no hay artículos
// publicados (o Sanity no responde), usa los textos de ejemplo de src/content.
import { getCollection, type CollectionEntry } from 'astro:content';
import { createClient } from '@sanity/client';
import { toHTML } from '@portabletext/to-html';
import type { SECCIONES } from '../content.config';

export interface DatosArticulo {
  title: string;
  dek: string;
  autor: string;
  fecha: Date;
  seccion: (typeof SECCIONES)[number];
  pull?: string;
  enfasis?: string;
}

export interface Articulo {
  id: string;
  data: DatosArticulo;
  /** texto plano, para calcular el tiempo de lectura */
  texto: string;
  cuerpo: { tipo: 'html'; html: string } | { tipo: 'markdown'; entrada: CollectionEntry<'articulos'> };
}

const sanity = createClient({
  projectId: import.meta.env.SANITY_PROJECT_ID ?? 'n6mrjy1q',
  dataset: import.meta.env.SANITY_DATASET ?? 'production',
  apiVersion: '2025-01-01',
  useCdn: true,
});

const CONSULTA = `*[_type == "articulo" && defined(slug.current)] | order(fecha desc) {
  "id": slug.current, title, dek, autor, fecha, seccion, pull, enfasis,
  cuerpo[]{ ..., _type == "image" => { "url": asset->url, "dimensions": asset->metadata.dimensions } }
}`;

type Bloque = { _type: string; children?: { text?: string }[]; url?: string; alt?: string; epigrafe?: string; dimensions?: { width: number; height: number } };

const escapar = (t = '') => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function aTextoPlano(cuerpo: Bloque[]): string {
  return cuerpo.map((b) => (b.children ?? []).map((c) => c.text ?? '').join('')).join(' ');
}

function aHtml(cuerpo: Bloque[]): string {
  return toHTML(cuerpo as never, {
    components: {
      types: {
        separador: () => '<hr>',
        image: ({ value }) => {
          const v = value as Bloque;
          if (!v.url) return '';
          const w = v.dimensions?.width ?? 1600;
          const h = v.dimensions?.height ?? 1200;
          const base = `${v.url}?auto=format`;
          const srcset = [800, 1200, 1600, 2400].filter((x) => x <= w).map((x) => `${base}&w=${x} ${x}w`).join(', ') || `${base}&w=${w} ${w}w`;
          const pie = v.epigrafe ? `<figcaption>${escapar(v.epigrafe)}</figcaption>` : '';
          return `<figure><img src="${base}&w=1600" srcset="${srcset}" sizes="(min-width: 900px) 70vw, 100vw" width="${w}" height="${h}" alt="${escapar(v.alt)}" loading="lazy" decoding="async" />${pie}</figure>`;
        },
      },
      marks: { resaltado: ({ children }) => `<mark>${children}</mark>` },
    },
  });
}

async function desdeSanity(): Promise<Articulo[]> {
  const filas = await sanity.fetch<(DatosArticulo & { id: string; fecha: string; cuerpo: Bloque[] })[]>(CONSULTA);
  return filas.map(({ id, cuerpo, fecha, ...resto }) => ({
    id,
    data: { ...resto, fecha: new Date(`${fecha}T00:00:00Z`) },
    texto: aTextoPlano(cuerpo ?? []),
    cuerpo: { tipo: 'html', html: aHtml(cuerpo ?? []) },
  }));
}

async function desdeEjemplos(): Promise<Articulo[]> {
  const entradas = await getCollection('articulos');
  return entradas
    .map((entrada) => ({
      id: entrada.id,
      data: entrada.data,
      texto: entrada.body ?? '',
      cuerpo: { tipo: 'markdown', entrada } as const,
    }))
    .sort((a, b) => b.data.fecha.getTime() - a.data.fecha.getTime());
}

let enCache: Promise<Articulo[]> | undefined;

// Se resuelve una sola vez por compilación, no una vez por página.
export function todosLosArticulos(): Promise<Articulo[]> {
  return (enCache ??= cargar());
}

async function cargar(): Promise<Articulo[]> {
  try {
    const publicados = await desdeSanity();
    if (publicados.length) return publicados;
    console.warn('[cualquiera] Sanity no tiene artículos todavía: se usan los textos de ejemplo.');
  } catch (error) {
    console.warn('[cualquiera] No se pudo leer Sanity: se usan los textos de ejemplo.', error);
  }
  return desdeEjemplos();
}

export function minutosDeLectura(articulo: Articulo): number {
  const palabras = articulo.texto.split(/\s+/).filter(Boolean).length;
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
