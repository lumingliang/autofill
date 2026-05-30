import request from '@/utils/request'
import axios from 'axios'

// 创建不带 baseURL 的请求实例（用于公开 API）
const publicRequest = axios.create({
  timeout: 600000,
})

export default {
  // 登录相关
  login: (data: any) => request.post('/base/access_token', data),
  selectTenant: (data: any) => request.post('/base/select_tenant', data),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  quickLogin: (data: any = {}) => request.post('/base/quick_login', data),

  // profile
  updatePassword: (data: any = {}) => request.post('/base/update_password', data),

  // users
  getUserList: (params: any = {}) => request.get('/user/list', { params }),
  getUserById: (params: any = {}) => request.get('/user/get', { params }),
  createUser: (data: any = {}) => request.post('/user/create', data),
  updateUser: (data: any = {}) => request.post('/user/update', data),
  deleteUser: (params: any = {}) => request.delete('/user/delete', { params }),
  resetPassword: (data: any = {}) => request.post('/user/reset_password', data),
  getMyTenants: () => request.get('/user/my_tenants'),
  selectUserTenant: (data: any = {}) => request.post('/user/select_tenant', data),
  getTenantRoles: (params: any = {}) => request.get('/user/tenant_roles', { params }),
  getUserTenantAssignedRoles: (params: any = {}) => request.get('/user/tenant_assigned_roles', { params }),
  updateUserTenantRoles: (data: any = {}) => request.post('/user/update_tenant_roles', data),

  // role
  getRoleList: (params: any = {}) => request.get('/role/list', { params }),
  createRole: (data: any = {}) => request.post('/role/create', data),
  updateRole: (data: any = {}) => request.post('/role/update', data),
  deleteRole: (params: any = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data: any = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params: any = {}) => request.get('/role/authorized', { params }),
  getRoleUsers: (params: any = {}) => request.get('/role/users', { params }),
  getRoleAvailableUsers: (params: any = {}) => request.get('/role/available_users', { params }),
  assignUsersToRole: (data: any = {}) => request.post('/role/assign_users', data),

  // menus
  getMenus: (params: any = {}) => request.get('/menu/list', { params }),
  createMenu: (data: any = {}) => request.post('/menu/create', data),
  updateMenu: (data: any = {}) => request.post('/menu/update', data),
  deleteMenu: (params: any = {}) => request.delete('/menu/delete', { params }),

  // apis
  getApis: (params: any = {}) => request.get('/api/list', { params }),
  createApi: (data: any = {}) => request.post('/api/create', data),
  updateApi: (data: any = {}) => request.post('/api/update', data),
  deleteApi: (params: any = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data: any = {}) => request.post('/api/refresh', data),

  // depts
  getDepts: (params: any = {}) => request.get('/dept/list', { params }),
  createDept: (data: any = {}) => request.post('/dept/create', data),
  updateDept: (data: any = {}) => request.post('/dept/update', data),
  deleteDept: (params: any = {}) => request.delete('/dept/delete', { params }),

  // tenants
  getTenantList: (params: any = {}) => request.get('/tenant/list', { params }),
  getTenantById: (params: any = {}) => request.get('/tenant/get', { params }),
  createTenant: (data: any = {}) => request.post('/tenant/create', data),
  updateTenant: (data: any = {}) => request.post('/tenant/update', data),
  deleteTenant: (params: any = {}) => request.delete('/tenant/delete', { params }),
  getTenantSelect: (params: any = {}) => request.get('/tenant/select', { params }),
  getTenantUsers: (params: any = {}) => request.get('/tenant/users', { params }),
  addUserToTenant: (data: any = {}) => request.post('/tenant/add_user', data),
  removeUserFromTenant: (data: any = {}) => request.post('/tenant/remove_user', data),
  batchAddUsersToTenant: (data: any = {}) => request.post('/tenant/batch_add_users', data),
  searchUsersForTenant: (params: any = {}) => request.get('/tenant/search_users', { params }),
  getTenantAssignedUsers: (params: any = {}) => request.get('/tenant/assigned_users', { params }),
  batchRemoveUsersFromTenant: (data: any = {}) => request.post('/tenant/batch_remove_users', data),

  // auditlog
  getAuditLogList: (params: any = {}) => request.get('/auditlog/list', { params }),

  // upload
  uploadAvatar: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/upload/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  uploadFile: (file: File, fileType = 'file') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('file_type', fileType)
    return request.post('/upload/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // autofill - 应用管理
  getAppList: (params: any = {}) => request.get('/autofill/app/list', { params }),
  getAppById: (params: any = {}) => request.get('/autofill/app/get', { params }),
  createApp: (data: any = {}) => request.post('/autofill/app/create', data),
  updateApp: (data: any = {}) => request.post('/autofill/app/update', data),
  deleteApp: (params: any = {}) => request.delete('/autofill/app/delete', { params }),
  getAppSelect: (params: any = {}) => request.get('/autofill/app/select', { params }),

  // autofill - 填单记录管理
  getRecordList: (params: any = {}) => request.get('/autofill/record/list', { params }),
  getRecordById: (params: any = {}) => request.get('/autofill/record/get', { params }),
  updateRecord: (data: any = {}) => request.post('/autofill/record/update', data),
  deleteRecord: (params: any = {}) => request.delete('/autofill/record/delete', { params }),

  // LLM 配置管理
  getLLMConfigList: (params: any = {}) => request.get('/ai/llm_config/list', { params }),
  getLLMConfigById: (params: any = {}) => request.get('/ai/llm_config/get', { params }),
  createLLMConfig: (data: any = {}) => request.post('/ai/llm_config/create', data),
  updateLLMConfig: (data: any = {}) => request.post('/ai/llm_config/update', data),
  deleteLLMConfig: (params: any = {}) => request.delete('/ai/llm_config/delete', { params }),
  getLLMProviders: () => request.get('/ai/llm_config/providers'),
  testLLMConfig: (data: any = {}) => request.post('/ai/llm_config/test', data),
  getLLMGatewayStatus: () => request.get('/ai/llm_config/gateway/status'),
  resetLLMMethods: (data: any = {}) => request.post('/ai/llm_config/reset_methods', data),
  getLLMMethods: (params: any = {}) => request.get('/ai/llm_config/methods', { params }),
  syncToGateway: (params: any = {}) => request.post('/ai/llm_config/sync_to_gateway', null, { params }),
  syncFromGateway: (params: any = {}) => request.post('/ai/llm_config/sync_from_gateway', null, { params }),
  getGatewayModels: () => request.get('/ai/llm_config/gateway/models'),

  // 规则管理
  getRuleList: (params: any = {}) => request.get('/autofill/rule/list', { params }),
  getRuleDetail: (params: any = {}) => request.get('/autofill/rule/get', { params }),
  createRule: (data: any = {}) => request.post('/autofill/rule/create', data),
  updateRule: (data: any = {}) => request.post('/autofill/rule/update', data),
  deleteRule: (params: any = {}) => request.delete('/autofill/rule/delete', { params }),
  saveRuleVersion: (data: any = {}) => request.post('/autofill/rule/save', data),
  getRuleVersions: (params: any = {}) => request.get('/autofill/rule/versions', { params }),
  getRuleVersionByNo: (params: any = {}) => request.get('/autofill/rule/version', { params }),
  rollbackRuleVersion: (data: any = {}) => request.post('/autofill/rule/rollback', data),
  importRuleCsv: (ruleId: number, file: File, currentMd5: string = '', tenantId?: number, allowAddNew: boolean = true) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('rule_id', ruleId.toString())
    formData.append('current_md5', currentMd5)
    formData.append('allow_add_new', allowAddNew.toString())
    const params: any = {}
    if (tenantId) params.tenant_id = tenantId
    return request.post('/autofill/rule/import', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  exportRuleCsv: (params: any = {}) => request.get('/autofill/rule/export', { params, responseType: 'blob' }),
  previewRuleCsv: (data: any = {}) => request.post('/autofill/rule/import/preview', data),

  // 系统提示词管理
  getSystemPromptList: (params: any = {}) => request.get('/autofill/system_prompts', { params }),
  getSystemPromptById: (params: any = {}) => request.get('/autofill/system_prompts/' + params.id),
  createSystemPrompt: (data: any = {}) => request.post('/autofill/system_prompts?tenant_id=' + (data.tenant_id || 0), data),
  updateSystemPrompt: (data: any = {}) => request.post('/autofill/system_prompts/' + data.id + '?tenant_id=' + (data.tenant_id || 0), data),
  deleteSystemPrompt: (params: any = {}) => request.delete('/autofill/system_prompts/' + params.id, { params }),
  getSystemPromptCategories: (params: any = {}) => request.get('/autofill/system_prompts/categories', { params }),

  // 规则执行引擎 (使用 API Key 认证，使用绝对路径)
  executeRule: (data: any = {}, apiKey: string) => publicRequest.post('/api/autofill/llm/rule/execute', data, {
    headers: { 'X-API-Key': apiKey }
  }),
  getRuleExecuteResult: (data: any = {}, apiKey: string) => publicRequest.post('/api/autofill/llm/rule/execute/result', data, {
    headers: { 'X-API-Key': apiKey }
  }),

  // 规则导入接口
  previewFileImport: (data: any = {}) => request.post('/autofill/rule/import/file/preview', data),
  getImportConfig: (params: any = {}) => request.get('/autofill/rule/import/config', { params }),
  saveImportConfig: (data: any = {}) => request.post('/autofill/rule/import/config', data),
  applyImport: (data: any = {}) => request.post('/autofill/rule/import/apply', data),

  // CURL导入接口
  previewCurlImport: (data: any = {}) => request.post('/autofill/rule/import/curl/preview', data),
  getCurlImportConfig: (params: any = {}) => request.get('/autofill/rule/import/curl/config', { params }),
  saveCurlImportConfig: (data: any = {}) => request.post('/autofill/rule/import/curl/config', data),
  applyCurlImport: (data: any = {}) => request.post('/autofill/rule/import/curl/apply', data),

  // 规则执行测试接口
  getRuleTestApps: () => request.get('/autofill/rule_test/apps'),
  getRuleTestRules: (params: any = {}) => request.get('/autofill/rule_test/rules', { params }),
  getRuleTestColumns: (params: any = {}) => request.get('/autofill/rule_test/rule_columns', { params }),
  executeRuleTest: (data: any = {}) => request.post('/autofill/rule_test/execute', data),
  exportRuleTestCurl: (data: any = {}) => request.post('/autofill/rule_test/export_curl', data),

}
