import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'overview', component: () => import('@/views/OverviewView.vue'), meta: { title: '概览' } },
    { path: '/projects', name: 'projects', component: () => import('@/views/ProjectsView.vue'), meta: { title: '项目' } },
    { path: '/projects/:id', name: 'project-detail', component: () => import('@/views/ProjectDetailView.vue'), meta: { title: '项目详情' } },
    { path: '/sessions/:sessionId', name: 'session-detail', component: () => import('@/views/SessionDetailView.vue'), meta: { title: '会话时间轴' } },
    { path: '/prices', name: 'prices', component: () => import('@/views/PricesView.vue'), meta: { title: '价格配置' } },
    { path: '/scan', name: 'scan', component: () => import('@/views/ScanView.vue'), meta: { title: '扫描' } },
  ],
})

export default router
