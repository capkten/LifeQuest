import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const viewsDirectory = new URL('./', import.meta.url)

test('notes discovery controls use readable Chinese labels', async () => {
  const source = await readFile(new URL('./Notes.vue', viewsDirectory), 'utf8')

  assert.match(source, /aria-label="\u6392\u5e8f"/)
  assert.match(source, />\u6700\u8fd1\u6253\u5f00<\/option>/)
  assert.match(source, />\u6700\u8fd1\u66f4\u65b0<\/option>/)
  assert.match(source, /aria-label="\u7b14\u8bb0\u672c\u7b5b\u9009"/)
  assert.doesNotMatch(source, /\u93ba\u6391\u7c2d|\u93c8\u5100\u677f\u621a\u5f48\u6d93\u5bee/)
})

test('shop search overrides the desktop flex basis on mobile', async () => {
  const source = await readFile(new URL('./Shop.vue', viewsDirectory), 'utf8')

  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search \{[\s\S]*?flex: 0 0 44px[\s\S]*?height: 44px/)
  assert.match(source, /@media \(max-width: 767px\) \{[\s\S]*?\.shop-search input \{[\s\S]*?height: 100%/)
})
