import { defineConfig } from 'sanity';
import { structureTool } from 'sanity/structure';
import { schemaTypes } from './src/sanity';

// El editor vive dentro del sitio, en /studio (ver astro.config.mjs).
export default defineConfig({
  name: 'cualquiera',
  title: 'cualquiera',
  projectId: 'n6mrjy1q',
  dataset: 'production',
  plugins: [structureTool()],
  schema: { types: schemaTypes },
});
