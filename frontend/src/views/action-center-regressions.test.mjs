import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { useActionCenter } from '../composables/useActionCenter.js'

const task = {
  kind: 'task',
  id: 'task-1',
  title: '完成计划',
  action: 'complete',
  completed: false,
}

function actionCenterPayload(title = task.title) {
  return {
    date: '2026-08-31',
    timezone: 'Asia/Shanghai',
    summary: {
      open_count: 1,
      overdue_count: 0,
      completed_count: 0,
      habit_due_count: 0,
      habit_completed_count: 0,
    },
    sections: {
      overdue: [],
      today: [{ ...task, title }],
      habits: [],
      calendar: [],
    },
    next_action: { ...task, title },
  }
}

function deferred() {
  let resolve
  const promise = new Promise((res) => { resolve = res })
  return { promise, resolve }
}

test('action center preserves the last successful data when refresh fails', async () => {
  let loadCount = 0
  const controller = useActionCenter({
    fetchActionCenter: async () => {
      loadCount += 1
      if (loadCount === 1) return actionCenterPayload('首次加载')
      throw new Error('network offline')
    },
  })

  await controller.load()
  await assert.rejects(controller.load(), /network offline/)

  assert.equal(controller.data.value.sections.today[0].title, '首次加载')
  assert.equal(controller.error.value.message, 'network offline')
  assert.equal(controller.loading.value, false)
})

test('action center submits one completion request for duplicate clicks', async () => {
  const completion = deferred()
  let completionCalls = 0
  const controller = useActionCenter({
    fetchActionCenter: async () => actionCenterPayload(),
    completeTask: async () => {
      completionCalls += 1
      await completion.promise
      return { id: task.id }
    },
  })

  const first = controller.complete(task)
  const second = controller.complete(task)
  assert.equal(await second, null)
  assert.equal(completionCalls, 1)

  completion.resolve()
  await first
  assert.equal(controller.completingKey.value, null)
})

test('action center passes the recurring occurrence date to task completion', async () => {
  const occurrenceTask = { ...task, occurrence_date: '2026-08-30' }
  const completionArgs = []
  const controller = useActionCenter({
    fetchActionCenter: async () => ({
      ...actionCenterPayload(),
      sections: { overdue: [occurrenceTask], today: [], habits: [], calendar: [] },
      next_action: occurrenceTask,
    }),
    completeTask: async (...args) => {
      completionArgs.push(args)
      return { id: task.id }
    },
  })

  await controller.complete(occurrenceTask)

  assert.deepEqual(completionArgs, [['task-1', '2026-08-30']])
})

test('home uses the action center instead of a second daily summary request', async () => {
  const source = await readFile(new URL('./Home.vue', import.meta.url), 'utf8')

  assert.match(source, /TodayActionCenter/)
  assert.match(source, /useActionCenter/)
  assert.doesNotMatch(source, /todoService\.getDailySummary\(\)/)
})

test('action center keys recurring occurrences by date', async () => {
  const source = await readFile(new URL('../components/home/TodayActionCenter.vue', import.meta.url), 'utf8')

  assert.match(source, /function itemKey\(item\)[\s\S]*item\.occurrence_date/)
})
