import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import { chromium } from 'playwright'

const baseURL = process.env.TEST_BASE_URL || 'http://127.0.0.1:3000'
const apiURL = process.env.TEST_API_URL || baseURL
const apiPath = path => new URL(path, apiURL).href

async function reviewContext(browser) {
  const context = await browser.newContext({ viewport: { width: 375, height: 667 }, baseURL })
  if (apiURL !== baseURL) {
    await context.route('**/api/**', async route => {
      const url = new URL(route.request().url())
      const response = await route.fetch({ url: apiPath(`${url.pathname}${url.search}`) })
      await route.fulfill({ response })
    })
  }
  return context
}

test('a first cave visitor can skip the introduction and revisit it without creating a task', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `intro-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    const introduction = page.getByRole('article', { name: '初到洞府', exact: true })
    await introduction.getByRole('heading', { name: '最近最想推进的一件事？', exact: true }).waitFor()
    await introduction.getByText('我是小满，替你照看这一小处。', { exact: true }).waitFor()
    assert.equal(await page.getByRole('group', { name: '今日三签', exact: true }).count(), 0)
    assert.equal(await introduction.getByRole('button', { name: '整理桌面 10 分钟', exact: true }).count(), 1)
    assert.equal(await introduction.getByRole('button', { name: '读 5 页书', exact: true }).count(), 1)
    assert.equal(await introduction.getByRole('button', { name: '写下今天最想推进的事', exact: true }).count(), 1)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    if (process.env.TEST_CAPTURE_DIR) {
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-onboarding-mobile.png`, fullPage: true })
      await page.setViewportSize({ width: 1440, height: 1000 })
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) >= 200)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-onboarding-desktop.png`, fullPage: true })
    }
    await introduction.getByRole('button', { name: '跳过引导', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('heading', { name: '起笔，就从这里。', exact: true }).waitFor()
    let today = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(today.onboarding.status, 'skipped')
    assert.equal(today.primary_sign, null)
    await page.reload()
    await page.getByRole('heading', { name: '起笔，就从这里。', exact: true }).waitFor()
    assert.equal(await page.getByRole('article', { name: '初到洞府', exact: true }).count(), 0)
    await page.goto('/cave/settings')
    await page.getByRole('button', { name: '重看首次引导', exact: true }).focus()
    await page.keyboard.press('Enter')
    const replay = page.getByRole('dialog', { name: '小满的引导', exact: true })
    await replay.getByText('我是小满，替你照看这一小处。', { exact: true }).waitFor()
    await replay.getByText('白鹿会在第三次成功入定后与你相逢，不会因重看引导提前解锁。', { exact: true }).waitFor()
    await page.keyboard.press('Escape')
    await replay.waitFor({ state: 'hidden' })
    today = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(today.onboarding.status, 'skipped')
    assert.equal(today.primary_sign, null)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('the introduction creates a real today task and offers a fifteen minute first session', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `first-task-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    const introduction = page.getByRole('article', { name: '初到洞府', exact: true })
    await introduction.getByRole('button', { name: '读 5 页书', exact: true }).focus()
    await page.keyboard.press('Enter')
    const input = introduction.getByRole('textbox', { name: '你现在想推进的一件事', exact: true })
    assert.equal(await input.inputValue(), '读 5 页书')
    await input.focus()
    await page.keyboard.press('Enter')
    await page.getByText('第一签已写好。从 15 分钟开始，照看这一件事。', { exact: true }).waitFor()
    const today = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(today.primary_sign.title, '读 5 页书')
    assert.equal(today.onboarding.status, 'pending')
    const start = page.getByRole('button', { name: /入定 15 分钟/ })
    await start.focus()
    await page.keyboard.press('Enter')
    const sheet = page.getByRole('dialog', { name: '落座入定', exact: true })
    assert.equal(await sheet.getByRole('button', { name: '15 分钟', exact: true }).getAttribute('aria-pressed'), 'true')
    assert.equal(await sheet.getByRole('checkbox', { name: '完成后同时完成任务', exact: true }).isChecked(), true)
    await sheet.getByRole('button', { name: '开始入定', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.waitForURL(/\/cave\/session\//)
    const id = new URL(page.url()).pathname.split('/').at(-1)
    const session = (await (await context.request.get(apiPath(`/api/cave/sessions/${id}`))).json()).session
    assert.equal(session.target_duration, 15)
    assert.equal(session.todo_id, today.primary_sign.id)
    await page.getByRole('button', { name: '跳过引导', exact: true }).click()
    const after = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(after.onboarding.status, 'skipped')
    assert.equal(after.active_session.id, id)
    await page.getByRole('button', { name: '提前结束', exact: true }).click()
    await page.getByRole('button', { name: '结束并收好这段时间', exact: true }).click()
    await page.getByRole('heading', { name: '这一段，已收好', exact: true }).waitFor()
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a first fifteen-minute retreat completes the introduction with a common encounter and a deer preview', { skip: !process.env.TEST_LONG_ONBOARDING, timeout: 900_000 }, async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `full-intro-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('article', { name: '初到洞府', exact: true }).getByRole('textbox', { name: '你现在想推进的一件事', exact: true }).fill('完成真正的第一段入定')
    await page.getByRole('button', { name: '写好这一签', exact: true }).click()
    await page.getByRole('button', { name: /入定 15 分钟/ }).click()
    await page.getByRole('dialog', { name: '落座入定', exact: true }).getByRole('button', { name: '开始入定', exact: true }).click()
    await page.waitForURL(/\/cave\/session\//)
    const id = new URL(page.url()).pathname.split('/').at(-1)
    await page.getByText('成功收功后，就完成初到洞府的引导。', { exact: true }).waitFor()
    // Real elapsed time reaches the existing 80% threshold: 12 minutes of a 15-minute target.
    await page.waitForFunction(() => ![...document.querySelectorAll('button')].find(button => button.textContent.trim() === '收功')?.disabled, null, { timeout: 790_000 })
    const completion = page.waitForResponse(response => response.url().endsWith('/api/cave/onboarding/complete') && response.request().method() === 'POST')
    await page.getByRole('button', { name: '收功', exact: true }).click()
    await page.waitForURL(`/cave/return/${id}`)
    assert.equal((await completion).status(), 200)
    const preview = page.getByRole('region', { name: '白鹿的预告', exact: true })
    await preview.getByText('白鹿还在山中。第三次成功入定后，才能邀它随行。', { exact: true }).waitFor()
    await page.getByRole('region', { name: '本次奇遇', exact: true }).getByText('凡品', { exact: true }).waitFor()
    const today = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(today.onboarding.status, 'completed')
    assert.equal(today.onboarding.completed_session_id, id)
    const receipt = (await (await context.request.get(apiPath(`/api/cave/sessions/${id}`))).json()).session
    assert.equal(receipt.target_duration, 15)
    assert.equal(receipt.settlement_result.task_completed, true)
    assert.equal(receipt.qi_gained >= 12, true)
    const companions = await (await context.request.get(apiPath('/api/cave/companions'))).json()
    assert.equal(companions.pets.find(pet => pet.key === 'white_deer').unlocked, false)
    assert.equal(companions.active_pet_key, null)
    const before = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    const replay = await context.request.post(apiPath('/api/cave/onboarding/complete'), { data: { session_id: id, request_id: randomUUID() } })
    assert.equal(replay.status(), 200)
    const after = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    assert.equal(after.cultivation, before.cultivation)
    assert.equal(after.spirit_stones, before.spirit_stones)
    if (process.env.TEST_CAPTURE_DIR) await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-onboarding-complete-mobile.png`, fullPage: true })
    await page.getByRole('button', { name: '回洞府', exact: true }).click()
    await page.waitForURL('/')
    assert.equal(await page.getByRole('article', { name: '初到洞府', exact: true }).count(), 0)
    await page.reload()
    assert.equal(await page.getByRole('article', { name: '初到洞府', exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a user can promote a backup sign without using the daily reroll', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const suffix = randomUUID().slice(0, 8)
    const username = `cave-${suffix}`
    const password = randomUUID()
    const registration = await context.request.post(apiPath('/api/auth/register'), {
      data: { username, email: `${username}@example.com`, password },
    })
    assert.equal(registration.status(), 200)
    const login = await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })
    assert.equal(login.status(), 200)
    const tokens = await login.json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    for (const title of ['读五页书', '整理一页笔记', '写下一个想法', '走出门看看']) {
      const result = await context.request.post(apiPath('/api/todos/workbench/tasks'), {
        data: { title, schedule: 'today', request_id: randomUUID() },
      })
      assert.equal(result.status(), 200)
    }
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(({ access_token, refresh_token }) => {
      localStorage.setItem('token', access_token)
      localStorage.setItem('refreshToken', refresh_token)
    }, tokens)
    await page.goto('/')
    const signs = page.getByRole('group', { name: '今日三签' })
    await signs.getByRole('button').nth(2).waitFor()
    const backup = signs.getByRole('button').nth(1)
    const promotedTitle = await backup.locator('strong').innerText()
    await backup.click()
    await page.getByRole('heading', { name: promotedTitle, exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: '换一签', exact: true }).isEnabled(), true)
    assert.equal(await signs.getByRole('button', { pressed: true }).locator('strong').innerText(), promotedTitle)
  } finally {
    await context.unrouteAll({ behavior: 'wait' })
    await context.close()
    await browser.close()
  }
})

test('an unseen return survives reload until the user explicitly returns to the cave', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `return-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const session = await (await context.request.post(apiPath('/api/cave/sessions'), { data: { target_duration: 15, request_id: randomUUID() } })).json()
    const settled = await context.request.post(apiPath(`/api/cave/sessions/${session.id}/settle`), { data: { early: true, request_id: randomUUID() } })
    assert.equal(settled.status(), 200)
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('link', { name: '查看归来', exact: true }).click()
    await page.getByRole('heading', { name: '这一段，已收好' }).waitFor()
    assert.equal(await page.getByRole('status', { name: '本次修为' }).innerText(), '+0')
    await page.getByText('灵气 0 → 修为 0', { exact: true }).waitFor()
    await page.goto('/')
    await page.reload()
    await page.getByRole('link', { name: '查看归来', exact: true }).click()
    await page.getByRole('button', { name: '回洞府', exact: true }).click()
    await page.waitForURL('/')
    await page.reload()
    assert.equal(await page.getByRole('link', { name: '查看归来', exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('the first successful return shows its common encounter and frozen total', { timeout: 90_000 }, async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `encounter-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const session = await (await context.request.post(apiPath('/api/cave/sessions'), { data: { target_duration: 1, request_id: randomUUID() } })).json()
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.setViewportSize({ width: 1280, height: 840 })
    // Let the real foreground countdown navigate and settle; do not alter the database or clock.
    const settlementResponse = page.waitForResponse(response => response.url().endsWith(`/cave/sessions/${session.id}/settle`) && response.request().method() === 'POST', { timeout: 75_000 })
    await page.goto(`/cave/session/${session.id}`)
    await page.waitForURL(`/cave/return/${session.id}`, { timeout: 75_000 })
    const response = await settlementResponse
    assert.equal(response.status(), 200)
    const settled = await response.json()
    assert.equal(settled.encounter_result?.rarity, 'common')
    if (settled.return_summary.total_reward.cultivation > 0) {
      await page.waitForFunction(() => Number(document.querySelector('[role="progressbar"][aria-label="修为进度"]')?.getAttribute('aria-valuenow')) > 0, null, { timeout: 5000 })
    } else {
      await page.getByText('60', { exact: true }).waitFor({ timeout: 5000 })
    }
    const encounter = page.getByRole('region', { name: '本次奇遇' })
    await encounter.getByRole('heading', { name: settled.encounter_result.title, exact: true }).waitFor()
    await encounter.getByText('凡品', { exact: true }).waitFor()
    await encounter.getByText(settled.encounter_result.story_text, { exact: true }).waitFor()
    assert.equal(await page.getByRole('status', { name: '本次修为' }).innerText(), `+${settled.return_summary.total_reward.cultivation}`)
    const replay = await (await context.request.get(apiPath(`/api/cave/sessions/${session.id}`))).json()
    assert.deepEqual(replay.session.return_summary, settled.return_summary)
    await page.getByRole('button', { name: '翻开图鉴', exact: true }).click()
    const catalog = page.getByRole('dialog', { name: '万象机缘录 · 顿悟图鉴' })
    await catalog.getByText(settled.encounter_result.title, { exact: true }).waitFor()
    await page.keyboard.press('Escape')
    await catalog.waitFor({ state: 'hidden' })
    if (process.env.TEST_CAPTURE_DIR) {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) === 0)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-return-mobile.png`, fullPage: true })
      const mobile = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth > innerWidth, mainNumberFont: getComputedStyle(document.querySelector('.return-total')).fontSize }))
      await page.setViewportSize({ width: 1280, height: 840 })
      await page.reload()
      await page.getByRole('region', { name: '本次奇遇' }).waitFor()
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) >= 200)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-return-desktop.png` })
      console.log(JSON.stringify({ mobile, desktopOverflow: await page.evaluate(() => document.documentElement.scrollWidth > innerWidth) }))
    }
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a new user can explore growth, five codex categories and locked companions', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `growth-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('navigation', { name: '主导航' }).getByRole('link', { name: '成长', exact: true }).click()
    await page.waitForURL('/cave/growth')
    await page.getByRole('heading', { name: '成长', exact: true }).waitFor()
    await page.getByRole('link', { name: '图鉴', exact: true }).waitFor()
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    if (process.env.TEST_CAPTURE_DIR) {
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-growth-mobile.png`, fullPage: true })
      await page.setViewportSize({ width: 1280, height: 840 })
      await page.reload()
      await page.getByRole('link', { name: '图鉴', exact: true }).waitFor()
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) >= 200)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-growth-desktop.png`, fullPage: true })
      await page.setViewportSize({ width: 375, height: 667 })
    }
    await page.getByRole('link', { name: '图鉴', exact: true }).click()
    const categories = page.getByRole('group', { name: '图鉴分类' })
    for (const category of ['奇遇', '灵宠', '同门', '地点', '功法']) await categories.getByRole('button', { name: new RegExp(`^${category}`) }).waitFor()
    await page.getByRole('link', { name: '伙伴', exact: true }).click()
    await page.getByRole('heading', { name: '小满', exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: '尚未解锁', exact: true }).count(), 3)
    assert.equal(await page.getByRole('button', { name: '尚未解锁', exact: true }).first().isEnabled(), false)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    if (process.env.TEST_CAPTURE_DIR) {
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-companions-mobile.png`, fullPage: true })
      await page.setViewportSize({ width: 1280, height: 840 })
      await page.reload()
      await page.getByRole('heading', { name: '小满', exact: true }).waitFor()
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) >= 200)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-companions-desktop.png`, fullPage: true })
    }
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('web cave settings explain in-app reminders without offering a native permission prompt', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `notify-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/cave/settings')
    const notifications = page.getByRole('region', { name: '入定通知', exact: true })
    await notifications.getByText('网页只保留应用内提醒，不请求系统通知。', { exact: true }).waitFor()
    assert.equal(await notifications.getByRole('button', { name: '允许系统通知', exact: true }).count(), 0)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a cached cave remains available after an API transport failure on reload', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `offline-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const created = await context.request.post(apiPath('/api/todos/workbench/tasks'), { data: { title: '断网也记得这一签', schedule: 'today', request_id: randomUUID() } })
    assert.equal(created.status(), 200)
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('heading', { name: '断网也记得这一签', exact: true }).waitFor()
    await context.route('**/api/**', route => route.abort('internetdisconnected'))
    await page.reload()
    await page.getByRole('status').getByText('离线', { exact: true }).waitFor()
    await page.getByRole('heading', { name: '断网也记得这一签', exact: true }).waitFor()
    assert.equal(new URL(page.url()).pathname, '/')
    assert.equal(await page.getByRole('button', { name: /入定 \d+ 分钟/ }).isDisabled(), true)
    await context.unrouteAll({ behavior: 'wait' })
    await context.setExtraHTTPHeaders({})
    await page.evaluate(() => {
      localStorage.setItem('token', `${localStorage.getItem('token').split('.').slice(0, 2).join('.')}.invalid`)
      localStorage.removeItem('refreshToken')
    })
    const rejected = page.waitForResponse(response => response.url().endsWith('/api/users/me') && response.status() === 401)
    await page.reload()
    await rejected
    await page.waitForURL(/\/login(?:\?|$)/)
    assert.equal(await page.getByRole('heading', { name: '断网也记得这一签', exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('yesterday cached signs are not presented as an empty today after offline rollover', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    await context.addInitScript(() => {
      const now = Date.now.bind(Date)
      Date.now = () => now() + Number(localStorage.getItem('test:day-shift') || 0)
    })
    const username = `midnight-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.request.post(apiPath('/api/todos/workbench/tasks'), { headers: { Authorization: `Bearer ${tokens.access_token}` }, data: { title: '只记在昨天缓存中的签', schedule: 'today', request_id: randomUUID() } })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('heading', { name: '只记在昨天缓存中的签', exact: true }).waitFor()
    await context.route('**/api/**', route => route.abort('internetdisconnected'))
    await page.evaluate(() => localStorage.setItem('test:day-shift', '86400000'))
    await page.reload()
    await page.getByRole('heading', { name: '等联网，再取今日签', exact: true }).waitFor()
    assert.equal(await page.getByRole('group', { name: '今日三签', exact: true }).count(), 0)
    assert.equal(await page.getByRole('button', { name: /今日签/ }).count(), 0)
    assert.equal(await page.getByText('今日无签。写下一件事，便是起笔。', { exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('another account cannot restore the previous account cave while the API is unavailable', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const accounts = []
    for (const prefix of ['first', 'second']) {
      const username = `${prefix}-${randomUUID().slice(0, 8)}`
      const password = randomUUID()
      await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
      accounts.push(await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json())
    }
    await context.request.post(apiPath('/api/todos/workbench/tasks'), { headers: { Authorization: `Bearer ${accounts[0].access_token}` }, data: { title: '只属于前一个账号的签', schedule: 'today', request_id: randomUUID() } })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, accounts[0])
    await page.goto('/')
    await page.getByRole('heading', { name: '只属于前一个账号的签', exact: true }).waitFor()
    await context.route('**/api/**', route => route.abort('internetdisconnected'))
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, accounts[1])
    await page.reload()
    await page.waitForURL(/\/login(?:\?|$)/)
    assert.equal(await page.getByRole('heading', { name: '只属于前一个账号的签', exact: true }).count(), 0)
    assert.equal(await page.getByRole('complementary', { name: '待收功', exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('offline early settlement survives reload and retries the same request without completing its task', { timeout: 120_000 }, async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `queue-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    await context.request.post(apiPath('/api/todos/workbench/tasks'), { data: { title: '未完的事，联网再收好', schedule: 'today', request_id: randomUUID() } })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('button', { name: /入定 15 分钟/ }).click()
    await page.getByRole('dialog', { name: '落座入定' }).getByRole('button', { name: '开始入定', exact: true }).click()
    await page.waitForURL(/\/cave\/session\//)
    const sessionId = new URL(page.url()).pathname.split('/').at(-1)
    let disconnected = true
    let networkFailed = false
    const payloads = []
    await context.route('**/api/**', async route => {
      const settlementRequest = route.request().url().endsWith(`/sessions/${sessionId}/settle`)
      if (settlementRequest) payloads.push(route.request().postDataJSON())
      if (disconnected && (settlementRequest || networkFailed)) {
        networkFailed = true
        await route.abort('internetdisconnected')
      } else await route.fallback()
    })
    await page.getByRole('button', { name: '提前结束', exact: true }).click()
    await page.getByRole('button', { name: '结束并收好这段时间', exact: true }).click()
    await page.getByRole('heading', { name: '等待联网收功', exact: true }).waitFor()
    assert.equal(await page.getByRole('status').getByText('这段时间已保存在此设备，联网后会自动确认。', { exact: true }).isVisible(), true)
    assert.equal(await page.getByLabel('本次修为', { exact: true }).count(), 0)
    await page.reload()
    await page.getByRole('heading', { name: '等待联网收功', exact: true }).waitFor()
    assert.equal(await page.getByLabel('本次修为', { exact: true }).count(), 0)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    if (process.env.TEST_CAPTURE_DIR) {
      await page.waitForFunction(() => ![...document.querySelectorAll('[role="alert"]')].some(element => element.textContent.includes('网络连接失败，请检查网络。')))
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-pending-mobile.png`, fullPage: true })
      await page.setViewportSize({ width: 1440, height: 1000 })
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) >= 200)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-pending-desktop.png`, fullPage: true })
      await page.setViewportSize({ width: 375, height: 667 })
    }
    await page.getByRole('link', { name: '先回洞府', exact: true }).click()
    await page.getByRole('heading', { name: '等待联网收功', exact: true }).waitFor()
    await page.getByRole('navigation', { name: '主导航', exact: true }).getByRole('link', { name: '待办', exact: true }).click()
    await page.waitForURL('/todos')
    assert.equal(await page.getByRole('complementary', { name: '进行中的入定', exact: true }).count(), 0)
    disconnected = false
    await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await page.getByRole('heading', { name: '这一段，已收好', exact: true }).waitFor({ timeout: 75_000 })
    assert.equal(payloads.length >= 2, true)
    assert.equal(payloads[0].early, true)
    for (const payload of payloads) assert.deepEqual(payload, payloads[0])
    const today = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(today.active_session, null)
    assert.equal(today.primary_sign.title, '未完的事，联网再收好')
    await page.reload()
    await page.getByRole('heading', { name: '这一段，已收好', exact: true }).waitFor()
    assert.equal(await page.getByRole('complementary', { name: '待收功', exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a lost successful settlement reply is replayed after reload without a second reward', { timeout: 150_000 }, async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `lost-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const started = await (await context.request.post(apiPath('/api/cave/sessions'), { data: { target_duration: 1, request_id: randomUUID() } })).json()
    let disconnected = false
    let firstReceipt = null
    let firstResources = null
    let confirmFirstCommit
    const firstCommit = new Promise(resolve => { confirmFirstCommit = resolve })
    const payloads = []
    await context.route('**/api/**', async route => {
      if (route.request().url().endsWith(`/sessions/${started.id}/settle`) && !disconnected) {
        payloads.push(route.request().postDataJSON())
        const response = await route.fetch({ url: apiPath(`/api/cave/sessions/${started.id}/settle`) })
        assert.equal(response.status(), 200)
        const receipt = await response.json()
        if (!firstReceipt) {
          firstReceipt = receipt
          disconnected = true
          await route.abort('internetdisconnected')
          confirmFirstCommit()
        } else {
          assert.deepEqual(receipt.return_summary, firstReceipt.return_summary)
          await route.fulfill({ response })
        }
      } else if (disconnected) await route.abort('internetdisconnected')
      else await route.fallback()
    })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto(`/cave/session/${started.id}`)
    await page.getByRole('heading', { name: '等待联网收功', exact: true }).waitFor({ timeout: 80_000 })
    if (!firstReceipt) await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await firstCommit
    assert.equal(firstReceipt.status, 'completed')
    assert.equal(firstReceipt.encounter_result.rarity, 'common')
    firstResources = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    assert.equal(Number.isInteger(firstResources.cultivation), true)
    assert.equal(Number.isInteger(firstResources.spirit_stones), true)
    assert.equal(await page.getByLabel('本次修为', { exact: true }).count(), 0)
    await page.reload()
    await page.getByRole('heading', { name: '等待联网收功', exact: true }).waitFor()
    disconnected = false
    await page.evaluate(() => window.dispatchEvent(new Event('online')))
    await page.getByRole('heading', { name: '这一段，已收好', exact: true }).waitFor()
    assert.equal(payloads.length >= 2, true)
    for (const payload of payloads) assert.deepEqual(payload, payloads[0])
    const resources = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    assert.equal(resources.cultivation, firstResources.cultivation)
    assert.equal(resources.spirit_stones, firstResources.spirit_stones)
    const persisted = await (await context.request.get(apiPath(`/api/cave/sessions/${started.id}`))).json()
    assert.deepEqual(persisted.session.return_summary, firstReceipt.return_summary)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('task completion is disabled offline without queueing a task completion request', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `task-offline-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    await context.request.post(apiPath('/api/todos/workbench/tasks'), { data: { title: '联网后再完成这件事', schedule: 'today', request_id: randomUUID() } })
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/todos?tab=tasks')
    const complete = page.getByRole('button', { name: '完成 联网后再完成这件事', exact: true })
    await complete.waitFor()
    assert.equal(await complete.isEnabled(), true)
    let completionRequests = 0
    page.on('request', request => { if (request.method() === 'POST' && /\/tasks\/[^/]+\/complete(?:\?|$)/.test(request.url())) completionRequests += 1 })
    await complete.focus()
    await context.setOffline(true)
    await page.getByRole('status').getByText('离线', { exact: true }).waitFor()
    assert.equal(await complete.isDisabled(), true)
    await page.getByText('请联网后再完成任务；离线不会排队完成任务。', { exact: true }).waitFor()
    await page.keyboard.press('Enter')
    assert.equal(completionRequests, 0)
    await context.setOffline(false)
    await page.waitForFunction(() => !document.querySelector('button[aria-label="完成 联网后再完成这件事"]').disabled)
    assert.equal(completionRequests, 0)
  } finally { await context.setOffline(false); await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('native reminder denial does not block starting and its off preference survives reload', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    await context.addInitScript(() => {
      window.notificationCalls = []
      window.__TAURI_INTERNALS__ = { invoke: async command => {
        window.notificationCalls.push(command)
        if (command === 'plugin:notification|is_permission_granted') return false
        if (command === 'plugin:notification|request_permission') return 'denied'
        throw new Error('Native command unavailable in browser system-adapter test')
      } }
    })
    const username = `denied-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/cave/settings')
    await page.getByText('应用运行时发出结束提醒；关闭后不承诺提醒。', { exact: true }).waitFor()
    assert.equal(await page.evaluate(() => window.notificationCalls.includes('plugin:notification|request_permission')), false)
    await page.goto('/')
    await page.getByRole('textbox', { name: '你现在想推进的一件事' }).fill('允许慢慢开始')
    await page.getByRole('button', { name: '写好这一签', exact: true }).click()
    await page.getByRole('button', { name: /入定 \d+ 分钟/ }).click()
    const draft = page.getByRole('dialog', { name: '落座入定' })
    await draft.getByRole('button', { name: '开始入定', exact: true }).click()
    await page.waitForURL(/\/cave\/session\//)
    assert.equal(await page.evaluate(() => window.notificationCalls.filter(command => command === 'plugin:notification|request_permission').length), 1)
    await page.getByRole('status').getByText('通知未开启，入定会继续，可在应用内迷你条查看。', { exact: true }).waitFor()
    await page.goto('/cave/settings')
    const notifications = page.getByRole('region', { name: '入定通知', exact: true })
    await notifications.getByRole('checkbox').uncheck()
    await page.reload()
    assert.equal(await notifications.getByRole('checkbox').isChecked(), false)
    assert.equal(await notifications.getByRole('button', { name: '允许系统通知', exact: true }).count(), 0)
    assert.equal(await page.evaluate(() => window.notificationCalls.includes('plugin:notification|request_permission')), false)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a new user can open senior letters from growth without being pushed into a trial', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `letters-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/cave/growth')
    await page.getByRole('link', { name: '同门书信', exact: true }).click()
    await page.waitForURL('/cave/letters')
    await page.getByRole('heading', { name: '同门书信', exact: true }).waitFor()
    await page.getByText('还没有来信', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: '接受试炼', exact: true }).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('an eligible user can read a delivered letter without accepting its trial', { skip: !process.env.TEST_SEED_DB }, async () => {
  const database = process.env.TEST_SEED_DB
  assert.equal(realpathSync(database), realpathSync(fileURLToPath(new URL('../../.harness/cave-stage05-runtime/preview.db', import.meta.url))), 'Only the isolated review database may be seeded')
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `letters-e2e-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    const registration = await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    assert.equal(registration.status(), 200)
    // Account age is a test precondition, not a business-data assertion or production clock hook.
    execFileSync(process.platform === 'win32' ? 'py' : 'python3', [
      ...(process.platform === 'win32' ? ['-3.12'] : []), '-I', '-c',
      'import sqlite3,sys; from datetime import datetime,timedelta,timezone; db=sqlite3.connect(sys.argv[1],timeout=30); row=db.execute("SELECT username FROM users WHERE username=?",(sys.argv[2],)).fetchone(); assert row==(sys.argv[2],); db.execute("UPDATE users SET created_at=? WHERE username=?",((datetime.now(timezone.utc)-timedelta(days=20)).replace(tzinfo=None).isoformat(" "),sys.argv[2])); db.commit(); db.close()',
      database, username,
    ])
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const delivered = await (await context.request.get(apiPath('/api/cave/letters'))).json()
    assert.equal(delivered.letters.length, 2)
    const letter = delivered.letters.find(item => item.senior_key === 'qingheng')
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('link', { name: '查看同门书信', exact: true }).waitFor()
    await page.goto('/cave/letters')
    await page.getByRole('link', { name: letter.title, exact: true }).click()
    await page.waitForURL(`/cave/letters/${letter.id}`)
    await page.getByRole('heading', { name: letter.title, exact: true }).waitFor()
    await page.getByText(letter.body, { exact: true }).waitFor()
    const reread = await (await context.request.get(apiPath(`/api/cave/letters/${letter.id}`))).json()
    assert.equal(reread.status, 'read')
    assert.equal(reread.trial.status, 'available')
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('an eligible user can accept one senior trial and decline another without a penalty', { skip: !process.env.TEST_SEED_DB }, async () => {
  const database = process.env.TEST_SEED_DB
  assert.equal(realpathSync(database), realpathSync(fileURLToPath(new URL('../../.harness/cave-stage05-runtime/preview.db', import.meta.url))), 'Only the isolated review database may be seeded')
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `trial-e2e-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    const registration = await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    assert.equal(registration.status(), 200)
    execFileSync(process.platform === 'win32' ? 'py' : 'python3', [
      ...(process.platform === 'win32' ? ['-3.12'] : []), '-I', '-c',
      'import sqlite3,sys; from datetime import datetime,timedelta,timezone; db=sqlite3.connect(sys.argv[1],timeout=30); row=db.execute("SELECT username FROM users WHERE username=?",(sys.argv[2],)).fetchone(); assert row==(sys.argv[2],); db.execute("UPDATE users SET created_at=? WHERE username=?",((datetime.now(timezone.utc)-timedelta(days=20)).replace(tzinfo=None).isoformat(" "),sys.argv[2])); db.commit(); db.close()',
      database, username,
    ])
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const delivered = await (await context.request.get(apiPath('/api/cave/letters'))).json()
    const letter = delivered.letters[0]
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto(`/cave/letters/${letter.id}`)
    await page.getByRole('button', { name: '接受试炼', exact: true }).click()
    await page.getByText('本周试炼已接下，完成后回来收功。', { exact: true }).waitFor()
    const reread = await (await context.request.get(apiPath(`/api/cave/letters/${letter.id}`))).json()
    assert.equal(reread.trial.status, 'accepted')
    assert.equal(reread.trial.can_accept, false)
    assert.equal(await page.getByRole('button', { name: '接受试炼', exact: true }).count(), 0)
    const other = delivered.letters.find(item => item.id !== letter.id)
    const before = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    await page.goto(`/cave/letters/${other.id}`)
    assert.equal(await page.getByRole('button', { name: '接受试炼', exact: true }).isEnabled(), false)
    await page.getByRole('button', { name: '暂不', exact: true }).click()
    await page.getByText('这次先放在案上，下周会有新的试炼。', { exact: true }).waitFor()
    const after = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    assert.equal(after.cultivation, before.cultivation)
    assert.equal(after.spirit_stones, before.spirit_stones)
    const inbox = await (await context.request.get(apiPath('/api/cave/letters'))).json()
    assert.equal(inbox.accepted_trial.letter_id, letter.id)
    assert.equal(inbox.letters.find(item => item.id === other.id).trial.status, 'declined')
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a proven senior trial reveals its story once without adding resources', { skip: !process.env.TEST_SEED_DB }, async () => {
  const database = process.env.TEST_SEED_DB
  assert.equal(realpathSync(database), realpathSync(fileURLToPath(new URL('../../.harness/cave-stage05-runtime/preview.db', import.meta.url))), 'Only the isolated review database may be seeded')
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `claim-e2e-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    assert.equal((await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })).status(), 200)
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const created = await context.request.post(apiPath('/api/todos/tasks'), { data: { title: '把搁置的这一页写完', difficulty: 'medium' } })
    assert.equal(created.status(), 200)
    const task = await created.json()
    // Only account/task ages are fixtures; acceptance, proof and rewards all use the real HTTP API.
    execFileSync(process.platform === 'win32' ? 'py' : 'python3', [
      ...(process.platform === 'win32' ? ['-3.12'] : []), '-I', '-c',
      'import sqlite3,sys; from datetime import datetime,timedelta,timezone; db=sqlite3.connect(sys.argv[1],timeout=30); now=datetime.now(timezone.utc).replace(tzinfo=None); db.execute("UPDATE users SET created_at=? WHERE username=?",((now-timedelta(days=13)).isoformat(" "),sys.argv[2])); db.execute("UPDATE tasks SET created_at=? WHERE id=? AND user_id=(SELECT id FROM users WHERE username=?)",((now-timedelta(days=4)).isoformat(" "),sys.argv[3].replace("-",""),sys.argv[2])); db.commit(); db.close()',
      database, username, task.id,
    ])
    const delivered = await (await context.request.get(apiPath('/api/cave/letters'))).json()
    const letter = delivered.letters.find(item => item.senior_key === 'lifeng')
    assert.equal(letter.trial.key, 'old_task')
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto(`/cave/letters/${letter.id}`)
    await page.getByRole('button', { name: '接受试炼', exact: true }).click()
    await page.getByText('本周试炼已接下，完成后回来收功。', { exact: true }).waitFor()
    assert.equal((await context.request.post(apiPath(`/api/todos/tasks/${task.id}/complete`))).status(), 200)
    const before = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    await page.reload()
    const claimedResponse = page.waitForResponse(response => response.url().endsWith(`/letters/${letter.id}/claim`) && response.request().method() === 'POST')
    await page.getByRole('button', { name: '领取见闻', exact: true }).click()
    const claimed = await (await claimedResponse).json()
    const reward = claimed.letters.find(item => item.id === letter.id).trial.reward
    const story = page.getByRole('region', { name: '试炼见闻' })
    await story.getByRole('heading', { name: reward.name, exact: true }).waitFor()
    await story.getByText(reward.story, { exact: true }).waitFor()
    const after = await (await context.request.get(apiPath('/api/cultivation/overview'))).json()
    assert.equal(after.cultivation, before.cultivation)
    assert.equal(after.spirit_stones, before.spirit_stones)
    assert.equal((await context.request.post(apiPath(`/api/cave/letters/${letter.id}/claim`), { data: { request_id: randomUUID() } })).status(), 200)
    const codex = await (await context.request.get(apiPath('/api/cave/codex'))).json()
    assert.equal(codex.categories.find(category => category.key === 'seniors').entries.find(entry => entry.key === 'trial:old_task').unlock_count, 1)
    await page.reload()
    await story.waitFor()
    assert.equal(await page.getByRole('button', { name: '领取见闻', exact: true }).count(), 0)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
    if (process.env.TEST_CAPTURE_DIR) {
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-letter-mobile.png`, fullPage: true })
      await page.setViewportSize({ width: 1280, height: 840 })
      await page.reload()
      await story.waitFor()
      await page.waitForFunction(() => parseFloat(getComputedStyle(document.querySelector('.app-main')).marginLeft) >= 200)
      await page.screenshot({ path: `${process.env.TEST_CAPTURE_DIR}/cave-letter-desktop.png`, fullPage: true })
    }
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('after skipping the introduction a new cave shows at most two locked waiting companions', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `places-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const today = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal((await context.request.post(apiPath('/api/cave/onboarding/skip'), { data: { request_id: randomUUID() } })).status(), 200)
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    const waiting = page.getByRole('list', { name: '待相逢的同行者' })
    await waiting.waitFor()
    assert.equal(await waiting.getByRole('listitem').count(), 2)
    for (const pet of today.companions.pets.slice(0, 2)) await waiting.getByText(pet.name, { exact: true }).waitFor()
    assert.equal(await page.getByText(/^正在随行：/).count(), 0)
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('after three real successful sessions a user can invite the deer by keyboard and see it during a session', { timeout: 300_000 }, async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `deer-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const tokens = await (await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })).json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    for (let count = 0; count < 3; count += 1) {
      const start = await context.request.post(apiPath('/api/cave/sessions'), { data: { target_duration: 1, request_id: randomUUID() } })
      assert.equal(start.status(), 200)
      const session = await start.json()
      // Real elapsed time crosses the documented 80% threshold; no database or clock changes.
      await new Promise(resolve => setTimeout(resolve, 51_000))
      const settle = await context.request.post(apiPath(`/api/cave/sessions/${session.id}/settle`), { data: { early: false, request_id: randomUUID() } })
      assert.equal(settle.status(), 200)
      assert.equal((await settle.json()).status, 'completed')
    }
    const companions = await (await context.request.get(apiPath('/api/cave/companions'))).json()
    const deer = companions.pets.find(pet => pet.key === 'white_deer')
    assert.equal(deer.unlocked, true)
    assert.equal(companions.active_pet_key, null)
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/cave/companions')
    const card = page.getByRole('article').filter({ has: page.getByRole('heading', { name: deer.name, exact: true }) })
    const invite = card.getByRole('button', { name: '邀它随行', exact: true })
    await invite.focus()
    await page.keyboard.press('Enter')
    await card.getByRole('button', { name: '正在随行', exact: true }).waitFor()
    await page.getByRole('navigation', { name: '主导航' }).getByRole('link', { name: '洞府', exact: true }).click()
    await page.getByText(`正在随行：${deer.name}`, { exact: true }).waitFor()
    const start = await context.request.post(apiPath('/api/cave/sessions'), { data: { target_duration: 15, request_id: randomUUID() } })
    assert.equal(start.status(), 200)
    const session = await start.json()
    await page.goto(`/cave/session/${session.id}`)
    await page.getByText(`正在随行：${deer.name}`, { exact: true }).waitFor()
  } finally { await context.unrouteAll({ behavior: 'wait' }); await context.close(); await browser.close() }
})

test('a user can choose a duration, minimize and end early without completing the task', async () => {
  const browser = await chromium.launch({ headless: true })
  const context = await reviewContext(browser)
  try {
    const username = `session-${randomUUID().slice(0, 8)}`
    const password = randomUUID()
    await context.request.post(apiPath('/api/auth/register'), { data: { username, email: `${username}@example.com`, password } })
    const login = await context.request.post(apiPath('/api/auth/login'), { form: { username, password } })
    const tokens = await login.json()
    await context.setExtraHTTPHeaders({ Authorization: `Bearer ${tokens.access_token}` })
    const created = await context.request.post(apiPath('/api/todos/workbench/tasks'), { data: { title: '留住这件未完成的事', schedule: 'today', request_id: randomUUID() } })
    assert.equal(created.status(), 200)
    const page = await context.newPage()
    await page.goto('/login')
    await page.evaluate(tokens => { localStorage.setItem('token', tokens.access_token); localStorage.setItem('refreshToken', tokens.refresh_token) }, tokens)
    await page.goto('/')
    await page.getByRole('button', { name: /入定 15 分钟/ }).click()
    const draft = page.getByRole('dialog', { name: '落座入定' })
    await draft.waitFor()
    await draft.getByRole('button', { name: '60 分钟', exact: true }).click()
    assert.equal(await draft.getByRole('checkbox', { name: '完成后同时完成任务' }).isChecked(), true)
    await draft.getByRole('button', { name: '开始入定', exact: true }).click()
    await page.waitForURL(/\/cave\/session\//)
    await page.getByRole('heading', { name: '留住这件未完成的事' }).waitFor()
    assert.equal(await page.getByRole('button', { name: '收功', exact: true }).isEnabled(), false)
    await page.getByRole('button', { name: '最小化，继续浏览' }).click()
    await page.waitForURL('/')
    await page.getByRole('navigation', { name: '主导航' }).getByRole('link', { name: '待办', exact: true }).click()
    await page.waitForURL('/todos')
    await page.reload()
    const miniBar = page.getByRole('complementary', { name: '进行中的入定' })
    await miniBar.getByText('留住这件未完成的事', { exact: true }).waitFor()
    assert.match(await page.title(), /入定/)
    await miniBar.getByRole('link', { name: '回到入定', exact: true }).click()
    await page.getByRole('button', { name: '提前结束', exact: true }).click()
    await page.getByRole('button', { name: '结束并收好这段时间', exact: true }).click()
    await page.waitForURL(/\/cave\/return\//)
    await page.getByRole('heading', { name: '这一段，已收好' }).waitFor()
    const cave = await (await context.request.get(apiPath('/api/cave/today'))).json()
    assert.equal(cave.active_session, null)
    assert.equal(cave.primary_sign.title, '留住这件未完成的事')
  } finally {
    await context.unrouteAll({ behavior: 'wait' })
    await context.close()
    await browser.close()
  }
})
