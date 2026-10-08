import pytest
from pydantic import ValidationError

from app.buyer.verifier import verify
from app.core.models import Flat, JobResult, JobSpec, StatusResponse, TaskCreate


@pytest.mark.parametrize("changes", [
    {"district": "Praha 70"}, {"district": "Not Praha 7"},
    {"price_czk": -1}, {"price_czk": 0}, {"price_czk": 25_001},
    {"url": "httpjunk"}, {"url": "https://"}, {"url": "https://[broken"},
    {"url": "https://example.com/a b"},
    {"url": "https://example.com:bad/flat"}, {"url": "https://example.com:99999/flat"},
    {"url": "https://example.com:0/flat"},
    {"url": "\x00https://example.com/flat"}, {"url": "https://example.com/\x00flat"},
    {"url": "https://example.com/\x7fflat"},
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


@pytest.mark.parametrize("url", ["https://example.com:443/flat", "http://localhost:8000/flat",
                                  "https://[::1]:8443/flat"])
def test_valid_explicit_ports_remain_usable(url):
    result = JobResult(flats=[Flat(title="Flat", price_czk=20_000, district="Praha 7", url=url)],
                       source="sample")
    assert verify(result, JobSpec(count=1))[0] is True


@pytest.mark.parametrize("budget", [0, -1, "NaN", "Infinity", "-Infinity"])
def test_invalid_task_budget_rejected(budget):
    with pytest.raises(ValidationError):
        TaskCreate(budget=budget)


@pytest.mark.parametrize("price", [True, False, "20000", 20000.0])
def test_seller_delivery_cannot_coerce_rent_to_an_integer(price):
    payload = {"job_id": "j1", "status": "completed", "result": {
        "source": "sample", "flats": [{"title": "Flat", "price_czk": price,
        "district": "Praha 7", "url": "https://example.com/flat"}]}}
    with pytest.raises(ValidationError) as error:
        StatusResponse.model_validate(payload)
    assert error.value.errors()[0]["loc"] == ("result", "flats", 0, "price_czk")


def test_integer_rent_survives_seller_boundary_and_verification():
    payload = {"job_id": "j1", "status": "completed", "result": {
        "source": "sample", "flats": [{"title": "Flat", "price_czk": 20000,
        "district": "Praha 7", "url": "https://example.com/flat"}]}}
    status = StatusResponse.model_validate(payload)
    assert status.result.flats[0].price_czk == 20000
    assert verify(status.result, JobSpec(count=1))[0] is True
