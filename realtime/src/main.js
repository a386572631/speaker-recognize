import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import App from './App.vue'

import 'ant-design-vue/dist/reset.css'
import './assets/styles/variables.css'
import './assets/styles/main.css'

const app = createApp(App)
app.use(Antd)
app.mount('#app')