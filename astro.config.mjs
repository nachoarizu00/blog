import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sanity from '@sanity/astro';

export default defineConfig({
  integrations: [
    sanity({
      projectId: 'n6mrjy1q',
      dataset: 'production',
      useCdn: true,
      apiVersion: '2025-01-01',
      studioBasePath: '/studio',
    }),
    react(),
  ],
});
