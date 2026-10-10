from peakseason.ingest import budget


def test_per_cell_cap_and_newest_first(make_report):
    reps = [make_report(age_days=d) for d in (5, 1, 3, 2, 4)]
    picked = budget.plan(reps, set(), per_run=10, per_cell=3)
    assert [r.observed_at for r in picked] == sorted((r.observed_at for r in reps), reverse=True)[
        :3
    ]


def test_per_run_cap(make_report):
    reps = [make_report(lat=10 + i, lng=10) for i in range(20)]
    assert len(budget.plan(reps, set(), per_run=7, per_cell=3)) == 7


def test_priority_famous_then_busiest(make_report):
    quiet_famous = make_report(lat=35.0094, lng=135.6668)
    busy = [make_report(lat=43.65, lng=-79.38) for _ in range(4)]
    single = make_report(lat=-33.87, lng=151.21)
    famous = {(quiet_famous.cell, "maple")}
    picked = budget.plan([single, *busy, quiet_famous], famous, per_run=3, per_cell=3)
    assert picked[0] is quiet_famous
    assert all(r.cell == busy[0].cell for r in picked[1:])


def test_annotated_photos_first_within_cell(make_report):
    old_signal = make_report(age_days=6, in_season_signal=True)
    new = [make_report(age_days=0) for _ in range(3)]
    picked = budget.plan([*new, old_signal], set(), per_run=10, per_cell=2)
    assert picked[0] is old_signal
