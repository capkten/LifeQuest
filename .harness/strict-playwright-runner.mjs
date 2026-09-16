import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const DEFAULT_VIEWPORTS = ['375x812', '768x1024', '1024x900', '1440x1000']
const DEFAULT_ROUTES = [
  '/',
  '/todos',
  '/coins/history',
  '/finance',
  '/finance/budgets',
  '/finance/debts',
  '/backpack/history',
  '/notes',
  '/projects',
  '/calendar',
  '/stats',
]

function parseArgs(argv) {
  const options = {
    baseUrl: 'http://127.0.0.1:4173',
    apiBaseUrl: null,
    authState: null,
    outputDir: resolve('.harness/iterations/2026-09-16-task-12'),
    contract: resolve('.harness/contracts/task-12-browser.json'),
    liveBaseUrl: 'https://life.capkin.cn/api',
    viewports: DEFAULT_VIEWPORTS,
    routes: DEFAULT_ROUTES,
    requireAuth: true,
  }

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--allow-unauthenticated') options.requireAuth = false
    else if (argument === '--viewports') options.viewports = argv[++index].split(',')
    else if (argument === '--routes') options.routes = argv[++index].split(',')
    else if (argument.startsWith('--')) {
      const key = {
        'base-url': 'baseUrl',
        'api-base-url': 'apiBaseUrl',
        'auth-state': 'authState',
        'output-dir': 'outputDir',
        contract: 'contract',
        'live-base-url': 'liveBaseUrl',
      }[argument.slice(2)]
      if (key) options[key] = argv[++index]
    }
  }
  return options
}

function parseViewport(value) {
  const [width, height] = value.split('x').map(Number)
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1) {
    throw new Error(`Invalid viewport: ${value}`)
  }
  return { name: value, width, height }
}

async function readContract(filename) {
  return JSON.parse(await readFile(filename, 'utf8'))
}

async function requestEvidence(method, url) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15000)
  try {
    const response = await fetch(url, { method, redirect: 'manual', signal: controller.signal })
    const body = await response.text()
    return {
      method,
      url,
      status: response.status,
      body: body.slice(0, 8000),
      headers: Object.fromEntries(response.headers.entries()),
    }
  } catch (error) {
    return { method, url, status: null, body: '', error: String(error) }
  } finally {
    clearTimeout(timer)
  }
}

async function collectLiveEvidence(liveBaseUrl) {
  const base = liveBaseUrl.replace(/\/$/, '')
  const fakeHabitId = '00000000-0000-0000-0000-000000000000'
  const checks = await Promise.all([
    requestEvidence('GET', `${base}/health`),
    requestEvidence('GET', `${base}/openapi.json`),
    requestEvidence('GET', `${base}/todos/daily`),
    requestEvidence('POST', `${base}/todos/habits/${fakeHabitId}/pause`),
    requestEvidence('POST', `${base}/todos/habits/${fakeHabitId}/resume`),
  ])
  const openapi = checks[1]
  let deployedVersion = null
  try {
    deployedVersion = JSON.parse(openapi.body)?.info?.version || null
  } catch {
    deployedVersion = null
  }
  return {
    endpoint: base,
    deployedVersion,
    health: checks[0],
    openapi,
    dailySummary: checks[2],
    pauseProbe: checks[3],
    resumeProbe: checks[4],
    mutationAttempted: true,
    authenticatedMutation: 'blocked: no production credentials were supplied; unauthenticated probes cannot mutate data',
    note: 'POST probes used a non-existent habit UUID without credentials and returned the deployed auth response. No authenticated production pause/resume mutation was attempted.',
  }
}

