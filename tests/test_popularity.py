from undercurrents.clustering import popularity


def test_versions_of_the_same_song_are_summed_and_remixes_left_out():
    recs = [
        {"recording_name": "Let It Happen", "total_listen_count": 100, "total_user_count": 40},
        {"recording_name": "Let It Happen", "total_listen_count": 5, "total_user_count": 3},
        {"recording_name": "Let It Happen (Soulwax remix)", "total_listen_count": 50, "total_user_count": 30},
        {"recording_name": "Why Won’t You Make Up Your Mind?", "total_listen_count": 7, "total_user_count": None},
    ]
    totals = popularity.aggregate(recs)
    assert totals["let it happen"] == {"listens": 105, "listeners": 40}
    assert totals["why wont you make up your mind"]["listens"] == 7


def test_assign_popularity_writes_counts(tmp_conn):
    tmp_conn.execute("INSERT INTO songs (id, name) VALUES (1, 'Let it happen')")
    tmp_conn.execute("INSERT INTO songs (id, name) VALUES (2, 'Unknown Song')")
    summary = popularity.assign_popularity(
        tmp_conn, recordings=[{"recording_name": "Let It Happen", "total_listen_count": 9, "total_user_count": 4}]
    )
    assert summary == {"recordings": 1, "songs_matched": 1}
    row = tmp_conn.execute("SELECT listen_count, listener_count FROM songs WHERE id = 1").fetchone()
    assert (row["listen_count"], row["listener_count"]) == (9, 4)
