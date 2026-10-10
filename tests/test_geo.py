import pytest

from peakseason import geo


def test_encode_known_value():
    # Reference value from the original geohash description.
    assert geo.encode(57.64911, 10.40744, 11) == "u4pruydqqvj"


@pytest.mark.parametrize(
    "lat,lng",
    [(43.6532, -79.3832), (35.0116, 135.7681), (-33.8688, 151.2093), (-54.8, -68.3), (0.0, 0.0)],
)
def test_decode_round_trip(lat, lng):
    h = geo.encode(lat, lng, 5)
    s, n, w, e = geo.bounds(h)
    assert s <= lat <= n and w <= lng <= e
    assert geo.encode(*geo.decode(h), 5) == h


def test_neighbours_are_adjacent_and_distinct():
    h = geo.encode(43.6532, -79.3832, 5)
    ns = geo.neighbours(h)
    assert len(ns) == 8 and len(set(ns)) == 8 and h not in ns
    lat, lng = geo.decode(h)
    assert all(geo.haversine_km(lat, lng, *geo.decode(n)) < 10 for n in ns)


def test_neighbours_wrap_antimeridian():
    h = geo.encode(-17.0, 179.99, 2)  # Fiji
    lngs = [geo.decode(n)[1] for n in geo.neighbours(h)]
    assert any(x < 0 for x in lngs)


def test_haversine():
    # Toronto -> Kyoto is roughly 10,500 km.
    assert 10_000 < geo.haversine_km(43.6532, -79.3832, 35.0116, 135.7681) < 11_000
    assert geo.haversine_km(1, 1, 1, 1) == 0


def test_place_parts_drops_addresses_unicode_safe():
    assert geo.place_parts("123 Queen St W, Toronto, ON M5H 2M9, Canada") == [
        "Toronto",
        "Canada",
    ]
    assert geo.place_parts("嵐山、京都市、日本") == ["嵐山", "京都市", "日本"]
    assert geo.place_parts("여의도동, 서울특별시, 대한민국") == [
        "여의도동",
        "서울특별시",
        "대한민국",
    ]
    assert geo.place_parts(None) == []


def test_cell_name_and_city():
    guesses = [
        "High Park, Toronto, ON, CA",
        "High Park, Toronto, ON, CA",
        "Bloor St, Toronto, ON, CA",
        "CA",
        None,
    ]
    assert geo.cell_name(guesses) == "High Park"
    assert geo.cell_city(guesses) == "Toronto"
    assert geo.cell_name(["CA", None]) is None


def test_median():
    assert geo.median([3, 1, 2]) == 2
    assert geo.median([1, 2, 3, 4]) == 2.5