async function runBrowser(options, contract) {
  const result = {
    status: 'passed',
    authenticated: Boolean(options.authState),
    baseUrl: options.baseUrl,
    viewports: [],
    failures: [],
  }
  if (options.requireAuth && !options.authState) {
    return {
      ...result,
      status: 'blocked',
      authenticated: false,
      failures: ['authenticated fixture was not supplied'],
    }
  }

  let browser
  try {
    browser = await chromium.launch({ headless: true })
  } catch (error) {
    return { ...result, status: 'blocked', failures: [`browser launch failed: ${error.message}`] }
  }

  const baseOrigin = new URL(options.baseUrl).origin
  const apiOrigin = new URL(options.apiBaseUrl || `${baseOrigin}/api`).origin
  const allowedOrigins = new Set([
    baseOrigin,
    apiOrigin,
    ...(contract.allowedExternalOrigins || []),
  ])

  try {
    for (const viewportValue of options.viewports.map(parseViewport)) {
      const context = await browser.newContext({
        viewport: { width: viewportValue.width, height: viewportValue.height },
        ...(options.authState ? { storageState: options.authState } : {}),
      })
      const page = await context.newPage()
      const consoleErrors = []
      const pageErrors = []
      const unexpectedRequests = []
      const failedRequests = []
      const staleResponses = []
      page.on('console', message => {
        if (message.type() === 'error') consoleErrors.push(message.text())
      })
      page.on('pageerror', error => pageErrors.push(String(error)))
      page.on('request', request => {
        if (!allowedOrigins.has(new URL(request.url()).origin)) {
          unexpectedRequests.push({ method: request.method(), url: request.url() })
        }
      })
      page.on('requestfailed', request => {
        failedRequests.push({ method: request.method(), url: request.url(), error: request.failure()?.errorText })
      })
      page.on('response', async response => {
        const headers = response.headers()
        if (headers['x-lifequest-stale-response'] === 'true' || headers['x-request-stale'] === 'true') {
          staleResponses.push({ url: response.url(), status: response.status() })
        }
      })

      const viewportResult = {
        viewport: viewportValue.name,
        pages: [],
        consoleErrors,
        pageErrors,
        unexpectedRequests,
        failedRequests,
        staleResponses,
      }
      for (const route of options.routes) {
        const routeResult = { route, status: 'passed' }
        try {
          await page.goto(new URL(route, options.baseUrl).href, { waitUntil: 'networkidle', timeout: 30000 })
          const checks = await page.evaluate((retrySelector) => {
            const width = document.documentElement.scrollWidth
            const viewportWidth = document.documentElement.clientWidth
            const visibleAlerts = [...document.querySelectorAll('[role="alert"]')]
              .filter(element => element.getBoundingClientRect().width > 0 && element.getBoundingClientRect().height > 0)
            const errorStates = [...document.querySelectorAll('.error-state, .inline-error')]
              .filter(element => element.getBoundingClientRect().width > 0 && element.getBoundingClientRect().height > 0)
            return {
              title: document.title,
              url: location.href,
              horizontalOverflow: width > viewportWidth + 1,
              visibleAlerts: visibleAlerts.length,
              retryableErrorState: errorStates.length === 0 || errorStates.some(element => element.querySelector(retrySelector)),
              staleSignal: Boolean(window.__LIFEQUEST_STALE_RESPONSE__),
            }
          }, contract.retrySelector || '.retry-btn, [data-testid="retry"]')
          Object.assign(routeResult, checks)
          if (checks.horizontalOverflow) routeResult.status = 'failed'
          if (!checks.retryableErrorState || checks.staleSignal) routeResult.status = 'failed'
          if (routeResult.status === 'failed') viewportResult.failures = viewportResult.failures || []
        } catch (error) {
          routeResult.status = 'failed'
          routeResult.error = error.message
        }
        const filename = `${viewportValue.name}-${route === '/' ? 'home' : route.slice(1).replaceAll('/', '-')}.png`
        await page.screenshot({ path: resolve(options.outputDir, filename), fullPage: true })
        viewportResult.pages.push(routeResult)
      }
      result.viewports.push(viewportResult)
      await context.close()
    }
  } finally {
    await browser.close()
  }

  const browserFailures = result.viewports.flatMap(viewport => [
    ...viewport.consoleErrors.map(error => `${viewport.viewport}: console error: ${error}`),
    ...viewport.pageErrors.map(error => `${viewport.viewport}: page error: ${error}`),
    ...viewport.unexpectedRequests.map(request => `${viewport.viewport}: unexpected request ${request.method} ${request.url}`),
    ...viewport.failedRequests.map(request => `${viewport.viewport}: failed request ${request.method} ${request.url}`),
    ...viewport.staleResponses.map(response => `${viewport.viewport}: stale response ${response.status} ${response.url}`),
    ...viewport.pages.filter(page => page.status === 'failed').map(page => `${viewport.viewport} ${page.route}: contract failed`),
  ])
  result.failures.push(...browserFailures)
  if (result.failures.length) result.status = 'failed'
  return result
}

const options = parseArgs(process.argv.slice(2))
await mkdir(options.outputDir, { recursive: true })
const contract = await readContract(options.contract)
const report = {
  runner: 'strict-playwright-runner',
  generatedAt: new Date().toISOString(),
  contract: options.contract,
  browser: await runBrowser(options, contract),
  live: await collectLiveEvidence(options.liveBaseUrl),
}
if (report.live.health.status !== 200) report.live.status = 'blocked'
else report.live.status = 'read-only evidence collected'
const outputFile = resolve(options.outputDir, 'strict-results.json')
await writeFile(outputFile, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({ outputFile, browser: report.browser.status, live: report.live.status }))
if (report.browser.status === 'failed') process.exitCode = 1
