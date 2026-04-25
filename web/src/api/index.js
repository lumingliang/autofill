import { request } from '@/utils'

export default {
  // 登录相关
  login: (data) => request.post('/base/access_token', data, { noNeedToken: true }),
  selectTenant: (data) => request.post('/base/select_tenant', data),
  getUserInfo: () => request.get('/base/userinfo'),
  getUserMenu: () => request.get('/base/usermenu'),
  getUserApi: () => request.get('/base/userapi'),
  
  // profile
  updatePassword: (data = {}) => request.post('/base/update_password', data),
  
  // users
  getUserList: (params = {}) => request.get('/user/list', { params }),
  getUserById: (params = {}) => request.get('/user/get', { params }),
  createUser: (data = {}) => request.post('/user/create', data),
  updateUser: (data = {}) => request.post('/user/update', data),
  deleteUser: (params = {}) => request.delete(`/user/delete`, { params }),
  resetPassword: (data = {}) => request.post(`/user/reset_password`, data),
  getMyTenants: () => request.get('/user/my_tenants'),
  selectUserTenant: (data = {}) => request.post('/user/select_tenant', data),
  getTenantRoles: (params = {}) => request.get('/user/tenant_roles', { params }),
  
  // role
  getRoleList: (params = {}) => request.get('/role/list', { params }),
  createRole: (data = {}) => request.post('/role/create', data),
  updateRole: (data = {}) => request.post('/role/update', data),
  deleteRole: (params = {}) => request.delete('/role/delete', { params }),
  updateRoleAuthorized: (data = {}) => request.post('/role/authorized', data),
  getRoleAuthorized: (params = {}) => request.get('/role/authorized', { params }),
  
  // menus
  getMenus: (params = {}) => request.get('/menu/list', { params }),
  createMenu: (data = {}) => request.post('/menu/create', data),
  updateMenu: (data = {}) => request.post('/menu/update', data),
  deleteMenu: (params = {}) => request.delete('/menu/delete', { params }),
  
  // apis
  getApis: (params = {}) => request.get('/api/list', { params }),
  createApi: (data = {}) => request.post('/api/create', data),
  updateApi: (data = {}) => request.post('/api/update', data),
  deleteApi: (params = {}) => request.delete('/api/delete', { params }),
  refreshApi: (data = {}) => request.post('/api/refresh', data),
  
  // depts
  getDepts: (params = {}) => request.get('/dept/list', { params }),
  createDept: (data = {}) => request.post('/dept/create', data),
  updateDept: (data = {}) => request.post('/dept/update', data),
  deleteDept: (params = {}) => request.delete('/dept/delete', { params }),
  
  // tenants - 多租户
  getTenantList: (params = {}) => request.get('/tenant/list', { params }),
  getTenantById: (params = {}) => request.get('/tenant/get', { params }),
  createTenant: (data = {}) => request.post('/tenant/create', data),
  updateTenant: (data = {}) => request.post('/tenant/update', data),
  deleteTenant: (params = {}) => request.delete('/tenant/delete', { params }),
  getTenantSelect: () => request.get('/tenant/select'),
  getTenantUsers: (params = {}) => request.get('/tenant/users', { params }),
  addUserToTenant: (data = {}) => request.post('/tenant/add_user', data),
  removeUserFromTenant: (data = {}) => request.post('/tenant/remove_user', data),
  
  // auditlog
  getAuditLogList: (params = {}) => request.get('/auditlog/list', { params }),
}
