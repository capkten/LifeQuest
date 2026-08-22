import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCultivationStore } from '../stores/cultivation'

const cultivationRouteComponent = () => import('../components/cultivation/CultivationStatusBar.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guest: true }
  },
  {
    path: '/',
    component: () => import('../components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue')
      },
      {
        path: 'notes',
        name: 'Notes',
        component: () => import('../views/Notes.vue')
      },
      {
        path: 'notes/:notebookId',
        name: 'NotebookWorkspace',
        component: () => import('../views/NotebookFileManage.vue')
      },
      {
        path: 'notes/:notebookId/view/:noteId',
        name: 'NotebookWorkspaceView',
        component: () => import('../views/NotebookFileManage.vue')
      },
      {
        path: 'notes/:notebookId/edit/:noteId',
        name: 'NotebookWorkspaceEdit',
        component: () => import('../views/NoteEditor.vue')
      },
      {
        path: 'notes/:notebookId/new',
        name: 'NewNoteInWorkspace',
        component: () => import('../views/NoteEditor.vue')
      },
      {
        path: 'notes/new/:notebookId',
        name: 'NewNote',
        component: () => import('../views/NoteEditor.vue')
      },
      {
        path: 'notes/edit/:id',
        name: 'NoteEditor',
        component: () => import('../views/NoteEditor.vue')
      },
      {
        path: 'todos',
        name: 'Todos',
        component: () => import('../views/Todos.vue')
      },
      {
        path: 'cultivation',
        name: 'Cultivation',
        component: () => import('../views/Cultivation.vue')
      },
      {
        path: 'world',
        name: 'World',
        component: () => import('../views/World.vue')
      },
      {
        path: 'sects',
        name: 'Sects',
        component: () => import('../views/Sects.vue')
      },
      {
        path: 'techniques',
        name: 'Techniques',
        component: () => import('../views/Techniques.vue')
      },
      {
        path: 'npcs',
        name: 'Npcs',
        component: () => import('../views/Npcs.vue')
      },
      {
        path: 'tribulations',
        name: 'Tribulations',
        component: () => import('../views/Tribulations.vue')
      },
      {
        path: 'immortal/world',
        name: 'ImmortalWorld',
        component: () => import('../views/ImmortalWorld.vue'),
        meta: { requiresAscended: true }
      },
      {
        path: 'immortal/activities',
        name: 'ImmortalActivities',
        component: () => import('../views/ImmortalActivities.vue'),
        meta: { requiresAscended: true }
      },
      {
        path: 'shop',
        name: 'Shop',
        component: () => import('../views/Shop.vue')
      },
      {
        path: 'shop/history',
        name: 'ExchangeHistory',
        component: () => import('../views/ExchangeHistory.vue')
      },
      {
        path: 'backpack',
        name: 'Backpack',
        component: () => import('../views/Backpack.vue')
      },
      {
        path: 'backpack/history',
        name: 'BackpackHistory',
        component: () => import('../views/BackpackHistory.vue')
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue')
      },
      {
        path: 'profile/edit',
        name: 'EditProfile',
        component: () => import('../views/EditProfile.vue')
      },
      {
        path: 'coins/history',
        name: 'CoinHistory',
        component: () => import('../views/CoinHistory.vue')
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('../views/Projects.vue')
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('../views/ProjectDetail.vue')
      },
      {
        path: 'calendar',
        name: 'Calendar',
        component: () => import('../views/Calendar.vue')
      },
      {
        path: 'stats',
        name: 'Stats',
        component: () => import('../views/Stats.vue')
      },
      {
        path: 'finance',
        name: 'Finance',
        component: () => import('../views/Finance.vue')
      },
      {
        path: 'finance/accounts',
        name: 'FinanceAccounts',
        component: () => import('../views/FinanceAccounts.vue')
      },
      {
        path: 'finance/transactions',
        name: 'FinanceTransactions',
        component: () => import('../views/FinanceTransactions.vue')
      },
      {
        path: 'finance/budgets',
        name: 'FinanceBudgets',
        component: () => import('../views/FinanceBudgets.vue')
      },
      {
        path: 'finance/debts',
        name: 'FinanceDebts',
        component: () => import('../views/FinanceDebts.vue')
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
