import router from '@/router'
import axios from 'axios'
import { getToken, removeToken } from './auth'

const request = axios.create({
    baseURL: import.meta.env.VITE_BASE_API,
    timeout: 600000,
})

request.interceptors.request.use(
    (config) => {
        const token = getToken()
        if (token) {
            config.headers.token = token
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

request.interceptors.response.use(
    (response) => {
        const { data, status, statusText } = response
        if (data?.code !== 200) {
            const code = data?.code ?? status
            const msg = resolveErrorMessage(code, data?.msg ?? statusText)
            window.$message?.error(msg)
            return Promise.reject({ code, message: msg, error: data || response })
        }
        return data
    },
    (error) => {
        if (!error || !error.response) {
            const msg = resolveErrorMessage(error?.code, error.message)
            window.$message?.error(msg)
            return Promise.reject({ message: msg, error })
        }
        const { data, status } = error.response
        if (data?.code === 401) {
            removeToken()
            router.push('/login')
        }
        const code = data?.code ?? status
        const msg = resolveErrorMessage(code, data?.msg ?? error.message)
        window.$message?.error(msg)
        return Promise.reject({ code, message: msg, error: error.response?.data || error.response })
    }
)

function resolveErrorMessage(code: number | string, message?: string): string {
    const map: Record<string, string> = {
        '400': '请求参数错误',
        '401': '登录已过期',
        '403': '没有权限',
        '404': '资源或接口不存在',
        '500': '服务器异常',
    }
    return message || map[String(code)] || `【${code}】: 未知异常!`
}

export default request
