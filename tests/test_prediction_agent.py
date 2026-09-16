from datetime import date

from undercurrents.prediction.agent import PredictionAgent
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, song_names, tour_id):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    songs = [
        SetlistSongEntry(i + 1, 1, name, name == "Encore Song", False, None, False, None)
        for i, name in enumerate(song_names)
    ]
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=songs,
    )
    db.save_setlist(conn, normalized)
    conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
    conn.commit()


def _seed_history(conn):
    db.ensure_songs_clustering_columns(conn)
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()

    dates = ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01", "2020-05-01", "2020-06-01"]
    for i, event_date in enumerate(dates):
        songs = ["Common Song", "Encore Song"] if i % 2 == 0 else ["Common Song", "Rare Song"]
        _setlist(conn, f"s{i}", event_date, songs, tour_id=1)

    rows = [(f"s{i}", float(i), float(i), i % 2) for i in range(len(dates))]
    db.replace_setlist_clusters(conn, rows)


def _setlist_with_country(conn, setlist_id, event_date, country, tour_id):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id=f"v-{country}", name="V", city="C", state=None, country=country)
    song = SetlistSongEntry(1, 1, "Common Song", False, False, None, False, None)
    normalized = NormalizedSetlist(
        id=setlist_id, event_date=event_date, last_updated_source="x",
        url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=[song],
    )
    db.save_setlist(conn, normalized)
    conn.execute("UPDATE setlists SET tour_id = ? WHERE id = ?", (tour_id, setlist_id))
    conn.commit()


def _seed_country_history(conn):
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()
    # 4 shows in Country A, 1 in Country B -- Country A should dominate the ranking.
    dates = ["2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01", "2020-05-01"]
    countries = ["Country A", "Country A", "Country B", "Country A", "Country A"]
    for i, (event_date, country) in enumerate(zip(dates, countries)):
        _setlist_with_country(conn, f"s{i}", event_date, country, tour_id=1)


def test_predict_next_show_country_returns_all_known_countries_sorted_by_probability(tmp_conn):
    _seed_country_history(tmp_conn)

    predictions = PredictionAgent().predict_next_show_country(tmp_conn, reference_date=date(2020, 6, 1))

    assert {p.country for p in predictions} == {"Country A", "Country B"}
    probabilities = [p.probability for p in predictions]
    assert probabilities == sorted(probabilities, reverse=True)
    assert predictions[0].country == "Country A"  # the historically dominant country


def test_predict_next_show_country_defaults_reference_date_to_today(tmp_conn):
    _seed_country_history(tmp_conn)

    predictions = PredictionAgent().predict_next_show_country(tmp_conn)  # must not raise
    assert len(predictions) == 2


def test_predict_next_show_returns_all_known_songs_sorted_by_probability(tmp_conn):
    _seed_history(tmp_conn)

    predictions = PredictionAgent().predict_next_show(tmp_conn, reference_date=date(2020, 7, 1))

    song_names = {db.get_song_id_by_name(tmp_conn, n) for n in ["Common Song", "Encore Song", "Rare Song"]}
    assert {p.song_id for p in predictions} == song_names
    probabilities = [p.probability for p in predictions]
    assert probabilities == sorted(probabilities, reverse=True)


def test_predict_next_show_defaults_reference_date_to_today(tmp_conn):
    _seed_history(tmp_conn)

    predictions = PredictionAgent().predict_next_show(tmp_conn)  # must not raise
    assert len(predictions) == 3


def test_predict_setlist_length_returns_a_plausible_float(tmp_conn):
    _seed_history(tmp_conn)

    predicted = PredictionAgent().predict_setlist_length(tmp_conn, reference_date=date(2020, 7, 1))

    assert isinstance(predicted, float)
    assert 0.0 <= predicted <= 10.0  # fixture setlists have 2 songs each; a sane model stays near that


def test_predict_position_category_returns_a_probability_distribution(tmp_conn):
    _seed_history(tmp_conn)
    common_song_id = db.get_song_id_by_name(tmp_conn, "Common Song")

    probabilities = PredictionAgent().predict_position_category(
        tmp_conn, common_song_id, reference_date=date(2020, 7, 1)
    )

    assert abs(sum(probabilities.values()) - 1.0) < 1e-6
    assert all(0.0 <= p <= 1.0 for p in probabilities.values())


def test_predict_next_show_date_returns_a_date_after_the_last_known_show(tmp_conn):
    _seed_history(tmp_conn)

    predicted = PredictionAgent().predict_next_show_date(tmp_conn, as_of_date=date(2020, 7, 1))

    assert isinstance(predicted, date)
    assert predicted > date(2020, 6, 1)  # after the fixture's last show (2020-06-01)


def test_predict_encore_probability_reflects_historical_ratio(tmp_conn):
    _seed_history(tmp_conn)
    encore_song_id = db.get_song_id_by_name(tmp_conn, "Encore Song")

    probability = PredictionAgent().predict_encore_probability(tmp_conn, encore_song_id)

    assert probability == 1.0  # every time it was played, it was in the encore


def test_predict_encore_probability_is_zero_for_never_played_song(tmp_conn):
    _seed_history(tmp_conn)
    fake_song_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    probability = PredictionAgent().predict_encore_probability(tmp_conn, fake_song_id)

    assert probability == 0.0


