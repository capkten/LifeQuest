import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

test('immortal routes and screens consume server-authoritative state', async () => {
  const [router, service, world, activities, officials] = await Promise.all([
    readFile(new URL('../router/index.js', import.meta.url), 'utf8'),
    readFile(new URL('../services/immortal.js', import.meta.url), 'utf8'),
    readFile(new URL('./ImmortalWorld.vue', import.meta.url), 'utf8'),
    readFile(new URL('./ImmortalActivities.vue', import.meta.url), 'utf8'),
    readFile(new URL('./ImmortalOfficials.vue', import.meta.url), 'utf8'),
  ])
  assert.match(router, /requiresAscended: true/)
  assert.match(service, /\/immortal\/overview/)
  assert.match(service, /\/immortal\/activities\/run/)
  assert.match(service, /\/immortal\/stage\/advance/)
  assert.match(service, /\/immortal\/officials\/commission/)
  assert.match(world, /overview\.essence/)
  assert.match(world, /advanceStage/)
  assert.match(activities, /running/)
  assert.match(officials, /overview\.officials/)
})
