def create(client, **overrides):
    body = {"idea": "I make achaar in Lucknow", "lang": "en", **overrides}
    return client.post("/api/runs", json=body)


def test_full_flow(client):
    run = create(client).json()
    run_id = run["id"]
    assert run["state"] == "briefed"

    listed = client.get(f"/api/runs/{run_id}/domains").json()
    assert listed["domains"][0]["name"] == "achaar1.com"

    chosen = client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"}).json()
    assert chosen["state"] == "domain_chosen"
    assert chosen["domain"]["renewal_price"] == 15.0
    assert chosen["site"] is None

    generated = client.post(f"/api/runs/{run_id}/generate", json={"domain": "achaar1.com", "price": 12.0}).json()
    assert generated["state"] == "site_generated"

    preview = client.get(f"/api/runs/{run_id}/preview", params={"lang": "hi"})
    assert preview.status_code == 200
    assert 'lang="hi"' in preview.text

    assert client.post(f"/api/runs/{run_id}/regenerate").json()["regenerations"] == 1
    assert client.get(f"/api/runs/{run_id}").json()["state"] == "site_generated"


def test_empty_idea_is_rejected(client):
    assert create(client, idea="   ").status_code == 422


def test_too_long_idea_is_rejected(client):
    assert create(client, idea="x" * 501).status_code == 422


def test_unknown_language_is_rejected(client):
    assert create(client, lang="fr").status_code == 422


def test_invalid_keyword_is_rejected(client):
    run_id = create(client).json()["id"]

    response = client.get(f"/api/runs/{run_id}/domains", params={"keyword": "bad; rm -rf"})

    assert response.status_code == 422


def test_unknown_run_returns_plain_error(client):
    response = client.get("/api/runs/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"


def test_out_of_order_step_returns_conflict(client):
    run_id = create(client).json()["id"]

    response = client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_run_state"


def test_mismatched_confirmation_returns_conflict(client):
    run_id = create(client).json()["id"]
    client.get(f"/api/runs/{run_id}/domains")
    client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"})

    response = client.post(f"/api/runs/{run_id}/generate", json={"domain": "achaar1.com", "price": 1.0})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "confirmation_mismatch"


def test_taken_domain_returns_conflict(client, domains):
    run_id = create(client).json()["id"]
    client.get(f"/api/runs/{run_id}/domains")
    domains.taken = True

    response = client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "domain_taken"


def test_claude_failure_returns_bad_gateway(client, claude):
    claude.fail = True

    response = create(client)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "generation_failed"


def test_unexpected_error_hides_details(client, orchestrator, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(orchestrator, "get_run", boom)

    response = client.get("/api/runs/any")

    assert response.status_code == 500
    assert "secret" not in response.text
    assert response.json()["error"]["code"] == "internal_error"


def test_run_creation_is_rate_limited(client, claude):
    calls = []
    original = claude.generate_brief
    claude.generate_brief = lambda idea, lang: calls.append(idea) or original(idea, lang)

    statuses = [create(client).status_code for _ in range(6)]

    assert statuses == [201, 201, 201, 201, 201, 429]
    blocked = create(client).json()
    assert blocked["error"]["code"] == "rate_limited"
    assert "sites" in blocked["error"]["message"]
    assert len(calls) == 5  # blocked requests never reach Claude


def test_run_limit_is_separate_from_contact_limit(client):
    for _ in range(5):
        assert create(client).status_code == 201
    contact = {"name": "Asha", "email": "asha@example.com", "message": "Hi"}
    assert client.post("/api/contact", json=contact).status_code == 200


def test_purchase_flow_over_http(client):
    run_id = client.post("/api/runs", json={"idea": "pickles", "lang": "en"}).json()["id"]
    client.get(f"/api/runs/{run_id}/domains")
    client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"})
    client.post(f"/api/runs/{run_id}/generate", json={"domain": "achaar1.com", "price": 12.0})

    quote = client.post(f"/api/runs/{run_id}/quote").json()["quote"]
    assert quote["price"] == 12.0 and quote["demo"] is True
    assert quote["agreements"][0]["type"] == "API_DPA"
    assert "token" not in quote and "idempotency_key" not in quote
    # Every route that returns the run hides them, not only the one that made the quote.
    again = client.get(f"/api/runs/{run_id}").json()["quote"]
    assert "token" not in again and "idempotency_key" not in again

    done = client.post(f"/api/runs/{run_id}/purchase", json={"agreement_types": ["API_DPA"], "price": 12.0}).json()
    assert done["state"] == "purchased"
    assert done["purchase"]["demo"] is True


def test_purchase_out_of_order_returns_conflict(client):
    run_id = client.post("/api/runs", json={"idea": "pickles", "lang": "en"}).json()["id"]

    response = client.post(f"/api/runs/{run_id}/purchase", json={"agreement_types": ["API_DPA"], "price": 1.0})

    assert response.status_code == 409


def test_purchase_needs_an_accepted_agreement(client):
    response = client.post("/api/runs/x/purchase", json={"agreement_types": [], "price": 1.0})

    assert response.status_code == 422


def test_premium_fee_is_returned_with_the_domain_list_and_the_chosen_domain(client, domains):
    from app.models import DomainOffer, PremiumFee

    fee = PremiumFee(type="ONE_TIME_PREMIUM_DOMAIN_PURCHASE", currency="USD", value=390000, amount=3900.0)
    domains.offers = [DomainOffer(name="achaar1.com", price=12.0, currency="USD", fees=[fee])]
    run_id = create(client).json()["id"]

    listed = client.get(f"/api/runs/{run_id}/domains").json()
    assert listed["domains"][0]["fees"] == [fee.model_dump()]

    # The chosen domain keeps the fee the user will see on the review screen.
    domains.confirm_available = lambda name: domains.offers[0]
    chosen = client.post(f"/api/runs/{run_id}/domain", json={"domain": "achaar1.com"}).json()
    assert chosen["domain"]["fees"][0]["amount"] == 3900.0
