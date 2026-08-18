import re


def test_system_catalog_has_chinese_world_and_technique_content():
    from app.services.content_catalog import TECHNIQUE_CATALOG, WORLD_NODE_CATALOG

    assert WORLD_NODE_CATALOG["mortal-domain-1"]["name"] == "青云凡域"
    assert TECHNIQUE_CATALOG["steady-breath"]["name"] == "凝息诀"
    assert TECHNIQUE_CATALOG["steady-breath"]["description"]


def test_catalog_covers_every_generated_content_key():
    from app.services.content_catalog import (
        EVENT_SUMMARY_LABELS,
        NPC_ROLE_LABELS,
        REALM_LABELS,
        SECT_CATALOG,
        TECHNIQUE_CATALOG,
        WORLD_NODE_CATALOG,
    )

    assert set(WORLD_NODE_CATALOG) == {f"mortal-domain-{index}" for index in range(1, 10)}
    expected_sects = {
        f"sect-{star}-{kind}-{ordinal}"
        for star in range(1, 10)
        for kind, ordinals in (("normal", range(1, 7)), ("special", range(7, 10)), ("hidden", (10,)))
        for ordinal in ordinals
    }
    assert set(SECT_CATALOG) == expected_sects
    assert set(TECHNIQUE_CATALOG) == {"steady-breath", "stone-channel", "golden-intent"}
    assert set(REALM_LABELS) == {
        "qi_refining",
        "foundation",
        "golden_core",
        "nascent_soul",
        "spirit_transformation",
        "void_refining",
        "body_combination",
        "great_vehicle",
        "tribulation",
        "ascended",
    }
    assert set(NPC_ROLE_LABELS) >= {"ordinary disciple", "sect master", "transmission elder", "trial envoy"}
    assert EVENT_SUMMARY_LABELS["met"]

    for catalog in (WORLD_NODE_CATALOG, SECT_CATALOG, TECHNIQUE_CATALOG):
        for content in catalog.values():
            for field in ("name", "description", "core_legacy"):
                if field in content:
                    assert not re.search(r"[A-Za-z]", content[field])


def test_sect_task_preference_labels_follow_stable_preference_keys():
    from app.services.content_catalog import SECT_CATALOG

    expected_labels = {
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

    for sect in SECT_CATALOG.values():
        assert sect["task_preference_label"] == expected_labels[sect["task_preference"]]
