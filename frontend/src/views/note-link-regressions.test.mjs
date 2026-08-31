import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (name) => readFile(new URL(`./${name}`, import.meta.url), 'utf8')
const serviceSource = (name) => readFile(new URL(`../services/${name}`, import.meta.url), 'utf8')

test('note service exposes one explicit link boundary for all execution kinds', async () => {
  const noteService = await serviceSource('note.js')
  const todoService = await serviceSource('todo.js')
  const projectService = await serviceSource('project.js')

  assert.match(noteService, /getNoteLinks\s*\(/)
  assert.match(noteService, /linkNote\s*\(/)
  assert.match(noteService, /unlinkNote\s*\(/)
  assert.match(todoService, /getTaskNotes\s*\(/)
  assert.match(todoService, /getGoalNotes\s*\(/)
  assert.match(todoService, /linkTaskNote\s*\(/)
  assert.match(projectService, /getProjectNotes\s*\(/)
  assert.match(projectService, /linkProjectNote\s*\(/)
})

test('note editor renders link controls and preserves retryable link state', async () => {
  const editor = await source('NoteEditor.vue')

  assert.match(editor, /关联任务/)
  assert.match(editor, /关联项目/)
  assert.match(editor, /关联目标/)
  assert.match(editor, /getNoteLinks\(/)
  assert.match(editor, /linkNote\(/)
  assert.match(editor, /unlinkNote\(/)
  assert.match(editor, /重试.*关联|关联.*重试/s)
})

test('todo page exposes linked-note navigation for tasks and goals', async () => {
  const todos = await source('Todos.vue')

  assert.match(todos, /打开关联笔记/)
  assert.match(todos, /getTaskNotes\(/)
  assert.match(todos, /getGoalNotes\(/)
  assert.match(todos, /note.*links|linkedNotes|关联笔记/s)
})

test('project detail exposes linked-note navigation and a retryable load path', async () => {
  const project = await source('ProjectDetail.vue')

  assert.match(project, /打开关联笔记/)
  assert.match(project, /getProjectNotes\(/)
  assert.match(project, /关联笔记.*重试|重试.*关联笔记/s)
})

test('link controls do not silently disappear when the note request fails', async () => {
  const editor = await source('NoteEditor.vue')
  const todos = await source('Todos.vue')
  const project = await source('ProjectDetail.vue')

  for (const view of [editor, todos, project]) {
    assert.match(view, /error|Error|失败/)
  }
})