def test_predict_encore_probability_includes_merged_variant_plays(tmp_conn):
    _seed_history(tmp_conn)
    canonical_id = db.get_song_id_by_name(tmp_conn, "Common Song")
    variant_id = db.upsert_song(tmp_conn, "Common Song (Live Variant)")
    tmp_conn.commit()
    db.set_song_canonical(tmp_conn, variant_id, canonical_id)
    # "Common Song" itself is never in the encore in the fixture (always position 1), so its
    # own encore probability is 0 — but if a merged variant's plays were always in the encore,
    # the canonical id's probability must reflect that too.
    _setlist(tmp_conn, "s-variant", "2020-07-01", ["Filler", "Common Song (Live Variant)"], tour_id=1)
    tmp_conn.execute(
        "UPDATE setlist_songs SET is_encore = 1 WHERE setlist_id = 's-variant' AND song_id = ?",
        (variant_id,),
    )
    tmp_conn.commit()

    probability = PredictionAgent().predict_encore_probability(tmp_conn, canonical_id)

    assert probability == 1 / 7  # 1 encore play (the variant) out of 6+1 total plays


def test_predict_opener_probability_reflects_historical_ratio(tmp_conn):
    _seed_history(tmp_conn)
    common_song_id = db.get_song_id_by_name(tmp_conn, "Common Song")

    probability = PredictionAgent().predict_opener_probability(tmp_conn, common_song_id)

    assert probability == 1.0  # "Common Song" is always listed (and thus positioned) first


def test_predict_opener_probability_is_zero_for_never_played_song(tmp_conn):
    _seed_history(tmp_conn)
    fake_song_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    probability = PredictionAgent().predict_opener_probability(tmp_conn, fake_song_id)

    assert probability == 0.0


def test_predict_closer_probability_reflects_historical_ratio(tmp_conn):
    _seed_history(tmp_conn)
    encore_song_id = db.get_song_id_by_name(tmp_conn, "Encore Song")

    probability = PredictionAgent().predict_closer_probability(tmp_conn, encore_song_id)

    assert probability == 1.0  # "Encore Song" is always the last (2nd) song of its setlist


def test_predict_closer_probability_is_zero_for_never_played_song(tmp_conn):
    _seed_history(tmp_conn)
    fake_song_id = db.upsert_song(tmp_conn, "Never Played")
    tmp_conn.commit()

    probability = PredictionAgent().predict_closer_probability(tmp_conn, fake_song_id)

    assert probability == 0.0


def test_predict_next_show_accepts_a_pretrained_model_and_skips_training(tmp_conn, monkeypatch):
    from undercurrents.prediction import features as features_module

    _seed_history(tmp_conn)
    rows, labels = features_module.build_training_rows(tmp_conn, before_date=date(2020, 7, 1))
    from undercurrents.prediction import model as model_module

    pretrained = model_module.train(rows, labels)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("build_training_rows should not be called when trained_model is given")

    monkeypatch.setattr(features_module, "build_training_rows", _fail_if_called)

    predictions = PredictionAgent().predict_next_show(
        tmp_conn, reference_date=date(2020, 7, 1), trained_model=pretrained
    )

    assert len(predictions) == 3


def test_predict_setlist_length_accepts_a_pretrained_model_and_skips_training(tmp_conn, monkeypatch):
    from undercurrents.prediction import setlist_length as setlist_length_module

    _seed_history(tmp_conn)
    rows, labels = setlist_length_module.build_training_rows(tmp_conn, before_date=date(2020, 7, 1))
    pretrained = setlist_length_module.train(rows, labels)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("build_training_rows should not be called when trained_model is given")

    monkeypatch.setattr(setlist_length_module, "build_training_rows", _fail_if_called)

    predicted = PredictionAgent().predict_setlist_length(
        tmp_conn, reference_date=date(2020, 7, 1), trained_model=pretrained
    )

    assert isinstance(predicted, float)


def test_predict_position_category_accepts_a_pretrained_model_and_skips_training(tmp_conn, monkeypatch):
    from undercurrents.prediction import position as position_module

    _seed_history(tmp_conn)
    common_song_id = db.get_song_id_by_name(tmp_conn, "Common Song")
    rows, labels = position_module.build_training_rows(tmp_conn, before_date=date(2020, 7, 1))
    pretrained = position_module.train(rows, labels)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("build_training_rows should not be called when trained_model is given")

    monkeypatch.setattr(position_module, "build_training_rows", _fail_if_called)

    probabilities = PredictionAgent().predict_position_category(
        tmp_conn, common_song_id, reference_date=date(2020, 7, 1), trained_model=pretrained
    )

    assert abs(sum(probabilities.values()) - 1.0) < 1e-6


def test_predict_next_show_date_accepts_a_pretrained_model_and_skips_training(tmp_conn, monkeypatch):
    from undercurrents.prediction import next_show_date as next_show_date_module

    _seed_history(tmp_conn)
    rows, labels = next_show_date_module.build_training_rows(tmp_conn, before_date=date(2020, 7, 1))
    pretrained = next_show_date_module.train(rows, labels)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("build_training_rows should not be called when trained_model is given")

    monkeypatch.setattr(next_show_date_module, "build_training_rows", _fail_if_called)

    predicted = PredictionAgent().predict_next_show_date(
        tmp_conn, as_of_date=date(2020, 7, 1), trained_model=pretrained
    )

    assert predicted > date(2020, 6, 1)


def test_predict_next_show_country_accepts_a_pretrained_model_and_skips_training(tmp_conn, monkeypatch):
    from undercurrents.prediction import next_show_location as next_show_location_module

    _seed_country_history(tmp_conn)
    rows, labels = next_show_location_module.build_training_rows(tmp_conn, before_date=date(2020, 6, 1))
    pretrained = next_show_location_module.train(rows, labels)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("build_training_rows should not be called when trained_model is given")

    monkeypatch.setattr(next_show_location_module, "build_training_rows", _fail_if_called)

    predictions = PredictionAgent().predict_next_show_country(
        tmp_conn, reference_date=date(2020, 6, 1), trained_model=pretrained
    )

    assert {p.country for p in predictions} == {"Country A", "Country B"}
