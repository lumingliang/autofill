import router from '@/router'
import axios from 'axios'
import { getToken, removeToken } from './auth'

const request = axios.create({
    baseURL: import.meta.env.VITE_BASE_API,
    timeout: 600000,
    paramsSerializer: (params) => {
        // 自定义参数序列化，将数组格式化为重复的key（FastAPI兼容格式）
        const parts: string[] = []
        Object.entries(params).forEach(([key, value]) => {
            if (value === null || value === undefined) {
                return
            }
            if (Array.isArray(value)) {
                value.forEach((v) => {
                    if (v !== null && v !== undefined) {
                        parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(v)}`)
                    }
                })
            } else {
                parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
            }
        })
        return parts.join('&')
    },
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
        const { data, status, statusText, config } = response
        // 如果是 blob 响应类型，直接返回 response，让调用方处理
        if (config.responseType === 'blob') {
            return response
        }
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
