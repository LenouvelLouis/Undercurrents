import numpy as np
import pytest

from undercurrents.benchmarks import data, sequence


def _shows(specs):
    return [
        {"setlist_id": f"s{i}", "event_date": date, "songs": songs}
        for i, (date, songs) in enumerate(specs)
    ]


def test_split_is_chronological_not_random():
    shows = _shows([(f"2020-01-{d:02d}", [1, 2, 3]) for d in range(1, 11)])
    train, test = data.split(shows, holdout_shows=3)

    assert len(train) == 7 and len(test) == 3
    assert [s["event_date"] for s in test] == ["2020-01-08", "2020-01-09", "2020-01-10"]
    # every training date is strictly before every test date
    assert max(s["event_date"] for s in train) < min(s["event_date"] for s in test)


def test_split_refuses_when_there_is_nothing_left_to_train_on():
    shows = _shows([("2020-01-01", [1, 2])])
    with pytest.raises(ValueError):
        data.split(shows, holdout_shows=5)


def test_markov_learns_a_deterministic_chain():
    shows = _shows([(f"2020-01-{d:02d}", [1, 2, 3]) for d in range(1, 9)])
    song_ids, index = sequence._vocab(shows)
    model = sequence.train_markov(shows, len(song_ids), index)

    # after song 1 the next song is always 2 in this data, so it must rank first
    scores = sequence.markov_scores(model, [index[1]])
    assert int(np.argmax(scores)) == index[2]
    # and the opener distribution favours song 1
    assert int(np.argmax(sequence.markov_scores(model, []))) == index[1]


def test_markov_smoothing_keeps_unseen_pairs_possible():
    shows = _shows([("2020-01-01", [1, 2]), ("2020-01-02", [1, 2])])
    song_ids, index = sequence._vocab(shows)
    model = sequence.train_markov(shows, len(song_ids), index)

    # 2 -> 1 never happens in the data, but must not be impossible
    assert model["transitions"][index[2]][index[1]] > 0


def test_evaluate_never_proposes_a_song_already_played_tonight():
    """A scorer with a fixed, strict preference order. Song 1 is always its favourite, so
    without the already-played mask it would predict song 1 again at step two and score 0.5.
    Scoring 1.0 is only reachable if the mask removed it, which is what this pins down."""
    shows = _shows([("2020-01-01", [1, 2]), ("2020-01-02", [1, 2])])
    song_ids, index = sequence._vocab(shows)

    def fixed_preference(_prefix):
        scores = np.zeros(len(song_ids))
        scores[index[1]] = 1.0  # always the top pick
        scores[index[2]] = 0.5
        return scores

    result = sequence._evaluate(fixed_preference, shows, index, len(song_ids))
    assert result["predictions"] == 4
    assert result["top_1_accuracy"] == pytest.approx(1.0, abs=1e-4)


def test_load_sequences_drops_tape_entries_and_one_song_shows(tmp_conn):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
    from undercurrents.storage import db

    def save(setlist_id, date, songs):
        db.save_setlist(
            tmp_conn,
            NormalizedSetlist(
                id=setlist_id, event_date=date, last_updated_source="x",
                url=f"https://x/{setlist_id}",
                artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
                venue=Venue(id="v1", name="V", city="C", state=None, country="X"),
                tour=None, songs=songs,
            ),
        )

    save("s1", "2020-01-01", [
        SetlistSongEntry(1, 1, "Intro", False, False, None, True, None),
        SetlistSongEntry(2, 1, "A", False, False, None, False, None),
        SetlistSongEntry(3, 1, "B", False, False, None, False, None),
    ])
    # a single-song show carries no transition, so it is not a usable sequence
    save("s2", "2020-01-02", [SetlistSongEntry(1, 1, "A", False, False, None, False, None)])

    sequences = data.load_sequences(tmp_conn)
    assert len(sequences) == 1
    assert len(sequences[0]["songs"]) == 2
