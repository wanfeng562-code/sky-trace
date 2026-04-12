from app.services.flight_store import FlightStore
from app.services.mock_collector import MockCollector

# Shared process-level objects.
flight_store = FlightStore()
mock_collector = MockCollector()
