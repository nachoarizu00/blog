// Convierte los textos de ejemplo (../src/content/articulos/*.md) a un archivo
// de importación para Sanity (semilla.ndjson). Uso: npm run semilla && npm run importar
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const aca = dirname(fileURLToPath(import.meta.url));
const carpeta = join(aca, '..', '..', 'src', 'content', 'articulos');
let n = 0;
const clave = () => `k${(n++).toString(36)}`;

function frontmatter(texto) {
  const [, fm, cuerpo] = texto.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  const datos = {};
  for (const linea of fm.split('\n')) {
    const m = linea.match(/^(\w+):\s*(.*)$/);
    if (!m) continue;
    datos[m[1]] = m[2].replace(/^"(.*)"$/, '$1');
  }
  return { datos, cuerpo };
}

// Inline: **negrita**, *cursiva*, <mark>resaltado</mark>
function inline(texto) {
  const hijos = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|<mark>[\s\S]*?<\/mark>)/g;
  let ultimo = 0;
  const empujar = (text, marks = []) => text && hijos.push({ _type: 'span', _key: clave(), text, marks });
  for (const m of texto.matchAll(re)) {
    empujar(texto.slice(ultimo, m.index));
    const t = m[0];
    if (t.startsWith('**')) empujar(t.slice(2, -2), ['strong']);
    else if (t.startsWith('<mark>')) empujar(t.slice(6, -7), ['resaltado']);
    else empujar(t.slice(1, -1), ['em']);
    ultimo = m.index + t.length;
  }
  empujar(texto.slice(ultimo));
  return hijos.length ? hijos : [{ _type: 'span', _key: clave(), text: '', marks: [] }];
}

function bloques(md) {
  const salida = [];
  for (const trozo of md.trim().split(/\n{2,}/)) {
    const t = trozo.trim();
    if (!t) continue;
    if (t === '---') salida.push({ _type: 'separador', _key: clave(), ok: true });
    else if (t.startsWith('## ')) salida.push({ _type: 'block', _key: clave(), style: 'h2', markDefs: [], children: inline(t.slice(3)) });
    else if (t.startsWith('> ')) salida.push({ _type: 'block', _key: clave(), style: 'blockquote', markDefs: [], children: inline(t.replace(/^> ?/gm, '').replace(/\n/g, ' ')) });
    else salida.push({ _type: 'block', _key: clave(), style: 'normal', markDefs: [], children: inline(t.replace(/\n/g, ' ')) });
  }
  return salida;
}

const lineas = readdirSync(carpeta)
  .filter((f) => f.endsWith('.md'))
  .map((f) => {
    const { datos, cuerpo } = frontmatter(readFileSync(join(carpeta, f), 'utf8'));
    const slug = f.replace(/\.md$/, '');
    return JSON.stringify({
      _id: `articulo-${slug}`,
      _type: 'articulo',
      title: datos.title,
      slug: { _type: 'slug', current: slug },
      dek: datos.dek,
      autor: datos.autor,
      fecha: datos.fecha,
      seccion: datos.seccion,
      ...(datos.pull && { pull: datos.pull }),
      ...(datos.enfasis && { enfasis: datos.enfasis }),
      ...(datos.nota && { nota: datos.nota }),
      cuerpo: bloques(cuerpo),
    });
  });

writeFileSync(join(aca, '..', 'semilla.ndjson'), lineas.join('\n') + '\n');
console.log(`semilla.ndjson: ${lineas.length} artículos`);
