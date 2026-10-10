import pytest

from peakseason import aggregate, geo
from peakseason.spots import Spot

from .conftest import NOW

TORONTO = (43.6532, -79.3832)
KYOTO = (35.0116, 135.7681)
SYDNEY = (-33.8688, 151.2093)


def run(target, reports, spots=()):
    return aggregate.aggregate(target, reports, NOW, 7, list(spots))


@pytest.mark.parametrize("where", [TORONTO, KYOTO, SYDNEY])
def test_maple_peak_in_any_hemisphere(targets, make_report, where):
    reps = [make_report(lat=where[0], lng=where[1], stage="peak") for _ in range(3)]
    [cell] = run(targets["maple"], reps)
    assert cell.stage == "peak"
    assert cell.report_count == 3
    assert cell.cell == geo.encode(*where)


def test_sakura_stage_list(targets, make_report):
    t = targets["sakura"]
    reps = [
        make_report("sakura", *SYDNEY, stage="first_bloom"),
        make_report("sakura", *SYDNEY, stage="full_bloom"),
        make_report("sakura", *SYDNEY, stage="full_bloom"),
    ]
    [cell] = run(t, reps)
    assert cell.stage == "full_bloom"
    assert t.is_go_now(cell.stage)


def test_fewer_than_two_reports_is_not_enough(targets, make_report):
    [cell] = run(targets["maple"], [make_report(stage="peak")])
    assert cell.stage is None
    assert cell.report_count == 1


def test_recency_weighting_favours_new_reports(targets, make_report):
    reps = [
        make_report(stage="green", age_days=6),
        make_report(stage="green", age_days=6),
        make_report(stage="peak", age_days=0),
    ]
    [cell] = run(targets["maple"], reps)
    # Unweighted mean would be 0.67 -> turning; recency pushes it to peak.
    assert cell.stage == "peak"


def test_text_reports_weigh_less(make_report):
    photo = make_report(stage="peak", age_days=0)
    text = make_report(stage="peak", age_days=0, kind="text", source="serpapi")
    assert aggregate.weight(text, NOW) == pytest.approx(0.6 * aggregate.weight(photo, NOW))


def test_reports_outside_window_ignored(targets, make_report):
    reps = [make_report(stage="peak", age_days=8), make_report(stage="peak", age_days=9)]
    assert run(targets["maple"], reps) == []


def test_annotation_only_is_signal_without_stage(targets, make_report):
    reps = [make_report(in_season_signal=True, annotations=["Colored Leaves"]) for _ in range(5)]
    [cell] = run(targets["maple"], reps)
    assert cell.stage is None
    assert cell.report_count == 0
    assert cell.in_season_signals == 5
    assert cell.evidence == []


def test_unclassified_photos_alone_are_not_exported(targets, make_report):
    assert run(targets["maple"], [make_report(), make_report()]) == []


def test_other_targets_ignored(targets, make_report):
    reps = [make_report("sakura", stage="full_bloom"), make_report("sakura", stage="full_bloom")]
    assert run(targets["maple"], reps) == []


def test_evidence_newest_first_max_three(targets, make_report):
    reps = [make_report(stage="peak", age_days=d) for d in (3, 1, 2, 4)]
    [cell] = run(targets["maple"], reps)
    assert [r.observed_at for r in cell.evidence] == sorted(
        (r.observed_at for r in reps), reverse=True
    )[:3]
    assert all(r.license and r.attribution for r in cell.evidence)


def test_name_and_coords_from_reports(targets, make_report):
    reps = [
        make_report(
            stage="peak", lat=43.6460, lng=-79.4630, place_guess="High Park, Toronto, ON, CA"
        ),
        make_report(
            stage="peak", lat=43.6470, lng=-79.4640, place_guess="High Park, Toronto, ON, CA"
        ),
    ]
    [cell] = run(targets["maple"], reps)
    assert cell.name == "High Park"
    assert cell.lat == pytest.approx(43.6465)
    assert not cell.is_famous_spot


def test_famous_spot_sets_name_and_coords(targets, make_report):
    spot = Spot(
        name="Arashiyama",
        local_name="嵐山",
        lat=35.0094,
        lng=135.6668,
        country="JP",
        lang="ja",
        known_for=["maple", "sakura"],
    )
    reps = [
        make_report(stage="peak", lat=35.0100, lng=135.6680, place_guess="右京区、京都市、日本"),
        make_report(stage="peak", lat=35.0090, lng=135.6660, place_guess="右京区、京都市、日本"),
    ]
    assert all(r.cell == spot.cell for r in reps)
    [cell] = run(targets["maple"], reps, [spot])
    assert cell.is_famous_spot
    assert cell.name == "Arashiyama"
    assert (cell.lat, cell.lng) == (spot.lat, spot.lng)
