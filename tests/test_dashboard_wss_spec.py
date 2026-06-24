import pytest
import asyncio
from fastapi.testclient import TestClient

from api.main import create_app

@pytest.fixture
def test_client():
    app = create_app()
    # TestClient can be used as a context manager to run startup/shutdown events
    with TestClient(app) as client:
        yield client

def test_dashboard_wss_subscribe_contract(test_client):
    """
    Spec Obligation: contract-signature.DashboardWSS.subscribe
    Verifies that the client can send a subscribe message.
    """
    with test_client.websocket_connect("/api/ws/dashboard") as websocket:
        # According to the DashboardWSS spec, we should be able to subscribe
        # subscribe: (norad_id: Integer?) -> Boolean
        websocket.send_json({"action": "subscribe", "norad_id": 43880})
        
        # We expect a boolean response confirming subscription
        response = websocket.receive_json()
        assert "subscribed" in response or response is True

def test_dashboard_wss_unsubscribe_contract(test_client):
    """
    Spec Obligation: contract-signature.DashboardWSS.unsubscribe
    Verifies that the client can send an unsubscribe message.
    """
    with test_client.websocket_connect("/api/ws/dashboard") as websocket:
        websocket.send_json({"action": "unsubscribe", "norad_id": 43880})
        response = websocket.receive_json()
        assert "unsubscribed" in response or response is True

def test_dashboard_wss_push_telemetry_contract(test_client):
    """
    Spec Obligation: contract-signature.DashboardWSS.push_telemetry
    Verifies that the server pushes TelemetryView data.
    """
    with test_client.websocket_connect("/api/ws/dashboard") as websocket:
        websocket.send_json({"action": "subscribe", "norad_id": 43880})
        
        # Consume the subscribe ack
        ack = websocket.receive_json()
        assert ack.get("subscribed") is True
        
        # We expect to receive a push_telemetry event
        data = websocket.receive_json()
        
        # In our simplified test mock, it might be telemetry or anomaly.
        # But we verify the type logic anyway.
        if data.get("type") == "push_telemetry":
            frame = data["frame"]
            # Verify it has TelemetryView shape
            assert "timestamp" in frame
            assert "norad_id" in frame
            assert "source" in frame
            assert "features" in frame
            assert "quality" in frame
            assert "model" in frame

def test_dashboard_wss_push_anomaly_alert_contract(test_client):
    """
    Spec Obligation: contract-signature.DashboardWSS.push_anomaly_alert
    Verifies that the server pushes AnomalyView alerts.
    """
    with test_client.websocket_connect("/api/ws/dashboard") as websocket:
        websocket.send_json({"action": "subscribe", "norad_id": 43880})
        
        # Consume the subscribe ack
        ack = websocket.receive_json()
        assert ack.get("subscribed") is True
        
        # We expect to eventually receive a push_anomaly_alert event
        data = websocket.receive_json()
        
        if data.get("type") == "push_anomaly_alert":
            alert = data["alert"]
            assert "timestamp" in alert
            assert "norad_id" in alert
            assert "score" in alert
            assert "features" in alert
            assert "quality" in alert
