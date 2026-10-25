// Genera src/data/saludo.json: el saludo como trazos de pluma, en orden de escritura.
// Tipografía de trazo único "EMS Felix" (Sheldon B. Michaels, SIL Open Font License),
// incluida en el paquete hersheytext. Uso: node tools/escribir.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const aca = dirname(fileURLToPath(import.meta.url));
const TEXTO = 'bueno, se ve que estás en';
const DURACION_TOTAL_MS = 2700;   // tiempo de escritura (sin contar pausas)
const PAUSA_LETRA_MS = 20;
const PAUSA_PALABRA_MS = 120;

const svg = readFileSync(join(aca, '..', 'node_modules', 'hersheytext', 'svg_fonts', 'EMSFelix.svg'), 'utf8');
const glifos = {};
for (const m of svg.matchAll(/<glyph\s+unicode="([^"]*)"[^>]*?horiz-adv-x="([\d.]+)"(?:\s+d="([^"]*)")?/g)) {
  const u = m[1].replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)));
  glifos[u] = { adv: +m[2], d: m[3] || '' };
}

let x = 0;
const trazos = [];
[...TEXTO].forEach((ch, i) => {
  const g = glifos[ch] ?? glifos[' '];
  for (const t of g.d.match(/M[^M]*/g) ?? []) {
    const nums = t.replace(/[ML]/g, ' ').trim().split(/\s+/).map(Number);
    if (/[^ML\d\s.\-]/.test(t)) throw new Error(`comando no previsto en "${ch}": ${t}`);
    const pts = [];
    for (let k = 0; k < nums.length; k += 2) pts.push([nums[k] + x, nums[k + 1]]);
    let largo = 0;
    for (let k = 1; k < pts.length; k++) largo += Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]);
    trazos.push({
      d: 'M' + pts.map(([a, b]) => `${+a.toFixed(1)} ${+b.toFixed(1)}`).join(' L'),
      largo,
      pausa: ch === ' ' ? 0 : 0,
      finDePalabra: TEXTO[i + 1] === ' ' || i === TEXTO.length - 1,
    });
  }
  x += g.adv;
});

const total = trazos.reduce((s, t) => s + t.largo, 0);
const velocidad = total / DURACION_TOTAL_MS;   // unidades por ms
let t0 = 0;
for (const t of trazos) {
  t.inicio = Math.round(t0);
  t.dur = Math.max(60, Math.round(t.largo / velocidad));
  t0 += t.dur + (t.finDePalabra ? PAUSA_PALABRA_MS : PAUSA_LETRA_MS);
  delete t.pausa; delete t.finDePalabra; t.largo = Math.round(t.largo);
}

mkdirSync(join(aca, '..', 'src', 'data'), { recursive: true });
writeFileSync(join(aca, '..', 'src', 'data', 'saludo.json'), JSON.stringify({ texto: TEXTO, ancho: Math.round(x), duracion: Math.round(t0), trazos }, null, 1));
console.log(`${trazos.length} trazos, ${Math.round(x)} de ancho, ${(t0 / 1000).toFixed(1)} s`);
