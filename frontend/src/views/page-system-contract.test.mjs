import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import test from 'node:test'

const viewsDirectory = new URL('./', import.meta.url)
const source = (name) => readFile(new URL(name, viewsDirectory), 'utf8')

async function viewFiles() {
  return (await readdir(viewsDirectory)).filter((name) => name.endsWith('.vue'))
}

test('every view renders its load and error states through AppState', async () => {
  for (const file of await viewFiles()) {
    const content = await source(file)
    assert.doesNotMatch(
      content,
      /class="(?:loading-state|error-state)/,
      `${file} must render loading/error through AppState instead of page-local markup`,
    )
  }
})

test('the app bar owns the page title, so views do not repeat it', async () => {
  for (const file of await viewFiles()) {
    const content = await source(file)
    assert.doesNotMatch(
      content,
      /class="(?:page-title|history-title)"/,
      `${file} must not repeat the app bar title inside the page`,
    )
  }
})

test('the app bar exposes the single page heading', async () => {
  const header = await readFile(new URL('../components/layout/Header.vue', import.meta.url), 'utf8')

  assert.match(header, /<h1 class="page-title">/)
})
