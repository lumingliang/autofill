import request from '@/utils/request'

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
  getTenantSelect: () => request.get('/tenant/select'),
  getTenantUsers: (params: any = {}) => request.get('/tenant/users', { params }),
  addUserToTenant: (data: any = {}) => request.post('/tenant/add_user', data),
  removeUserFromTenant: (data: any = {}) => request.post('/tenant/remove_user', data),

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

  // autofill - 总结模板管理
  getTemplateList: (params: any = {}) => request.get('/autofill/template/list', { params }),
  getTemplateById: (params: any = {}) => request.get('/autofill/template/get', { params }),
  createTemplate: (data: any = {}) => request.post('/autofill/template/create', data),
  updateTemplate: (data: any = {}) => request.post('/autofill/template/update', data),
  deleteTemplate: (params: any = {}) => request.delete('/autofill/template/delete', { params }),
  importTemplateFromCsv: (file: File, appName: string, tenantId?: number) => {
    const formData = new FormData()
    formData.append('file', file)
    const params: any = { app_name: appName }
    if (tenantId) params.tenant_id = tenantId
    return request.post('/autofill/template/import', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  // autofill - 下拉选项管理
  getDropdownList: (params: any = {}) => request.get('/autofill/dropdown/list', { params }),
  getDropdownTree: (params: any = {}) => request.get('/autofill/dropdown/tree', { params }),
  getDropdownClasses: (params: any = {}) => request.get('/autofill/dropdown/classes', { params }),
  getDropdownById: (params: any = {}) => request.get('/autofill/dropdown/get', { params }),
  createDropdown: (data: any = {}) => request.post('/autofill/dropdown/create', data),
  updateDropdown: (data: any = {}) => request.post('/autofill/dropdown/update', data),
  deleteDropdown: (params: any = {}) => request.delete('/autofill/dropdown/delete', { params }),
  importDropdownFromCsv: (file: File, appName: string, tenantId?: number) => {
    const formData = new FormData()
    formData.append('file', file)
    const params: any = { app_name: appName }
    if (tenantId) params.tenant_id = tenantId
    return request.post('/autofill/dropdown/import', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  previewCsvStructure: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/autofill/dropdown/preview-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  importHierarchicalDropdownFromCsv: (
    file: File,
    appName: string,
    className: string = '事件类型',
    level1NameField: string,
    level1IdField: string,
    level1DescField: string,
    level2NameField: string,
    level2IdField: string,
    level2DescField: string,
    level3NameField: string,
    level3IdField: string,
    level3DescField: string,
    tenantId?: number
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    const params: any = {
      app_name: appName,
      class_name: className,
      level1_name_field: level1NameField,
      level1_id_field: level1IdField,
      level1_desc_field: level1DescField || '',
      level2_name_field: level2NameField,
      level2_id_field: level2IdField,
      level2_desc_field: level2DescField || '',
      level3_name_field: level3NameField,
      level3_id_field: level3IdField,
      level3_desc_field: level3DescField || '',
    }
    if (tenantId) params.tenant_id = tenantId
    return request.post('/autofill/dropdown/import-hierarchical', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

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

  // LLM 代理公开接口 (使用 API Key 认证)
  llmProxy: (data: any = {}, apiKey: string) => request.post('/api/llm/proxy', data, {
    headers: { 'Authorization': `Bearer ${apiKey}` }
  }),
  llmProxyHealth: (apiKey: string) => request.get('/api/llm/proxy/health', {
    headers: { 'Authorization': `Bearer ${apiKey}` }
  }),

  // autofill - 页面管理
  getPageList: (params: any = {}) => request.get('/autofill/page/list', { params }),
  getPageById: (params: any = {}) => request.get('/autofill/page/get', { params }),
  getPageDetail: (params: any = {}) => request.get('/autofill/page/detail', { params }),
  exportPageMd: (params: any = {}) => request.get('/autofill/page/export_md', { params }),
  createPage: (data: any = {}) => request.post('/autofill/page/create', data),
  updatePage: (data: any = {}) => request.post('/autofill/page/update', data),
  deletePage: (params: any = {}) => request.delete('/autofill/page/delete', { params }),
  getPageSelect: (params: any = {}) => request.get('/autofill/page/select', { params }),

  // autofill - 字段组管理
  getFieldGroupList: (params: any = {}) => request.get('/autofill/field_group/list', { params }),
  getFieldGroupById: (params: any = {}) => request.get('/autofill/field_group/get', { params }),
  getFieldGroupDetail: (params: any = {}) => request.get('/autofill/field_group/detail', { params }),
  getFieldGroupDetailByName: (params: any = {}) => request.get('/autofill/field_group/detail_by_name', { params }),
  exportFieldGroupMd: (params: any = {}) => request.get('/autofill/field_group/export_md', { params }),
  getFieldGroupByCode: (params: any = {}) => request.get('/autofill/field_group/get_by_code', { params }),
  createFieldGroup: (data: any = {}) => request.post('/autofill/field_group/create', data),
  updateFieldGroup: (data: any = {}) => request.post('/autofill/field_group/update', data),
  deleteFieldGroup: (params: any = {}) => request.delete('/autofill/field_group/delete', { params }),
  getFieldGroupSelect: (params: any = {}) => request.get('/autofill/field_group/select', { params }),

  // autofill - 字段管理
  getFieldSpecList: (params: any = {}) => request.get('/autofill/field_spec/list', { params }),
  getFieldSpecById: (params: any = {}) => request.get('/autofill/field_spec/get', { params }),
  getFieldSpecsByGroup: (params: any = {}) => request.get('/autofill/field_spec/by_group', { params }),
  createFieldSpec: (data: any = {}) => request.post('/autofill/field_spec/create', data),
  updateFieldSpec: (data: any = {}) => request.post('/autofill/field_spec/update', data),
  deleteFieldSpec: (params: any = {}) => request.delete('/autofill/field_spec/delete', { params }),
  exportFieldSpecs: (data: any = {}) => request.post('/autofill/field_spec/export', data),
  importFieldSpecs: (data: any = {}) => request.post('/autofill/field_spec/import', data, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  syncFieldSpecOptions: (data: any = {}) => request.post('/autofill/field_spec/sync_options', data),
  parseCurlCommand: (data: any = {}) => request.post('/autofill/field_spec/parse_curl', data),

  // 测试填单
  testFillChat: (data: any = {}) => request.post('/autofill/test-fill/chat', data),
  testFill: (data: any = {}) => request.post('/autofill/test-fill/fill', data),

}
