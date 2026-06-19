import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Test-Agent V2',
  description: 'AI-Native Testing Framework',
  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'API', link: '/api/overview' },
      { text: 'Plugins', link: '/plugins/overview' }
    ],
    sidebar: {
      '/guide/': [
        { text: 'Getting Started', link: '/guide/getting-started' },
        { text: 'Architecture', link: '/guide/architecture' }
      ],
      '/api/': [
        { text: 'Overview', link: '/api/overview' }
      ],
      '/plugins/': [
        { text: 'Overview', link: '/plugins/overview' }
      ]
    }
  }
})
