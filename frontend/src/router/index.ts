import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/courses' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { public: true },
    },
    { path: '/courses', name: 'courses', component: () => import('@/views/CoursesView.vue') },
    {
      path: '/courses/:courseId',
      name: 'course',
      component: () => import('@/views/CourseView.vue'),
    },
    {
      path: '/courses/:courseId/chat/:conversationId?',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/courses/:courseId/quiz',
      name: 'quiz-create',
      component: () => import('@/views/QuizView.vue'),
    },
    {
      path: '/courses/:courseId/quiz/:quizId',
      name: 'quiz-take',
      component: () => import('@/views/QuizView.vue'),
    },
    {
      path: '/courses/:courseId/wrong-book',
      name: 'wrong-book',
      component: () => import('@/views/WrongBookView.vue'),
    },
    {
      path: '/courses/:courseId/review',
      name: 'review',
      component: () => import('@/views/ReviewView.vue'),
    },
    { path: '/:pathMatch(.*)*', component: () => import('@/views/NotFoundView.vue') },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && auth.isAuthenticated) return { name: 'courses' }
  return true
})

export default router
