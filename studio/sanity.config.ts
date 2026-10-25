import { defineConfig } from 'sanity';
import { structureTool } from 'sanity/structure';
import { schemaTypes } from './schemaTypes';

export default defineConfig({
  name: 'cualquiera',
  title: 'cualquiera',
  projectId: 'n6mrjy1q',
  dataset: 'production',
  plugins: [structureTool()],
  schema: { types: schemaTypes },
});
