import pytest
from pydantic import ValidationError

from app.buyer.verifier import verify
from app.core.models import Flat, JobResult, JobSpec, TaskCreate


@pytest.mark.parametrize("changes", [
    {"district": "Praha 70"}, {"district": "Not Praha 7"},
    {"price_czk": -1}, {"price_czk": 0}, {"price_czk": 25_001},
    {"url": "httpjunk"}, {"url": "https://"}, {"url": "https://[broken"},
    {"url": "https://example.com/a b"},
])
def test_unusable_listings_cannot_release_escrow(changes):
    fields = {"title": "Flat", "price_czk": 20_000, "district": "Praha 7",
              "url": "https://example.com/flat/1"}
    fields.update(changes)
    result = JobResult(flats=[Flat(**fields)], source="sample")
    assert verify(result, JobSpec(count=1))[0] is False


@pytest.mark.parametrize("district", [" PRAHA   7 ", "Praha 7 - Letna", "Praha 7 — Praha Holesovice"])
def test_district_comparison_ignores_case_spacing_and_locality(district):
    result = JobResult(flats=[Flat(title="Flat", price_czk=20_000, district=district,
                                   url="https://example.com/flat/1")], source="sample")
    assert verify(result, JobSpec(count=1))[0] is True


@pytest.mark.parametrize("budget", [0, -1, "NaN", "Infinity", "-Infinity"])
def test_invalid_task_budget_rejected(budget):
    with pytest.raises(ValidationError):
        TaskCreate(budget=budget)
