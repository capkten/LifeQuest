import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCultivationStore } from '../stores/cultivation'

const cultivationRouteComponent = () => import('../components/cultivation/CultivationStatusBar.vue')

const routes = [
  {
    path: '/oauth/authorize',
    name: 'OAuthAuthorize',
    component: () => import('../views/OAuthAuthorize.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true, title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guest: true, title: '注册' }
  },
  {
    path: '/',
    component: () => import('../components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'notes',
        name: 'Notes',
        component: () => import('../views/Notes.vue'),
        meta: { title: '笔记' }
      },
      {
        path: 'notes/:notebookId',
        name: 'NotebookWorkspace',
        component: () => import('../views/NotebookFileManage.vue'),
        meta: { title: '笔记本' }
      },
      {
        path: 'notes/:notebookId/sync',
        name: 'NoteSync',
        component: () => import('../views/NoteSync.vue'),
        meta: { title: '文件夹同步' }
      },
      {
        path: 'notes/:notebookId/view/:noteId',
        name: 'NotebookWorkspaceView',
        component: () => import('../views/NotebookFileManage.vue'),
        meta: { title: '笔记本' }
      },
      {
        path: 'notes/:notebookId/edit/:noteId',
        name: 'NotebookWorkspaceEdit',
        component: () => import('../views/NoteEditor.vue'),
        meta: { title: '笔记' }
      },
      {
        path: 'notes/:notebookId/new',
        name: 'NewNoteInWorkspace',
        component: () => import('../views/NoteEditor.vue'),
        meta: { title: '新建笔记' }
      },
      {
        path: 'notes/new/:notebookId',
        name: 'NewNote',
        component: () => import('../views/NoteEditor.vue'),
        meta: { title: '新建笔记' }
      },
      {
        path: 'notes/edit/:id',
        name: 'NoteEditor',
        component: () => import('../views/NoteEditor.vue'),
        meta: { title: '编辑笔记' }
      },
      {
        path: 'todos',
        name: 'Todos',
        component: () => import('../views/Todos.vue'),
        meta: { title: '待办' }
      },
      {
        path: 'review',
        name: 'WeeklyReview',
        component: () => import('../views/WeeklyReview.vue'),
        meta: { title: '周复盘' }
      },
      {
        path: 'cultivation',
        name: 'Cultivation',
        component: () => import('../views/Cultivation.vue'),
        meta: { title: '修炼' }
      },
      {
        path: 'world',
        name: 'World',
        component: () => import('../views/World.vue'),
        meta: { title: '凡界' }
      },
      {
        path: 'sects',
        name: 'Sects',
        component: () => import('../views/Sects.vue'),
        meta: { title: '宗门' }
      },
      {
        path: 'techniques',
        name: 'Techniques',
        component: () => import('../views/Techniques.vue'),
        meta: { title: '功法' }
      },
      {
        path: 'npcs',
        name: 'Npcs',
        component: () => import('../views/Npcs.vue'),
        meta: { title: '人物关系' }
      },
      {
        path: 'tribulations',
        name: 'Tribulations',
        component: () => import('../views/Tribulations.vue'),
        meta: { title: '渡劫' }
      },
      {
        path: 'immortal/world',
        name: 'ImmortalWorld',
        component: () => import('../views/ImmortalWorld.vue'),
        meta: { requiresAscended: true, title: '仙界' }
      },
      {
        path: 'immortal/activities',
        name: 'ImmortalActivities',
        component: () => import('../views/ImmortalActivities.vue'),
        meta: { requiresAscended: true, title: '仙界活动' }
      },
      {
        path: 'immortal/officials',
        name: 'ImmortalOfficials',
        component: () => import('../views/ImmortalOfficials.vue'),
        meta: { requiresAscended: true, title: '仙官委托' }
      },
      {
        path: 'shop',
        name: 'Shop',
        component: () => import('../views/Shop.vue'),
        meta: { title: '商城' }
      },
      {
        path: 'shop/history',
        name: 'ExchangeHistory',
        component: () => import('../views/ExchangeHistory.vue'),
        meta: { title: '兑换历史' }
      },
      {
        path: 'backpack',
        name: 'Backpack',
        component: () => import('../views/Backpack.vue'),
        meta: { title: '背包' }
      },
      {
        path: 'backpack/history',
        name: 'BackpackHistory',
        component: () => import('../views/BackpackHistory.vue'),
        meta: { title: '背包历史' }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue'),
        meta: { title: '个人' }
      },
      {
        path: 'profile/edit',
        name: 'EditProfile',
        component: () => import('../views/EditProfile.vue'),
        meta: { title: '编辑资料' }
      },
      {
        path: 'coins/history',
        name: 'CoinHistory',
        component: () => import('../views/CoinHistory.vue'),
        meta: { title: '金币记录' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('../views/Projects.vue'),
        meta: { title: '项目' }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('../views/ProjectDetail.vue'),
        meta: { title: '项目详情' }
      },
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('../views/Calendar.vue'),
        meta: { title: '日历' }
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('../views/Stats.vue'),
        meta: { title: '统计' }
      },
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('../views/Finance.vue'),
        meta: { title: '记账' }
      },
      {
        path: 'finance/accounts',
        name: 'FinanceAccounts',
        component: () => import('../views/FinanceAccounts.vue'),
        meta: { title: '账户' }
      },
      {
        path: 'finance/transactions',
        name: 'FinanceTransactions',
        component: () => import('../views/FinanceTransactions.vue'),
        meta: { title: '账目明细' }
      },
      {
        path: 'finance/budgets',
        name: 'FinanceBudgets',
        component: () => import('../views/FinanceBudgets.vue'),
        meta: { title: '预算' }
      },
      {
        path: 'finance/debts',
        name: 'FinanceDebts',
        component: () => import('../views/FinanceDebts.vue'),
        meta: { title: '债务' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Check if route requires authentication (check matched routes)
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

  if (requiresAuth) {
    if (!authStore.isAuthenticated) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }

    // If authenticated but user data not loaded, fetch it
    if (!authStore.user) {
      try {
        await authStore.fetchUser()
      } catch (error) {
        authStore.logout()
        next({ name: 'Login', query: { redirect: to.fullPath } })
        return
      }
    }
  }

  if (to.matched.some(record => record.meta.requiresAscended)) {
    const cultivationStore = useCultivationStore()
    try {
      const overview = cultivationStore.overview || await cultivationStore.loadOverview()
      if (overview?.ascended !== true) {
        next({ name: 'Cultivation' })
        return
      }
    } catch (error) {
      next({ name: 'Cultivation' })
      return
    }
  }

  // If guest route and user is authenticated, redirect to home
  if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'Home' })
    return
  }

  next()
})

export default router
