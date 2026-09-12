from undercurrents.orchestrator.intent import ClassifiedIntent, Intent, classify

KNOWN_SONGS = ["Elephant", "Feels Like We Only Go Backwards", "Nangs"]


def test_classify_predict_intent_english():
    result = classify("What will they play next show?", KNOWN_SONGS)
    assert result.intent == Intent.PREDICT


def test_classify_predict_intent_french():
    result = classify("Que vont-ils probablement jouer au prochain concert ?", KNOWN_SONGS)
    assert result.intent == Intent.PREDICT


def test_classify_cluster_intent():
    result = classify("Tell me about the Currents tour cluster", KNOWN_SONGS)
    assert result.intent == Intent.CLUSTER


def test_classify_fact_intent_from_keyword():
    result = classify("How many shows have they played?", KNOWN_SONGS)
    assert result.intent == Intent.FACT
    assert result.mentioned_song_name is None


def test_classify_fact_intent_from_mentioned_song():
    result = classify("When did they last play Elephant?", KNOWN_SONGS)
    assert result.intent == Intent.FACT
    assert result.mentioned_song_name == "Elephant"


def test_classify_prefers_longest_matching_song_name():
    songs = ["Let It Happen", "Happen"]
    result = classify("When will they play Let It Happen?", songs)
    assert result.mentioned_song_name == "Let It Happen"


def test_classify_falls_back_to_chat_for_unrelated_question():
    result = classify("What's your favorite color?", KNOWN_SONGS)
    assert result.intent == Intent.CHAT
    assert result.mentioned_song_name is None


def test_classified_intent_is_a_frozen_dataclass():
    a = ClassifiedIntent(Intent.CHAT)
    b = ClassifiedIntent(Intent.CHAT)
    assert a == b
