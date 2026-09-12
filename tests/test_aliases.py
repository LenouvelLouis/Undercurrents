from undercurrents.clustering import aliases


def test_no_title_appears_in_more_than_one_category():
    fix_text_keys = set(aliases.FIX_TEXT)
    merge_keys = set(aliases.MERGE)
    excluded = set(aliases.EXCLUDE)
    assert not (fix_text_keys & merge_keys)
    assert not (fix_text_keys & excluded)
    assert not (merge_keys & excluded)


def test_known_merge_alias_present():
    assert aliases.MERGE["Halcyon And On And On"] == "Halcyon + On + On"


def test_known_fix_text_aliases_present():
    assert aliases.FIX_TEXT["She Just Won’t Believe Me"] == "She Just Won't Believe Me"
    assert aliases.FIX_TEXT["Tomorrow’s Dust"] == "Tomorrow's Dust"


def test_known_excluded_titles_present():
    assert "" in aliases.EXCLUDE
    assert "Intro" in aliases.EXCLUDE
    assert "Aionwell Lab Intro" in aliases.EXCLUDE
    assert "Auto-Prog III" in aliases.EXCLUDE
