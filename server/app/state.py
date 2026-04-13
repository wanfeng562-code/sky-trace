from app.services.flight_store import FlightStore
from app.services.mock_collector import MockCollector
from app.services.unified_pipeline import UnifiedDataPipeline

# Shared process-level objects.
flight_store = FlightStore()
mock_collector = MockCollector()
unified_pipeline = UnifiedDataPipeline(flight_store=flight_store, mock_collector=mock_collector)
