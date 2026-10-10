import json

import httpx
import pytest

from peakseason.config import ROOT
from peakseason.model.classify import Classifier, extract_json
from peakseason.store import Store

URL = "https://example.org/photos/1/medium.jpg"


class FakeModel:
    name = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def complete(self, prompt, image=None):
        self.calls += 1
        return self.replies.pop(0)


@pytest.fixture
async def http():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=b"\xff\xd8jpeg"))
    async with httpx.AsyncClient(transport=transport) as client:
        yield client


async def classify(targets, http, replies, target="maple"):
    model = FakeModel(replies)
    clf = Classifier(model, Store(":memory:"), http, ROOT)
    return await clf.classify_photo(targets[target], URL), model, clf


async def test_valid_photo(targets, http):
    reply = json.dumps(
        {"is_target_photo": True, "stage": "peak", "progress": 0.8, "confidence": 0.9}
    )
    c, model, _ = await classify(targets, http, [reply])
    assert (c.status, c.stage, c.confidence) == ("ok", "peak", 0.9)
    assert model.calls == 1


async def test_bare_rejection_is_valid(targets, http):
    c, model, _ = await classify(targets, http, ['{"is_target_photo": false}'])
    assert c.status == "rejected"
    assert model.calls == 1


async def test_retry_then_ok(targets, http):
    good = '```json\n{"is_target_photo": true, "stage": "full_bloom", "confidence": 0.7}\n```'
    c, model, _ = await classify(targets, http, ["not json", good], target="sakura")
    assert (c.status, c.stage) == ("ok", "full_bloom")
    assert model.calls == 2


async def test_unknown_stage_twice_is_unclassified(targets, http):
    bad = '{"is_target_photo": true, "stage": "full_bloom", "confidence": 0.9}'
    c, model, _ = await classify(targets, http, [bad, bad])  # sakura stage for maple
    assert c.status == "unclassified"
    assert model.calls == 2


async def test_cache_hit_skips_model(targets, http):
    reply = '{"is_target_photo": true, "stage": "green", "confidence": 0.5}'
    model = FakeModel([reply])
    clf = Classifier(model, Store(":memory:"), http, ROOT)
    first = await clf.classify_photo(targets["maple"], URL)
    second = await clf.classify_photo(targets["maple"], URL)
    assert first == second and model.calls == 1


def test_extract_json_tolerates_text():
    assert extract_json('Sure! {"a": 1} hope that helps') == {"a": 1}
