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
    assert chosen["state"] == "site_generated"

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
