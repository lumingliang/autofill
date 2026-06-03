import request from '@/utils/request'

// 批量测试任务接口

export interface BatchTestTask {
  id: number
  task_name: string
  version_no: number
  dify_agent_id: number
  dify_agent_name: string
  file_name: string
  file_size: number
  row_count: number
  collection_name: string
  status: number
  success_count: number
  fail_count: number
  remark: string
  created_by: number
  created_at: string
  updated_at: string
}

export interface BatchTestTaskQuery {
  page?: number
  page_size?: number
  keyword?: string
}

export interface BatchTestResultQuery {
  page?: number
  page_size?: number
  status?: number
}

export interface BatchTestImportResponse {
  task_id: number
  task_name: string
  version_no: number
  row_count: number
  status: number
  collection_name: string
}

export interface BatchTestFilePreview {
  file_name: string
  file_size: number
  row_count: number
  headers: string[]
  sample_data: Record<string, string>[]
  has_query_column: boolean
}

// 预览文件
export function previewBatchTestFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/batch-test/tasks/preview',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 导入文件创建任务
export function importBatchTestFile(
  file: File,
  difyAgentId: number,
  taskName?: string,
  remark?: string
) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('dify_agent_id', difyAgentId.toString())
  if (taskName) formData.append('task_name', taskName)
  if (remark) formData.append('remark', remark)

  return request({
    url: '/batch-test/tasks/import',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 获取任务列表
export function getBatchTestTaskList(params: BatchTestTaskQuery) {
  return request({
    url: '/batch-test/tasks/list',
    method: 'get',
    params
  })
}

// 获取任务详情
export function getBatchTestTaskDetail(taskId: number) {
  return request({
    url: `/batch-test/tasks/${taskId}`,
    method: 'get'
  })
}

// 停止任务
export function stopBatchTestTask(taskId: number) {
  return request({
    url: `/batch-test/tasks/${taskId}/stop`,
    method: 'post'
  })
}

// 删除任务
export function deleteBatchTestTask(taskId: number) {
  return request({
    url: `/batch-test/tasks/${taskId}`,
    method: 'delete'
  })
}

// 重新执行任务
export function retryBatchTestTask(taskId: number) {
  return request({
    url: `/batch-test/tasks/${taskId}/retry`,
    method: 'post'
  })
}

// 获取测试结果列表
export function getBatchTestResults(taskId: number, params: BatchTestResultQuery) {
  return request({
    url: `/batch-test/tasks/${taskId}/results`,
    method: 'get',
    params
  })
}

// 导出测试结果
export function exportBatchTestResults(taskId: number) {
  return request({
    url: `/batch-test/tasks/${taskId}/export`,
    method: 'get',
    responseType: 'blob'
  })
}

// 获取 Dify Agent 下拉列表
export function getDifyAgentSelect() {
  return request({
    url: '/autofill/dify-agent/select',
    method: 'get'
  })
}
