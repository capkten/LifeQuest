"""Canonical Chinese content for system-generated cultivation records."""

REALM_LABELS = {
    "qi_refining": "炼气期",
    "foundation": "筑基期",
    "golden_core": "金丹期",
    "nascent_soul": "元婴期",
    "spirit_transformation": "化神期",
    "void_refining": "炼虚期",
    "body_combination": "合体期",
    "great_vehicle": "大乘期",
    "tribulation": "渡劫期",
    "ascended": "飞升境",
}

SOURCE_LABELS = {
    "task": "任务",
    "habit": "习惯",
    "goal": "目标",
    "checkin": "签到",
    "shop": "商店",
    "achievement": "成就",
    "other": "其他",
}

TODO_SOURCE_PREFIXES = {
    "task": "t",
    "habit": "h",
    "goal": "g",
}

# Keep named exports available for callers that need a source-specific catalog.
COIN_SOURCE_LABELS = SOURCE_LABELS
CULTIVATION_SOURCE_LABELS = SOURCE_LABELS


def source_label(source):
    source_value = getattr(source, "value", source)
    return SOURCE_LABELS.get(source_value, source_value)

WORLD_NODE_CATALOG = {
    "mortal-domain-1": {
        "name": "青云凡域",
        "description": "凡尘散修启程之地，记录最初的修行足迹。",
        "required_realm": None,
    },
    "mortal-domain-2": {
        "name": "灵台域",
        "description": "灵台初明之地，汇聚完整流派与初级秘境。",
        "required_realm": "foundation",
    },
    "mortal-domain-3": {
        "name": "紫府域",
        "description": "紫府洞开之地，传承高阶功法与专精构筑。",
        "required_realm": "foundation",
    },
    "mortal-domain-4": {
        "name": "天罡域",
        "description": "天罡星力交汇之地，宗门战争在此展开。",
        "required_realm": "foundation",
    },
    "mortal-domain-5": {
        "name": "玄冥域",
        "description": "玄冥法则沉降之地，通往灵界与高难试炼。",
        "required_realm": "foundation",
    },
    "mortal-domain-6": {
        "name": "太虚域",
        "description": "太虚空间变幻之地，连接星海与多域事件。",
        "required_realm": "foundation",
    },
    "mortal-domain-7": {
        "name": "九曜域",
        "description": "九曜星辉照临之地，承载顶级传承与宗门联盟。",
        "required_realm": "foundation",
    },
    "mortal-domain-8": {
        "name": "仙阙域",
        "description": "仙阙遗泽留存之地，指向仙道遗产与天劫路线。",
        "required_realm": "foundation",
    },
    "mortal-domain-9": {
        "name": "天门域",
        "description": "天门试炼终点之前的疆域，连接天道与飞升之路。",
        "required_realm": "foundation",
    },
}

_SECT_ENTRY_REALMS = {
    1: "foundation",
    2: "golden_core",
    3: "nascent_soul",
    4: "spirit_transformation",
    5: "void_refining",
    6: "body_combination",
    7: "great_vehicle",
    8: "tribulation",
    9: "tribulation",
}

