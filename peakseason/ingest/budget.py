"""Choose which photos to spend this run's model budget on.

Order: cells with a famous spot -> cells with the most observations -> the rest.
Within a cell: photos with an in-season annotation first, then newest first.
At most `per_cell` photos per (cell, target) and `per_run` overall. Whatever is left is
picked up next run, because finished photos are cached.
"""

from collections import Counter, defaultdict

from peakseason.reports import Report


def plan(
    candidates: list[Report],
    famous_cells: set[tuple[str, str]],
    per_run: int,
    per_cell: int,
) -> list[Report]:
    """`candidates` are unclassified photo reports; `famous_cells` are (cell, target_id)."""
    groups: dict[tuple[str, str], list[Report]] = defaultdict(list)
    for r in candidates:
        groups[(r.cell, r.target_id)].append(r)
    sizes = Counter({k: len(v) for k, v in groups.items()})

    def group_priority(key: tuple[str, str]):
        return (key not in famous_cells, -sizes[key], key)

    picked: list[Report] = []
    for key in sorted(groups, key=group_priority):
        reports = sorted(
            groups[key], key=lambda r: (not r.in_season_signal, -r.observed_at.timestamp())
        )
        for r in reports[:per_cell]:
            if len(picked) >= per_run:
                return picked
            picked.append(r)
    return picked
