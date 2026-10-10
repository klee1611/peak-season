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
# Region codes as iNaturalist writes them: "CA", "CA-ON", "JP-26".
_CODE = re.compile(r"^[A-Z]{2,3}(-[A-Z0-9]{1,3})?$")
# Extra cleanup for English-style street addresses (other scripts rely on the digit rule).
_STREET = re.compile(
    r"\b(st|rd|ave|dr|blvd|ln|hwy|cres|ct|pkwy|street|road|avenue|drive|lane|boulevard|"
    r"highway|crescent|court|parkway)\.?( [nsew])?$|\b(at|after|before|near|off)\b",
    re.IGNORECASE,
)


def _clean_part(part: str) -> str:
    """Remove addresses and postcodes from one part of a place_guess.

    A part that starts with a number is a street address ("89 Hongeunjungang-ro") and is
    dropped. Otherwise digit tokens are postcodes ("North Sydney NSW 2060") and are removed
    along with the state code before them. A single token with a digit (CJK addresses are
    written without spaces) is dropped.
    """
    if not _DIGIT.search(part):
        return part
    words = part.split()
    if _DIGIT.search(words[0]):
        return ""
    words = [w for w in words if not _DIGIT.search(w)]
    while words and _CODE.match(words[-1]):
        words.pop()
    return " ".join(words)


def place_parts(place_guess: str | None) -> list[str]:
    """Split a place_guess into usable place names, most specific first.

    Removes house numbers, postcodes, region codes, street names and the trailing country,
    so people's addresses never reach the UI. Works on any script: CJK enumeration commas
    split like ASCII commas, and the digit rule needs no language knowledge.
    """
    if not place_guess:
        return []
    raw = [p.strip() for p in _SPLIT.split(place_guess)]
    if len(raw) >= 2:
        raw = raw[:-1]  # the last part is the country
    out = []
    for p in raw:
        p = _clean_part(p).strip()
        if p.lower() in _JUNK or _CODE.match(p) or _STREET.search(p):
            continue
        out.append(p)
    return out


def cell_name(place_guesses: list[str | None]) -> str | None:
    """Most common cleaned leading part of the cell's place guesses."""
    names = Counter()
    for pg in place_guesses:
        parts = place_parts(pg)
        if parts:
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
