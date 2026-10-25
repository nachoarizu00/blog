import { defineArrayMember, defineField, defineType } from 'sanity';

// Mismas secciones que src/content.config.ts
const SECCIONES = ['Política', 'Derecho', 'Arte', 'Cine', 'Literatura', 'Música', 'Filosofía', 'Cualquier cosa'];

export const articulo = defineType({
  name: 'articulo',
  title: 'Artículo',
  type: 'document',
  fields: [
    defineField({ name: 'title', title: 'Título', type: 'string', validation: (r) => r.required() }),
    defineField({
      name: 'slug',
      title: 'Dirección (slug)',
      type: 'slug',
      options: { source: 'title', maxLength: 80 },
      validation: (r) => r.required(),
    }),
    defineField({ name: 'dek', title: 'Bajada', type: 'text', rows: 3, validation: (r) => r.required() }),
    defineField({ name: 'autor', title: 'Autor/a', type: 'string', validation: (r) => r.required() }),
    defineField({ name: 'fecha', title: 'Fecha de publicación', type: 'date', validation: (r) => r.required() }),
    defineField({
      name: 'seccion',
      title: 'Sección',
      type: 'string',
      options: { list: SECCIONES, layout: 'radio' },
      validation: (r) => r.required(),
    }),
    defineField({
      name: 'pull',
      title: 'Frase destacada (portada)',
      type: 'string',
      description: 'Una frase del texto que se cita en grande en la portada. Opcional.',
    }),
    defineField({
      name: 'enfasis',
      title: 'Palabra a intervenir en el título',
      type: 'string',
      description: 'Una palabra o frase del título que lleva subrayado, círculo o resaltador. Debe estar escrita igual que en el título. Opcional.',
    }),
    defineField({
      name: 'cuerpo',
      title: 'Texto',
      type: 'array',
      of: [
        defineArrayMember({
          type: 'block',
          styles: [
            { title: 'Párrafo', value: 'normal' },
            { title: 'Subtítulo', value: 'h2' },
            { title: 'Cita destacada', value: 'blockquote' },
          ],
          lists: [],
          marks: {
            decorators: [
              { title: 'Cursiva', value: 'em' },
              { title: 'Negrita', value: 'strong' },
              { title: 'Resaltador', value: 'resaltado' },
            ],
            annotations: [
              {
                name: 'link',
                type: 'object',
                title: 'Enlace',
                fields: [{ name: 'href', type: 'url', title: 'URL' }],
              },
            ],
          },
        }),
        defineArrayMember({ name: 'separador', title: 'Separador (* * *)', type: 'object', fields: [{ name: 'ok', type: 'boolean', hidden: true }] }),
      ],
      validation: (r) => r.required(),
    }),
  ],
  orderings: [{ title: 'Fecha, más reciente primero', name: 'fechaDesc', by: [{ field: 'fecha', direction: 'desc' }] }],
  preview: { select: { title: 'title', subtitle: 'autor' } },
});
