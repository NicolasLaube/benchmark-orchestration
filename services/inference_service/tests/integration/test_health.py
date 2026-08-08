async def test_health_live_returns_service_information(client) -> None:

    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "up"}
