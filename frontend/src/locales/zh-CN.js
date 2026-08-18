export const REALM_LABELS = Object.freeze({
  qi_refining: '炼气期',
  foundation: '筑基期',
  golden_core: '金丹期',
  nascent_soul: '元婴期',
  spirit_transformation: '化神期',
  void_refining: '炼虚期',
  body_combination: '合体期',
  great_vehicle: '大乘期',
  tribulation: '渡劫期',
  ascended: '飞升境',
})

export const SECT_KIND_LABELS = Object.freeze({
  normal: '普通宗门',
  special: '特殊宗门',
  hidden: '隐藏宗门',
})

export const TECHNIQUE_TYPE_LABELS = Object.freeze({
  main: '主修',
  auxiliary: '辅修',
  mind: '心法',
  body: '炼体',
})

export const SLOT_TYPE_LABELS = Object.freeze({
  main: '主修',
  auxiliary: '辅修',
  mind: '心法',
  body: '身法',
})

export const TASK_PREFERENCE_LABELS = Object.freeze({
  'discipline-1': '纪律修行',
  'discipline-2': '专注修行',
  'discipline-3': '持久修行',
  'discipline-4': '探索历练',
  'discipline-5': '资源积累',
  'discipline-6': '团队协作',
  'discipline-7': '专精突破',
  'discipline-8': '高难试炼',
  'discipline-9': '传承研究',
  'discipline-10': '隐秘探索',
})

export const STATUS_LABELS = Object.freeze({
  active: '进行中',
  awaiting_messenger: '等待接引',
  awaiting_trial: '等待试炼',
  completed: '已完成',
  failed: '失败',
  locked: '已锁定',
  left: '已离开',
  pending: '待处理',
  success: '成功',
})

export const RESOURCE_LABELS = Object.freeze({
  coins: '金币',
  cultivation: '修为',
  spirit_stones: '灵石',
  immortal_stones: '仙石',
  merit: '功德',
  contribution: '宗门贡献',
  aptitude_points: '资质点',
  experience: '经验',
})

export const NPC_ROLE_LABELS = Object.freeze({
  'ordinary disciple': '普通弟子',
  'sect master': '宗主',
  'transmission elder': '传功长老',
  'trial envoy': '入门使者',
})

export const EVENT_SUMMARY_LABELS = Object.freeze({
  met: '与普通弟子相遇',
})

export const ERROR_MESSAGES = Object.freeze({
  'Task not found': '任务不存在。',
  'TECHNIQUE_NOT_FOUND:technique not found': '功法不存在。',
  'SLOT_CONFLICT:DUPLICATE_TECHNIQUE': '同一功法不能重复配置。',
  'SLOT_CONFLICT:OCCUPANCY': '功法占用的格子不匹配。',
  'SLOT_CONFLICT:CATEGORY': '功法类型不能混用。',
  'SLOT_CONFLICT:NON_CONTIGUOUS': '功法必须配置在连续格子中。',
  INVALID_SLOT_TYPE: '功法格子类型无效。',
})

export default {
  REALM_LABELS,
  SECT_KIND_LABELS,
  TECHNIQUE_TYPE_LABELS,
  SLOT_TYPE_LABELS,
  TASK_PREFERENCE_LABELS,
  STATUS_LABELS,
  RESOURCE_LABELS,
  NPC_ROLE_LABELS,
  EVENT_SUMMARY_LABELS,
  ERROR_MESSAGES,
}
