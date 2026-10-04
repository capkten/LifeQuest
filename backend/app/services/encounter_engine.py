import random
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cultivation_retreat import EncounterEvent

DEFAULT_ENCOUNTERS = [
    # 凡品 (Common) - 练气及以上 (min_realm_level=1)
    {
        "id": "enc_epiphany_01",
        "title": "灵台空明",
        "story_text": "你在入定中忽觉百骸舒畅，往日百思不解的现实疑难迎刃而解，灵台一片清明。",
        "rarity": "common",
        "min_realm_level": 1,
        "reward_type": "exp",
        "reward_payload": {"exp": 50},
        "weight": 100,
    },
    {
        "id": "enc_lingzhi_01",
        "title": "幽谷灵芝",
        "story_text": "闭关吐纳之际，偶感室外灵气氤氲，竟在窗台缝隙处见一株微光初绽的百年灵芝。",
        "rarity": "common",
        "min_realm_level": 1,
        "reward_type": "coins",
        "reward_payload": {"coins": 60},
        "weight": 100,
    },
    {
        "id": "enc_tea_dao_01",
        "title": "清心茶韵",
        "story_text": "出关煮水烹茗，茶香袅袅中窥见一丝天地至理，心境澄澈无尘。",
        "rarity": "common",
        "min_realm_level": 1,
        "reward_type": "exp",
        "reward_payload": {"exp": 75},
        "weight": 90,
    },
    # 灵品 (Rare) - 练气/筑基 (min_realm_level=1 或 2)
    {
        "id": "enc_wandering_taoist_01",
        "title": "游方道人",
        "story_text": "一位闲云野鹤般的游方道士路过洞府，见你静坐勤勉，赞许之余赠予一枚温玉与指点心得。",
        "rarity": "rare",
        "min_realm_level": 1,
        "reward_type": "exp_and_coins",
        "reward_payload": {"exp": 120, "coins": 100},
        "weight": 50,
    },
    {
        "id": "enc_ancient_manual_fragment",
        "title": "残经一页",
        "story_text": "微风翻动案头旧书，夹层中竟滑落一张泛黄的古代修行札记，字字珠玑。",
        "rarity": "rare",
        "min_realm_level": 1,
        "reward_type": "exp",
        "reward_payload": {"exp": 180},
        "weight": 45,
    },
    {
        "id": "enc_spirit_beast_visit",
        "title": "白鹿衔芝",
        "story_text": "一只周身萦绕微光的灵鹿悄然驻足檐下，放下灵果后踏云而去，留下满室清香。",
        "rarity": "rare",
        "min_realm_level": 2,
        "reward_type": "coins",
        "reward_payload": {"coins": 200},
        "weight": 40,
    },
    # 玄品 (Epic) - 筑基/金丹 (min_realm_level=2 或 3)
    {
        "id": "enc_celestial_alignment",
        "title": "太虚星坠",
        "story_text": "夜观星象，偶遇九星连珠之奇观，星辉垂照贯通顶门，真元暴涨，犹如脱胎换骨。",
        "rarity": "epic",
        "min_realm_level": 2,
        "reward_type": "exp_and_coins",
        "reward_payload": {"exp": 300, "coins": 300},
        "weight": 20,
    },
    {
        "id": "enc_sword_intent_echo",
        "title": "古剑遗意",
        "story_text": "冥想深处听闻龙吟剑鸣，上古剑修遗留的一抹不灭剑意与你的专注之心共鸣激荡。",
        "rarity": "epic",
        "min_realm_level": 2,
        "reward_type": "exp",
        "reward_payload": {"exp": 450},
        "weight": 15,
    },
    # 仙品 (Legendary) - 高阶机缘 (min_realm_level=3)
    {
        "id": "enc_immortal_inheritance",
        "title": "仙凡同契",
        "story_text": "大道无形，专注自明。虚空中降下一缕太古仙尊的垂青灵光，赐下无上造化机缘！",
        "rarity": "legendary",
        "min_realm_level": 3,
        "reward_type": "exp_and_coins",
        "reward_payload": {"exp": 888, "coins": 888},
        "weight": 5,
    },
]


def calculate_encounter_probability(duration_minutes: int, streak_days: int) -> float:
    """
    Calculate probability of triggering a random encounter:
    Base: 0.15
    Duration: +0.05 per 15 full minutes
    Streak: +0.01 per day (max 0.10)
    Bounded within [0.10, 0.60]
    """
    base = 0.15
    dur = max(0, duration_minutes)
    stk = max(0, streak_days)

    duration_bonus = (dur // 15) * 0.05
    streak_bonus = min(0.10, stk * 0.01)

    prob = base + duration_bonus + streak_bonus
    prob = max(0.10, min(0.60, prob))
    return round(prob, 2)


class EncounterEngine:
    @staticmethod
    def seed_events(db: Session) -> None:
        """Seed default encounter events if not already present."""
        existing_ids = {e.id for e in db.query(EncounterEvent.id).all()}
        new_events = []
        for item in DEFAULT_ENCOUNTERS:
            if item["id"] not in existing_ids:
                new_events.append(EncounterEvent(**item))

        if new_events:
            db.add_all(new_events)
            db.commit()

    @staticmethod
    def roll_encounter(
        db: Session,
        user_id: Optional[str],
        realm_level: int = 1,
        duration_minutes: int = 25,
        streak_days: int = 0,
        force_hit: bool = False,
    ) -> Optional[EncounterEvent]:
        """
        Determine if a random encounter occurs and pick an eligible event.
        Filters by min_realm_level and picks by weighted random choice.
        """
        prob = calculate_encounter_probability(duration_minutes, streak_days)
        hit = force_hit or (random.random() <= prob)
        if not hit:
            return None

        candidates = (
            db.query(EncounterEvent)
            .filter(EncounterEvent.min_realm_level <= max(1, realm_level))
            .all()
        )
        if not candidates:
            return None

        weights = [max(1, c.weight) for c in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]
