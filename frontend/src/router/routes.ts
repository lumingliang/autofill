import type { RouteRecordRaw } from 'vue-router'
import { markRaw } from 'vue'
import Login from '@/views/login/index.vue'
import Layout from '@/layout/index.vue'

export const WHITE_LIST = ['/login', '/404', '/403']

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/workbench',
    meta: { hidden: true },
  },
  {
    path: '/workbench',
    name: '工作台',
    component: markRaw(Layout),
    meta: { title: '工作台', icon: 'icon-park-outline:workbench', order: 1 },
    children: [
      {
        path: '',
        name: '工作台Default',
        component: () => import('@/views/workbench/index.vue'),
        meta: { title: '工作台', icon: 'icon-park-outline:workbench', affix: true },
      },
    ],
  },
  {
    path: '/profile',
    name: '个人中心',
    component: markRaw(Layout),
    meta: { title: '个人中心', hidden: true },
    children: [
      {
        path: '',
        name: '个人中心Default',
        component: () => import('@/views/profile/index.vue'),
        meta: { title: '个人中心', hidden: true },
      },
    ],
  },
  {
    path: '/login',
    name: 'Login',
    component: markRaw(Login),
    meta: { title: '登录', hidden: true },
  },
  {
    path: '/404',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '页面未找到', hidden: true },
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/views/error/403.vue'),
    meta: { title: '无权限', hidden: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
    meta: { hidden: true },
  },
]
