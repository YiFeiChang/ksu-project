import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
    base: '/service/ksu-project-pi/',
    plugins: [vue(), vueJsx(), vueDevTools()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    build: {
        outDir: '../dotnet/Pi.WebService/wwwroot',
        emptyOutDir: true,
    },
    server: {
        proxy: {
            // 這裡代表所有以 /api 開頭的請求都會被代理
            '/api': {
                target: 'http://10.0.2.3:5000', // 請替換為您的實際後端 API 伺服器網址與 port
                changeOrigin: true, // 允許跨網域
                secure: false, // 如果您的後端使用的是自簽憑證 (例如 .NET 的開發憑證) 請設為 false
            },
        },
    },
})
