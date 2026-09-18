"""The running-order decoder. The GRU is trained here on a toy corpus with the epoch count
cut right down, so these tests check the decoding contract rather than the model's quality,
which is what the backtest is for."""

import pytest

from undercurrents.benchmarks import sequence
from undercurrents.prediction import running_order


@pytest.fixture
def tiny_bundle(monkeypatch):
    monkeypatch.setattr(sequence, "EPOCHS", 2)
    monkeypatch.setattr(sequence, "EMBED_DIM", 8)
    monkeypatch.setattr(sequence, "HIDDEN_DIM", 8)
    sequences = [
        {"setlist_id": "s1", "event_date": "2020-01-01", "songs": [1, 2, 3, 4]},
        {"setlist_id": "s2", "event_date": "2020-01-02", "songs": [1, 2, 4, 3]},
        {"setlist_id": "s3", "event_date": "2020-01-03", "songs": [1, 3, 2, 4]},
    ]
    return running_order.train(sequences)


def test_a_bundle_carries_its_vocabulary_and_no_live_model(tiny_bundle):
    # Only plain data is kept, so the file can be reloaded without this module's classes.
    assert tiny_bundle["song_ids"] == [1, 2, 3, 4]
    assert tiny_bundle["trained_on_shows"] == 3
    assert "state_dict" in tiny_bundle
    assert all(not callable(value) for value in tiny_bundle.values())


def test_decode_never_repeats_a_song(tiny_bundle):
    order = running_order.decode(tiny_bundle, length=4)
    song_ids = [entry["song_id"] for entry in order]
    assert len(song_ids) == 4
    assert len(set(song_ids)) == 4, "the band does not play a song twice in one night"
    assert [entry["position"] for entry in order] == [1, 2, 3, 4]


def test_decode_is_capped_by_the_vocabulary(tiny_bundle):
    # Asking for more songs than exist must not loop forever or invent an id.
    order = running_order.decode(tiny_bundle, length=99)
    assert len(order) == 4
    assert {entry["song_id"] for entry in order} == {1, 2, 3, 4}


def test_decode_of_zero_length_is_empty(tiny_bundle):
    assert running_order.decode(tiny_bundle, length=0) == []


def test_confidence_is_the_share_among_songs_still_available(tiny_bundle):
    order = running_order.decode(tiny_bundle, length=4)
    for entry in order:
        assert 0.0 <= entry["confidence"] <= 1.0
    # By the last position one song remains, so it takes the whole remaining mass.
    assert order[-1]["confidence"] == pytest.approx(1.0)


def test_a_seed_prefix_is_honoured_and_never_repeated(tiny_bundle):
    # Index 0 in the vocabulary is song id 1.
    order = running_order.decode(tiny_bundle, length=3, seed=[0])
    song_ids = [entry["song_id"] for entry in order]
    assert 1 not in song_ids, "a song given as already played cannot be predicted again"
    assert len(set(song_ids)) == 3
    # positions continue from where the seed left off rather than restarting at 1
    assert [entry["position"] for entry in order] == [2, 3, 4]


def test_a_seed_shrinks_how_many_songs_are_left_to_place(tiny_bundle):
    order = running_order.decode(tiny_bundle, length=99, seed=[0, 1])
    assert len(order) == 2, "only two songs remain once two of the four are seeded"


def test_restore_rebuilds_a_usable_model(tiny_bundle):
    model = running_order.restore(tiny_bundle)
    first = running_order.decode(tiny_bundle, length=4, model=model)
    second = running_order.decode(tiny_bundle, length=4, model=model)
    # Greedy decoding is deterministic: the same bundle must give the same order twice.
    assert first == second
