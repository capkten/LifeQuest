import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import { getErrorMessage } from '../utils/errorMessage.js'

const srcDirectory = new URL('../', import.meta.url)

test('router includes authenticated cultivation routes', async () => {
  const source = await readFile(new URL('../router/index.js', import.meta.url), 'utf8')

  assert.match(source, /path: ['"]cultivation['"]/, 'cultivation route is missing')
  assert.match(source, /path: ['"]tribulations['"]/, 'tribulations route is missing')
  assert.match(source, /const cultivationRouteComponent\s*=\s*\(\)\s*=>\s*import\(/)
  assert.doesNotMatch(source, /component:\s*cultivationRouteComponent[\s\S]*undefined/)
})

test('todo page keeps the legacy reward fallback', async () => {
  const source = await readFile(new URL('./Todos.vue', import.meta.url), 'utf8')

  assert.match(source, /coins_reward/)
  assert.match(source, /exp_reward/)
  assert.match(source, /cultivation|修为/)
  assert.match(source, /cultivation_reward/)
})

test('mortal world is reachable and labeled consistently', async () => {
  const [sidebar, world] = await Promise.all([
    readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8'),
    readFile(new URL('./World.vue', import.meta.url), 'utf8'),
  ])

  assert.match(sidebar, /to="\/world"/)
  assert.match(sidebar, /凡界/)
  assert.doesNotMatch(sidebar, /cultivationUnlocked\s*&&\s*isAscended[^\n]*to="\/world"/)
  assert.match(world, /凡界地图/)
  assert.doesNotMatch(world, /仙界地图/)
})

test('cultivation overview exposes stable today and recent reward arrays', async () => {
  const schema = await readFile(new URL('../../../backend/app/schemas/cultivation.py', import.meta.url), 'utf8')

  assert.match(schema, /today:[\s\S]*default_factory=list/)
  assert.match(schema, /recent_rewards:[\s\S]*default_factory=list/)
})

test('cultivation service keeps endpoint paths in one module', async () => {
  const source = await readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8')
  const apiSource = await readFile(new URL('../services/api.js', import.meta.url), 'utf8')

  assert.match(source, /import\s+api\s+from\s+['"]\.\/api['"]/)
  assert.match(apiSource, /baseURL:\s*apiBaseUrl/)
  assert.match(source, /['"]\/cultivation\/overview['"]\)/)
  assert.match(source, /['"]\/cultivation\/world['"]\)/)
  assert.match(source, /['"]\/cultivation\/npcs['"]\)/)
  assert.match(source, /['"]\/cultivation\/tribulation\/preview['"](?:\)|,)/)
  assert.ok(source.includes("'/cultivation/tribulation/attempt'"))
  assert.doesNotMatch(source, /['"]\/api\/cultivation\//)
  assert.doesNotMatch(source, /final_probability|roll/)
  assert.match(source, /attemptTribulation\(\{\s*pill_count\s*\}\)/)
})

test('npc page exposes the authenticated meet entry and event timeline', async () => {
  const [service, page] = await Promise.all([
    readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8'),
    readFile(new URL('./Npcs.vue', import.meta.url), 'utf8'),
  ])

  assert.match(service, /meetNpc[\s\S]*npcs\/meet/)
  assert.match(service, /sect_key|sectKey/)
  assert.match(service, /population_index|populationIndex/)
  assert.match(page, /@submit\.prevent/)
  assert.match(page, /sect_key|sectKey/)
  assert.match(page, /population_index|populationIndex/)
  assert.match(page, /meetNpc/)
  assert.match(page, /events/)
})

test('tribulation page exposes transparent risk order and authoritative result states', async () => {
  const [page, probability, router] = await Promise.all([
    readFile(new URL('./Tribulations.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/cultivation/TribulationProbability.vue', import.meta.url), 'utf8'),
    readFile(new URL('../router/index.js', import.meta.url), 'utf8'),
  ])

  assert.match(router, /path: ['"]tribulations['"][\s\S]*import\(['"]\.\.\/views\/Tribulations\.vue['"]\)/)
  for (const label of ['当前境界', '失败损失', '准备度', '基础成功率', '渡劫丹加成', '最终成功率', '冷却']) {
    assert.match(page + probability, new RegExp(label))
  }
  assert.match(page, /pill_count/)
  assert.match(page + probability, /开始渡劫/)
  assert.match(page, /success|失败|成功/)
  assert.match(page, /cultivation|修为/)
  assert.match(probability, /cooldown_until/)
  assert.match(page, /requestId|sequence|AbortController|latest/i)
  assert.match(page, /skipErrorToast/)
  assert.match(page, /error\.value\s*=\s*null/)
  assert.match(page, /useCultivationStore/)
  assert.match(page, /cultivationStore\.refresh\(\)/)
  assert.match(page, /result\.value\s*=\s*await cultivationService\.attemptTribulation[\s\S]*await syncAndLoad\(\)/)
  assert.doesNotMatch(page, /if\s*\(result\.value\.success\)\s*await cultivationStore\.refresh\(\)/)
  assert.match(page, /async function syncAndLoad[\s\S]*try\s*\{\s*await cultivationStore\.refresh\(\)\s*\}\s*catch[\s\S]*await load\(\)/)
  assert.match(probability, /:disabled="[^"]*operationBusy/)
  assert.match(probability, /aria-live="polite"/)
})

test('cultivation error details from the backend map to actionable messages', () => {
  const details = [
    ['TECHNIQUE_REALM_REQUIRED:筑基', '筑基'],
    ['SLOT_REALM_REQUIRED:金丹', '金丹'],
    ['FINAL_MINOR_STAGE_REQUIRED', '最终小境界'],
    ['tribulation already complete', '已经完成'],
    ['tribulation cooldown active', '冷却'],
    ['tribulation requires final minor stage threshold', '最终小境界'],
  ]

  for (const [detail, expected] of details) {
    assert.match(getErrorMessage({ response: { data: { detail } } }), new RegExp(expected))
    assert.notEqual(getErrorMessage({ response: { data: { detail } } }), '操作失败，请重试。')
  }
})

test('tribulation attempt checks cooldown before availability', async () => {
  const source = await readFile(new URL('./Tribulations.vue', import.meta.url), 'utf8')

  assert.match(source, /if \(preview\.value\?\.cooldown_until\)[\s\S]*?return[\s\S]*?if \(!preview\.value\?\.available\)/)
})

test('settlements update visible deltas and obtain an authoritative overview', async () => {
  const source = await readFile(new URL('../stores/cultivation.js', import.meta.url), 'utf8')

  assert.match(source, /settlement\.cultivation/)
  assert.match(source, /settlement\.spirit_stones/)
  assert.match(source, /overview\.value\s*=\s*\{/)
  assert.match(source, /await refresh\(\)/)
  assert.doesNotMatch(source, /nextOverview\s*=\s*settlement\s*\|\|\s*settlement/)
})

test('realm progress derives its percentage from StageProgress thresholds', async () => {
  const source = await readFile(new URL('../components/cultivation/RealmProgress.vue', import.meta.url), 'utf8')

  assert.match(source, /current_threshold/)
  assert.match(source, /next_threshold/)
  assert.match(source, /remaining/)
  assert.doesNotMatch(source, /progress\.percent/)
  assert.match(source, /aria-valuemax="100"/)
})

test('cultivation shared states expose accessible stable contracts', async () => {
  const [statusBar, realmProgress, resourceSummary, rewardToast, probability, slots, mapNode, npcTimeline, styles] = await Promise.all([
    'components/cultivation/CultivationStatusBar.vue',
    'components/cultivation/RealmProgress.vue',
    'components/cultivation/ResourceSummary.vue',
    'components/cultivation/RewardToast.vue',
    'components/cultivation/TribulationProbability.vue',
    'components/cultivation/TechniqueSlotGrid.vue',
    'components/cultivation/MapNode.vue',
    'components/cultivation/NpcTimeline.vue',
    'styles/stitch-overrides.css',
  ].map((path) => readFile(new URL(path, srcDirectory), 'utf8')))

  assert.match(statusBar, /aria-live="polite"/)
  assert.match(realmProgress, /aria-valuenow/)
  assert.match(resourceSummary, /aria-labelledby="resource-summary-title"/)
  assert.match(rewardToast, /role="status"/)
  assert.match(rewardToast, /<Close\s*\/>/)
  assert.match(probability, /defineEmits\(\[[^\]]*'attempt'/)
  assert.match(probability, /attempting|submitting/)
  assert.match(probability, /:aria-busy="operationBusy"/)
  assert.match(probability, /const operationBusy = computed\(\(\) => props\.loading\s*\|\|\s*props\.attempting\s*\|\|\s*props\.submitting\)/)
  assert.match(probability, /<button[^>]+:disabled="[^"]*loading[^"\n]*operationBusy[^>]*"[^>]+@click="\$emit\('retry'\)"/)
  assert.match(probability, /<button[^>]+:disabled="[^"]*loading[^"]*operationBusy[^>]*"[^>]+@click="\$emit\('attempt'\)"/)
  assert.match(probability, /aria-live="polite"/)
  assert.match(styles, /cultivation-slot-grid[\s\S]*min-height/)
  assert.match(styles, /prefers-reduced-motion/)
  assert.match(slots, /error/)
  assert.match(slots, /暂无可用功法格子/)
  assert.match(slots, /:disabled="[^"]*(busy|loading)/)
  assert.match(mapNode, /locked/)
  assert.match(mapNode, /labelStatus/)
  assert.match(mapNode, /:disabled="isLocked"/)
  assert.match(npcTimeline, /fixed_core/)
  assert.match(npcTimeline, /recently_met/)
  assert.match(npcTimeline, /events/)
  assert.match(npcTimeline, /Array\.isArray/)
  assert.doesNotMatch(npcTimeline, /props\.npcs\.map/)
  assert.match(npcTimeline, /index\s*\+\s*1/)
  assert.match(npcTimeline, /关系事件记录|人物记录|人物信息待补充/)
  assert.match([mapNode, npcTimeline].join('\n'), /aria-label/)
})

test('world page has lock and selection semantics', async () => {
  const [source, mapNode] = await Promise.all([
    readFile(new URL('./World.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/cultivation/MapNode.vue', import.meta.url), 'utf8'),
  ])

  assert.match(source, /锁定|解锁条件/)
  assert.match(mapNode, /aria-selected/)
  assert.match(source, /MapNode/)
  assert.match(source, /required_realm/)
  assert.match(source, /sort_order/)
  assert.match(source, /completed/)
  assert.match(source, /ascended/)
  assert.match(source, /:disabled|locked/)
  assert.doesNotMatch(source, /node\.is_current|node\.status === ['"]current['"]|node\.completed/)
})

test('sidebar uses the explicit API ascended state', async () => {
  const sidebar = await readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8')
  const schema = await readFile(new URL('../../../backend/app/schemas/cultivation.py', import.meta.url), 'utf8')
  assert.match(sidebar, /cultivationOverview\.value\?\.ascended\s*===\s*true/)
  assert.match(schema, /ascended:\s*bool\s*=\s*False/)
})

test('npcs route exposes mortal disciples without ascended-only officials', async () => {
  const router = await readFile(new URL('../router/index.js', import.meta.url), 'utf8')
  const api = await readFile(new URL('../../../backend/app/api/cultivation.py', import.meta.url), 'utf8')
  const service = await readFile(new URL('../../../backend/app/services/cultivation.py', import.meta.url), 'utf8')
  assert.match(router, /path:\s*['"]npcs['"][\s\S]*component:/)
  assert.doesNotMatch(router, /path:\s*['"]npcs['"][\s\S]*requiresAscended:\s*true/)
  assert.match(router, /requiresAscended[\s\S]*cultivationStore\.loadOverview/)
  assert.match(api, /def npcs\([\s\S]*get_npcs\(current_user\.id\)/)
  assert.match(service, /profile\.realm_key == ASCENDED_REALM_KEY/)
  assert.match(service, /is_generated\.is_\(True\)/)
})

test('sidebar exposes mortal NPCs while reserving official label for ascended users', async () => {
  const sidebar = await readFile(new URL('../components/layout/Sidebar.vue', import.meta.url), 'utf8')

  assert.match(sidebar, /v-if="cultivationUnlocked" to="\/npcs"/)
  assert.match(sidebar, /isAscended \? ['"]仙官['"] : ['"]凡界 NPC['"]|['"]凡界 NPC['"]|isAscended.*仙官/)
  assert.doesNotMatch(sidebar, /v-if="cultivationUnlocked && isAscended" to="\/npcs"/)
})

test('sects page consumes server NPC relationship state and links to real records', async () => {
  const [page, service] = await Promise.all([
    readFile(new URL('./Sects.vue', import.meta.url), 'utf8'),
    readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8'),
  ])

  assert.match(service, /getNpcs\(\)/)
  assert.match(page, /getNpcs/)
  assert.match(page, /recently_met/)
  assert.match(page, /npc\.name|item\.name/)
  assert.match(page, /to="\/npcs"/)
  assert.doesNotMatch(page, /宗主|传功长老|试炼使者/)
})

test('cultivation state is cleared across auth identity changes', async () => {
  const auth = await readFile(new URL('../stores/auth.js', import.meta.url), 'utf8')
  const cultivation = await readFile(new URL('../stores/cultivation.js', import.meta.url), 'utf8')
  const api = await readFile(new URL('../services/api.js', import.meta.url), 'utf8')
  const session = await readFile(new URL('../services/authSession.js', import.meta.url), 'utf8')
  assert.match(cultivation, /function clear\(\)/)
  assert.match(cultivation, /overview\.value\s*=\s*null/)
  assert.match(cultivation, /error\.value\s*=\s*null/)
  assert.match(cultivation, /requestVersion/)
  assert.match(cultivation, /requestSequence|sequence/)
  assert.match(cultivation, /\+\+requestSequence|requestSequence\s*\+\+/)
  assert.match(auth, /useCultivationStore/)
  assert.match(auth, /cultivationStore\.clear\(\)/)
  assert.match(auth, /userData\.id|previousUserId|user\.value\?\.id/)
  assert.match(auth, /refreshAccessToken[\s\S]*logout\(\)/)
  assert.match(api, /invalidateAuthSession/)
  assert.doesNotMatch(api, /window\.location\.href\s*=\s*['"]\/login/)
  assert.match(session, /registerAuthCleanup/)
  assert.match(session, /localStorage\.removeItem\(['"]token['"]\)/)
})

test('recent rewards preserve descriptions before numeric fallback', async () => {
  const source = await readFile(new URL('./Cultivation.vue', import.meta.url), 'utf8')

  assert.match(source, /reward\.description\s*\|\|\s*reward\.detail\s*\|\|\s*\(\s*reward\.cultivation\s*\?\s*`\+\$\{reward\.cultivation\}/)
  assert.doesNotMatch(source, /reward\.description\s*\|\|\s*reward\.detail\s*\|\|\s*reward\.cultivation\s*\?/)
})

test('static world detail does not claim expansion state', async () => {
  const source = await readFile(new URL('./World.vue', import.meta.url), 'utf8')

  assert.doesNotMatch(source, /<article[^>]+aria-expanded/)
  assert.doesNotMatch(source, /<p[^>]+aria-expanded/)
})

test('sect page exposes comparison filters', async () => {
  const source = await readFile(new URL('./Sects.vue', import.meta.url), 'utf8')

  assert.match(source, /星级/)
  assert.match(source, /特殊|隐藏/)
  assert.match(source, /比较/)
})

test('sects page cannot let an older filter response overwrite the latest one', async () => {
  const source = await readFile(new URL('./Sects.vue', import.meta.url), 'utf8')

  assert.match(source, /createSequencedRequest/)
  assert.match(source, /requestSequence/)
})

test('technique page shows price and conflict without relying on color', async () => {
  const source = await readFile(new URL('./Techniques.vue', import.meta.url), 'utf8')

  assert.match(source, /需要境界/)
  assert.match(source, /灵石/)
  assert.match(source, /冲突/)
  assert.match(source, /TechniqueSlotGrid/)
})

test('task 12 exposes technique learning and tribulation lock states', async () => {
  const [techniques, component, service] = await Promise.all([
    readFile(new URL('./Techniques.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/cultivation/TribulationProbability.vue', import.meta.url), 'utf8'),
    readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8'),
  ])

  assert.match(service, /learnTechnique\(/)
  assert.match(techniques, /!technique\.learned[\s\S]*学习|学习[\s\S]*learnTechnique/)
  assert.match(techniques, /getErrorMessage/)
  assert.match(component, /preview\.available\s*===\s*false|!preview\.available/)
  assert.match(component, /lock_reason/)
  assert.doesNotMatch(component, /开始渡劫[\s\S]*v-if/)
})

test('task 7 fixes preserve authoritative state and honest empty/locked states', async () => {
  const [techniques, sects, slots] = await Promise.all([
    readFile(new URL('./Techniques.vue', import.meta.url), 'utf8'),
    readFile(new URL('./Sects.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/cultivation/TechniqueSlotGrid.vue', import.meta.url), 'utf8'),
  ])

  assert.match(techniques, /techniques\.value\s*=\s*response\?\.techniques\s*\|\|\s*\[\]/)
  assert.match(techniques, /purchaseSlot\([^)]*slot_type/)
  assert.match(techniques, /technique\.learned/)
  assert.match(techniques, /slot_count/)
  assert.match(techniques, /conflict/)
  assert.match(techniques, /暂无已学功法|功法库为空|empty/i)
  assert.match(sects, /can_join/)
  assert.match(sects, /visible === true/)
  assert.doesNotMatch(sects, /concat\(\[['"]宗主|传功长老|试炼使者/)
  assert.match(slots, /visibleSlots/)
})

test('technique confirmation uses authoritative server preview values', async () => {
  const source = await readFile(new URL('./Techniques.vue', import.meta.url), 'utf8')

  assert.match(source, /spirit_stones/)
  assert.match(source, /next_slot_purchases/)
  assert.match(source, /post_purchase_balance/)
  assert.doesNotMatch(source, /const prices\s*=/)
  assert.doesNotMatch(source, /服务器返回后显示/)
})

test('technique purchase preview locks unavailable purchases with an actionable error', async () => {
  const source = await readFile(new URL('./Techniques.vue', import.meta.url), 'utf8')

  assert.match(source, /can_purchase\s*===\s*false/)
  assert.match(source, /境界不足|灵石不足|无法购买|不可购买/)
  assert.match(source, /error\.value\s*=\s*new Error|error\.value\s*=\s*['"`]/)
})

test('sect joining follows server eligibility fields', async () => {
  const source = await readFile(new URL('./Sects.vue', import.meta.url), 'utf8')

  assert.match(source, /sect\.visible !== true/)
  assert.match(source, /sect\.can_join !== true/)
  assert.match(source, /sect\.realm_confirmed === true/)
})

test('sect prerequisites are exposed in server order and hidden sects stay unavailable', async () => {
  const [source, service] = await Promise.all([
    readFile(new URL('./Sects.vue', import.meta.url), 'utf8'),
    readFile(new URL('../services/cultivation.js', import.meta.url), 'utf8'),
  ])

  assert.match(service, /messenger\/contact/)
  assert.match(service, /trial\/complete/)
  assert.match(source, /messenger_contacted/)
  assert.match(source, /trial_confirmed/)
  assert.match(source, /contactMessenger/)
  assert.match(source, /completeTrial/)
  assert.match(source, /sect\.visible !== true/)
  assert.match(source, /sect\.can_join !== true/)
})

test('multi-slot techniques assign contiguous purchased slots or show insufficient state', async () => {
  const source = await readFile(new URL('./Techniques.vue', import.meta.url), 'utf8')

  assert.match(source, /slot_count/)
  assert.match(source, /slice\([^)]*slot_count/)
  assert.match(source, /连续|不足|insufficient/i)
  assert.match(source, /updateLoadout\(assignments\)/)
})

test('technique locks explain realm, stone, slot and purchase prerequisites', async () => {
  const source = await readFile(new URL('./Techniques.vue', import.meta.url), 'utf8')

  assert.match(source, /useToast\(/)
  assert.match(source, /function explainBlocked\(/)
  assert.match(source, /aria-disabled/)
  assert.match(source, /境界不足|灵石不足|连续格子不足|购买/)
})

test('tribulation locks explain prerequisites and cooldown without native disabled', async () => {
  const [page, probability] = await Promise.all([
    readFile(new URL('./Tribulations.vue', import.meta.url), 'utf8'),
    readFile(new URL('../components/cultivation/TribulationProbability.vue', import.meta.url), 'utf8'),
  ])

  assert.match(page, /useToast\(/)
  assert.match(page, /function explainBlocked\(/)
  assert.match(page + probability, /aria-disabled/)
  assert.match(page, /冷却|渡劫前置条件/)
  assert.match(probability, /aria-disabled/)
  assert.match(probability, /lockReasonLabel|cooldownLabel/)
})
