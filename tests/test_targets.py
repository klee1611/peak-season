import pytest
import yaml

from peakseason.config import ROOT
from peakseason.targets import Target, load_target


def test_both_targets_load(targets):
    assert {"maple", "sakura"} <= set(targets)
    assert targets["maple"].stage_ids == ["green", "turning", "peak", "past_peak"]
    assert targets["maple"].is_go_now("peak")
    assert not targets["maple"].is_go_now("turning")


def test_sakura_go_now_on_first_and_full_bloom(targets):
    s = targets["sakura"]
    assert [x.id for x in s.stages if x.go_now] == ["first_bloom", "full_bloom"]


def test_sakura_does_not_use_genus_prunus(targets):
    taxa = targets["sakura"].inat_taxa
    assert all(not (t.name == "Prunus" and t.rank == "genus") for t in taxa)


def test_prompt_files_have_versions(targets):
    for t in targets.values():
        for rel in (t.photo_prompt, t.text_prompt):
            assert (ROOT / rel).read_text(encoding="utf-8").startswith("# version:")


def _base():
    return yaml.safe_load((ROOT / "targets" / "maple.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(stages=[d["stages"][0]]),
        lambda d: d.update(stages=d["stages"] + [d["stages"][0]]),
        lambda d: [s.update(go_now=False) for s in d["stages"]],
        lambda d: d.update(inat_taxa=[]),
    ],
)
def test_bad_target_rejected(mutate):
    data = _base()
    mutate(data)
    with pytest.raises(ValueError):
        Target.model_validate(data)


def test_missing_prompt_file_rejected(tmp_path):
    data = _base()
    data["photo_prompt"] = "prompts/does_not_exist.txt"
    (tmp_path / "targets").mkdir()
    p = tmp_path / "targets" / "x.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="prompt file not found"):
        load_target(p, root=ROOT)


def test_validate_groups_union(targets):
    from peakseason.validate import observed_groups

    maple = targets["maple"]
    labels = ["Leaves=Green Leaves", "Leaves=Colored Leaves", "Flowers and Fruits=Fruits"]
    assert observed_groups(maple, labels) == {"Green Leaves", "Colored Leaves"}
    assert observed_groups(maple, []) == set()
