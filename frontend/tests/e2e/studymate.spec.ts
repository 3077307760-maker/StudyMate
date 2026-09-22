import { expect, test, type APIRequestContext } from '@playwright/test'

const unique = Date.now()

async function waitForReady(
  request: APIRequestContext,
  documentId: string,
  headers: Record<string, string>,
) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const response = await request.get(`/api/documents/${documentId}`, { headers })
    expect(response.ok()).toBeTruthy()
    if ((await response.json()).status === 'ready') return
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('document indexing timed out')
}
test('register, upload and ask with citation', async ({ page, request }) => {
  const email = `e2e-${unique}@example.com`
  const password = 'password123'
  const register = await request.post('/api/auth/register', {
    data: { email, password, display_name: 'E2E 用户' },
  })
  expect(register.ok()).toBeTruthy()
  const auth = await register.json()
  const headers = { Authorization: `Bearer ${auth.access_token}` }

  const courseResponse = await request.post('/api/courses', {
    data: { name: 'E2E 操作系统' },
    headers,
  })
  const course = await courseResponse.json()

  const upload = await request.post(`/api/courses/${course.id}/documents`, {
    headers,
    multipart: {
      file: {
        name: 'e2e-notes.md',
        mimeType: 'text/markdown',
        buffer: Buffer.from(
          '# 进程与线程\n\n进程是资源分配的基本单位。线程是处理器调度和分派的基本单位，同一进程内的线程共享资源。',
        ),
      },
    },
  })
  expect(upload.ok()).toBeTruthy()
  const document = await upload.json()
  await waitForReady(request, document.id, headers)

  await page.goto('/login')
  await page.getByPlaceholder('student@example.com').fill(email)
  await page.getByPlaceholder('至少 8 位').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL('**/courses')

  await page.goto(`/courses/${course.id}/chat`)
  await page.getByPlaceholder('针对课程资料提问，Ctrl/⌘ + Enter 发送').fill('进程和线程有什么区别？')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByText('本次引用')).toBeVisible()
  await expect(page.locator('.citation-card')).toHaveCount(1)
})
