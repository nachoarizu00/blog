import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

export const SECCIONES = [
  'Política',
  'Derecho',
  'Arte',
  'Cine',
  'Literatura',
  'Música',
  'Filosofía',
  'Cualquier cosa',
] as const;

const articulos = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articulos' }),
  schema: z.object({
    title: z.string(),
    // bajada: se muestra bajo el título y como fragmento en la portada
    dek: z.string(),
    autor: z.string(),
    fecha: z.coerce.date(),
    seccion: z.enum(SECCIONES),
    // frase que se cita en grande en la portada
    pull: z.string().optional(),
    // palabra(s) del título que se intervienen con un trazo
    enfasis: z.string().optional(),
    // anotación a mano alzada que acompaña la pieza en la portada
    nota: z.string().optional(),
  }),
});

export const collections = { articulos };
