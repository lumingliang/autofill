/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_BASE_URL: string
  readonly VITE_APP_API_URL: string
  // 更多环境变量...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
  readonly glob: (pattern: string) => Record<string, () => Promise<any>>
  readonly globEager: (pattern: string) => Record<string, any>
}

// 声明虚拟模块
declare module 'uno.css'
declare module '*.less'
