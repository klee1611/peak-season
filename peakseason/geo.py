"""Geohash cells, distances and place-name cleanup. Pure functions, no dependencies."""

import math
import re
from collections import Counter

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_DECODE = {c: i for i, c in enumerate(_BASE32)}

CELL_PRECISION = 5  # ~5 km x 5 km
SHARD_PRECISION = 2  # ~1,250 km x 625 km


def encode(lat: float, lng: float, precision: int = CELL_PRECISION) -> str:
    lat_lo, lat_hi, lng_lo, lng_hi = -90.0, 90.0, -180.0, 180.0
    chars, bits, ch, even = [], 0, 0, True
    while len(chars) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            if lng >= mid:
                ch, lng_lo = ch * 2 + 1, mid
            else:
                ch, lng_hi = ch * 2, mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                ch, lat_lo = ch * 2 + 1, mid
            else:
                ch, lat_hi = ch * 2, mid
        even = not even
        bits += 1
        if bits == 5:
            chars.append(_BASE32[ch])
            bits, ch = 0, 0
    return "".join(chars)


def bounds(gh: str) -> tuple[float, float, float, float]:
    """Return (lat_lo, lat_hi, lng_lo, lng_hi) of a geohash cell."""
    lat_lo, lat_hi, lng_lo, lng_hi = -90.0, 90.0, -180.0, 180.0
    even = True
    for c in gh:
        v = _DECODE[c]
        for shift in range(4, -1, -1):
            bit = (v >> shift) & 1
            if even:
                mid = (lng_lo + lng_hi) / 2
                lng_lo, lng_hi = (mid, lng_hi) if bit else (lng_lo, mid)
            else:
                mid = (lat_lo + lat_hi) / 2
                lat_lo, lat_hi = (mid, lat_hi) if bit else (lat_lo, mid)
            even = not even
    return lat_lo, lat_hi, lng_lo, lng_hi


def decode(gh: str) -> tuple[float, float]:
    lat_lo, lat_hi, lng_lo, lng_hi = bounds(gh)
    return (lat_lo + lat_hi) / 2, (lng_lo + lng_hi) / 2


def neighbours(gh: str) -> list[str]:
    """The (up to) 8 surrounding cells. Wraps across the antimeridian; stops at the poles."""
    lat_lo, lat_hi, lng_lo, lng_hi = bounds(gh)
    lat, lng = (lat_lo + lat_hi) / 2, (lng_lo + lng_hi) / 2
    dlat, dlng = lat_hi - lat_lo, lng_hi - lng_lo
    out: list[str] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            nlat = lat + dy * dlat
            if not -90 < nlat < 90:
                continue
            nlng = (lng + dx * dlng + 180) % 360 - 180
            n = encode(nlat, nlng, len(gh))
            if n != gh and n not in out:
                out.append(n)
    return out


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Separators used in place_guess strings across languages (ASCII comma, full-width comma,
# Japanese/Chinese enumeration comma).
_SPLIT = re.compile(r"\s*[,，、]\s*")
_DIGIT = re.compile(r"\d")
_JUNK = {"unnamed road", "unknown", ""}


def place_parts(place_guess: str | None) -> list[str]:
    """Split a place_guess into usable parts, dropping street addresses and postcodes.

    Any part containing a digit is treated as an address or postcode. That loses the
    occasional "Route 66", but keeps people's house numbers out of the UI.
    """
    if not place_guess:
        return []
    parts = [p.strip() for p in _SPLIT.split(place_guess)]
    return [p for p in parts if p.lower() not in _JUNK and not _DIGIT.search(p)]


def cell_name(place_guesses: list[str | None]) -> str | None:
    """Most common cleaned leading part of the cell's place guesses."""
    names = Counter()
    for pg in place_guesses:
        parts = place_parts(pg)
        # A single part that is only a country/region code ("CA", "JP") is not a name.
        if parts and not (len(parts) == 1 and len(parts[0]) <= 3):
            names[parts[0]] += 1
    return names.most_common(1)[0][0] if names else None


def cell_city(place_guesses: list[str | None]) -> str | None:
    """Most common second part (usually the city) of the cell's place guesses."""
    cities = Counter()
    for pg in place_guesses:
        parts = place_parts(pg)
        if len(parts) >= 2:
            cities[parts[1]] += 1
    return cities.most_common(1)[0][0] if cities else None


def median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