_SECT_DEFINITIONS = (
    (1, (("赤霞门", "火行基础法"), ("白石观", "守正与护体"), ("云游盟", "散修资源和商路"), ("青木堂", "木行生息法"), ("铁羽寨", "铁羽护身术"), ("长风渡", "远行纳气法"), ("青岚剑阁", "青岚引气剑诀"), ("百草丹谷", "百草养元经"), ("玄甲门", "玄甲淬体诀"), ("无名庐", "无名养剑篇"))),
    (2, (("金河宗", "金水调息法"), ("伏龙山庄", "驭兽和山野任务"), ("归元观", "平衡和恢复"), ("清河院", "清河静水诀"), ("玄木谷", "玄木回春法"), ("逐日庄", "逐日行气术"), ("太虚剑宗", "太虚御剑篇"), ("灵枢丹宗", "灵枢回天术"), ("镇岳体宗", "镇岳金身"), ("观心台", "观心照影法"))),
    (3, (("星河门", "星象观测和远行"), ("紫霄府", "雷法基础和纪律"), ("百炼楼", "装备和资源管理"), ("流云阁", "流云观星术"), ("赤峰院", "赤峰炼火诀"), ("玄铁山庄", "玄铁锻体法"), ("紫府雷宗", "紫府天雷诀"), ("万兽山", "万兽通灵篇"), ("天工阁", "天工百巧录"), ("雷隐谷", "雷隐遁法"))),
    (4, (("天罡门", "正面战斗和守城"), ("玄门道院", "综合修行和讲学"), ("云海楼", "远程任务和信息"), ("破军府", "破军战意诀"), ("太一书院", "太一正心篇"), ("逐风殿", "逐风身法"), ("天罡战府", "天罡战体"), ("九宫阵宗", "九宫护界阵"), ("妙音楼", "妙音定心法"), ("归藏阵墟", "归藏九阵录"))),
    (5, (("玄冥宗", "阴阳调和"), ("丹霞宫", "高阶丹道"), ("天渊门", "深渊探索和耐久"), ("寒渊阁", "寒渊定魄法"), ("紫玉宫", "紫玉炼心诀"), ("万壑门", "万壑藏锋术"), ("幽冥殿", "幽冥借力法"), ("太乙丹宫", "太乙炼命术"), ("玄水灵宗", "玄水化生经"), ("黄泉客栈", "黄泉渡魂经"))),
    (6, (("太虚门", "空间行走"), ("万法宗", "多流派兼修"), ("归墟商盟", "资源交易和远征"), ("流光门", "流光遁空术"), ("太初院", "太初归元法"), ("万星商会", "万星聚财诀"), ("星海剑宫", "星海剑意"), ("万法书院", "万法推演录"), ("混元道场", "混元归一功"), ("虚极天", "虚极观界经"))),
    (7, (("九曜门", "九曜星力"), ("天机府", "预测和规划"), ("龙象门", "龙象护体"), ("星衍宫", "星衍推步法"), ("苍龙府", "苍龙护世诀"), ("玄策门", "玄策定谋术"), ("九曜神宗", "九曜神变"), ("天机阁", "天机演算术"), ("太古龙门", "太古龙血法"), ("无相天", "无相化形录"))),
    (8, (("仙阙宗", "仙阙正统法"), ("忘情门", "情绪和心境"), ("赤霄宫", "赤霄火云法"), ("清微宫", "清微养神法"), ("太阴府", "太阴照心诀"), ("观心宗", "观心明性篇"), ("仙阙道宫", "仙阙无垢经"), ("太上忘情宫", "太上忘情诀"), ("不死凰庭", "凤凰涅槃法"), ("斩情海", "斩情问道录"))),
    (9, (("天门宗", "天门正法"), ("昆仑宫", "昆仑镇世法"), ("无极门", "无极守一功"), ("万象宗", "万象归元法"), ("玄穹府", "玄穹镇天诀"), ("归一宫", "归一守道篇"), ("天门圣地", "天门开界术"), ("昆仑仙府", "昆仑万象经"), ("无极道宗", "无极混沌法"), ("无名天关", "无名渡劫法"))),
)

_SECT_KINDS = ("normal", "normal", "normal", "normal", "normal", "normal", "special", "special", "special", "hidden")

_TASK_PREFERENCE_LABELS = {
    "discipline-1": "纪律修行",
    "discipline-2": "专注修行",
    "discipline-3": "持久修行",
    "discipline-4": "探索历练",
    "discipline-5": "资源积累",
    "discipline-6": "团队协作",
    "discipline-7": "专精突破",
    "discipline-8": "高难试炼",
    "discipline-9": "传承研究",
    "discipline-10": "隐秘探索",
}

SECT_CATALOG = {
    f"sect-{star}-{kind}-{ordinal}": {
        "name": name,
        "description": f"{name}的修行传承与宗门事务。",
        "core_legacy": legacy,
        "kind": kind,
        "kind_label": {"normal": "普通宗门", "special": "特殊宗门", "hidden": "隐藏宗门"}[kind],
        "task_preference": f"discipline-{ordinal}",
        "task_preference_label": _TASK_PREFERENCE_LABELS[f"discipline-{ordinal}"],
        "entry_realm": _SECT_ENTRY_REALMS[star],
        "entry_realm_label": REALM_LABELS[_SECT_ENTRY_REALMS[star]],
        "trial_key": f"trial-{star}-{ordinal}",
        "world_node_key": f"mortal-domain-{star}",
    }
    for star, definitions in _SECT_DEFINITIONS
    for ordinal, ((name, legacy), kind) in enumerate(zip(definitions, _SECT_KINDS), 1)
}

TECHNIQUE_CATALOG = {
    "steady-breath": {
        "name": "凝息诀",
        "description": "调匀呼吸，凝聚灵气，稳步提升修行效率。",
        "technique_type": "mind",
        "technique_type_label": "心法",
        "required_realm": "qi_refining",
        "required_realm_label": REALM_LABELS["qi_refining"],
        "spirit_stone_cost": 10,
        "slot_count": 1,
    },
    "stone-channel": {
        "name": "磐石引脉术",
        "description": "借磐石之势淬炼经脉，夯实筑基根本。",
        "technique_type": "body",
        "technique_type_label": "炼体",
        "required_realm": "foundation",
        "required_realm_label": REALM_LABELS["foundation"],
        "spirit_stone_cost": 10,
        "slot_count": 1,
    },
    "golden-intent": {
        "name": "金丹明意诀",
        "description": "澄明心念，凝练金丹真意，稳固本命修为。",
        "technique_type": "main",
        "technique_type_label": "主修",
        "required_realm": "golden_core",
        "required_realm_label": REALM_LABELS["golden_core"],
        "spirit_stone_cost": 10,
        "slot_count": 1,
    },
}

NPC_ROLE_LABELS = {
    "ordinary disciple": "普通弟子",
    "sect master": "宗主",
    "transmission elder": "传功长老",
    "trial envoy": "入门使者",
}

EVENT_SUMMARY_LABELS = {
    "met": "与普通弟子相遇",
}
