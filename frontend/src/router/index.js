import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
        path: 'notes/:id',
        name: 'NotebookDetail',
        component: () => import('../views/NotebookDetail.vue')
      },
      {
        path: 'notes/folder/:id',
        name: 'FolderDetail',
        component: () => import('../views/FolderDetail.vue')
      },
      {
        path: 'notes/edit/:id',
        name: 'NoteEditor',
        component: () => import('../views/NoteEditor.vue')
      },
      {
        path: 'notes/new/:folderId',
        name: 'NewNote',
        component: () => import('../views/NoteEditor.vue')
      },
      {
        path: 'todos',
        name: 'Todos',
        component: () => import('../views/Todos.vue')
      },
      {
        path: 'shop',
        name: 'Shop',
        component: () => import('../views/Shop.vue')
      },
      {
        path: 'backpack',
        name: 'Backpack',
        component: () => import('../views/Backpack.vue')
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/Profile.vue')
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

  // If guest route and user is authenticated, redirect to home
  if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'Home' })
    return
  }

  next()
})

export default router
