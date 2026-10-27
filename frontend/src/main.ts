import { createPinia } from 'pinia'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import '@/styles/theme.css'

import { registerAuthBridge } from '@/api/http'
import App from '@/App.vue'
import router from '@/router'
import { useUserStore } from '@/stores/user'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 令牌只在内存中流转：访问令牌由 store 持有，刷新令牌由服务端 httpOnly Cookie 管理
registerAuthBridge({
  getAccessToken: () => useUserStore().accessToken,
  refresh: () => useUserStore().refreshAccessToken(),
  onUnauthorized: () => {
    // 续期失败：清空登录态并回到登录页，同时保留原目标地址
    useUserStore().clearSession()
    if (router.currentRoute.value.name !== 'login') {
      router.push({
        name: 'login',
        query: { redirect: router.currentRoute.value.fullPath },
      })
    }
  },
})

app.mount('#app')
