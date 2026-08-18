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
  available: '可进入',
  completed: '已完成',
  cancelled: '已取消',
  current: '当前所在',
  failed: '失败',
  in_progress: '进行中',
  locked: '已锁定',
  left: '已离开',
  pending: '待处理',
  planning: '规划中',
  success: '成功',
  archived: '已归档',
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
  mind_state: '心境',
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

export const LOCK_REASON_LABELS = Object.freeze({
  FINAL_MINOR_STAGE_REQUIRED: '尚未达到当前境界的最终小境界阈值。',
  TRIBULATION_COOLDOWN_ACTIVE: '渡劫冷却中，请稍后再试。',
  ASCENDED: '已达飞升终点。',
})

export const DIFFICULTY_LABELS = Object.freeze({
  easy: '简单',
  medium: '中等',
  hard: '困难',
})

export const FREQUENCY_LABELS = Object.freeze({
  daily: '每日',
  weekly: '每周',
  monthly: '每月',
})

export const ACCOUNT_TYPE_LABELS = Object.freeze({
  cash: '现金',
  bank: '银行卡',
  credit: '信用卡',
  alipay: '支付宝',
  wechat: '微信',
  debt: '借贷',
  other: '其他',
})

export const PERIOD_LABELS = Object.freeze({
  week: '周',
  month: '月',
  year: '年',
  weekly: '每周',
  monthly: '每月',
  yearly: '每年',
})

export const SOURCE_LABELS = Object.freeze({
  task: '任务',
  habit: '习惯',
  goal: '目标',
  checkin: '签到',
  shop: '商城',
  achievement: '成就',
})

export const PROJECT_STATUS_LABELS = Object.freeze({
  planning: '规划中',
  active: '进行中',
  completed: '已完成',
  archived: '已归档',
})

export const TASK_STATUS_LABELS = Object.freeze({
  pending: '待开始',
  in_progress: '进行中',
  completed: '已完成',
  cancelled: '已取消',
})

export const ITEM_TYPE_LABELS = Object.freeze({
  consumable: '消耗品',
  gear: '装备',
  collectible: '收藏品',
  quest: '任务',
})

export const ACTION_TYPE_LABELS = Object.freeze({
  use: '使用',
  equip: '装备',
  discard: '丢弃',
  add: '添加',
  unequip: '卸下',
})

export const EXCHANGE_STATUS_LABELS = Object.freeze({
  pending: '处理中',
  completed: '已完成',
  cancelled: '已取消',
  refunded: '已退款',
})

export const TRANSACTION_TYPE_LABELS = Object.freeze({
  income: '收入',
  expense: '支出',
  transfer: '转账',
})

export const ERROR_MESSAGES = Object.freeze({
  TITLE_REQUIRED: '保存前请填写标题。',
  NOTEBOOK_REQUIRED: '请先选择笔记本。',
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
  LOCK_REASON_LABELS,
  DIFFICULTY_LABELS,
  FREQUENCY_LABELS,
  ACCOUNT_TYPE_LABELS,
  PERIOD_LABELS,
  SOURCE_LABELS,
  PROJECT_STATUS_LABELS,
  TASK_STATUS_LABELS,
  ITEM_TYPE_LABELS,
  ACTION_TYPE_LABELS,
  EXCHANGE_STATUS_LABELS,
  TRANSACTION_TYPE_LABELS,
  ERROR_MESSAGES,
}
