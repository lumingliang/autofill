import request from '@/utils/request'

export interface SystemPrompt {
    id: string
    name: string
    tenant_id: number
    content: string
    description: string
    is_default: boolean
    is_active: boolean
    category: string
    created_at: string
    updated_at: string
}

export interface SystemPromptQuery {
    page?: number
    page_size?: number
    tenant_id?: number
    keyword?: string
    category?: string
    is_default?: boolean
    is_active?: boolean
}

export interface SystemPromptCreate {
    tenant_id?: number
    name: string
    content: string
    description?: string
    category: string
    is_default?: boolean
    is_active?: boolean
}

export interface SystemPromptUpdate {
    name: string
    content: string
    description?: string
    category: string
    is_default?: boolean
    is_active?: boolean
}

// 获取系统提示词列表
export function getSystemPromptList(params: SystemPromptQuery) {
    return request({
        url: '/api/v1/autofill/system_prompts',
        method: 'get',
        params
    })
}

// 获取系统提示词详情
export function getSystemPromptDetail(id: string) {
    return request({
        url: `/api/v1/autofill/system_prompts/${id}`,
        method: 'get'
    })
}

// 创建系统提示词
export function createSystemPrompt(data: SystemPromptCreate) {
    return request({
        url: '/api/v1/autofill/system_prompts',
        method: 'post',
        data
    })
}

// 更新系统提示词
export function updateSystemPrompt(id: string, data: SystemPromptUpdate) {
    return request({
        url: `/api/v1/autofill/system_prompts/${id}`,
        method: 'post',
        data
    })
}

// 删除系统提示词
export function deleteSystemPrompt(id: string) {
    return request({
        url: `/api/v1/autofill/system_prompts/${id}`,
        method: 'delete'
    })
}
