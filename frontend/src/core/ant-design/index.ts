import { message, Modal } from 'ant-design-vue'
import type { App } from 'vue'

export function setupAntDesign(app: App) {
    message.config({
        duration: 2,
        maxCount: 1,
    })

    // 挂载到全局
    window.$message = message
    window.$modal = Modal
}

declare global {
    interface Window {
        $message: typeof message
        $modal: typeof Modal
    }
}
