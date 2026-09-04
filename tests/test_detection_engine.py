"""Tests for DetectionEngine module."""

import tempfile
from pathlib import Path

from common.events import FailureType
from detector.engine import DetectionEngine
from detector.storage import IncidentStorage
from tests.scenarios import (
    generate_mock_cpu_overload_telemetry,
    generate_mock_service_failure_telemetry,
)


def test_detection_engine_processing_and_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_engine.db"
        storage = IncidentStorage(db_path=db_path)
        engine = DetectionEngine(config_path="config/aegisos.yaml", storage=storage)

        telemetry = generate_mock_service_failure_telemetry(unit_name="crashed.service")

        # 1. First telemetry run -> 1 new incident
        incidents1 = engine.process_telemetry(telemetry)
        assert len(incidents1) == 1
        assert incidents1[0].failure_type == FailureType.SERVICE_FAILURE
        assert incidents1[0].affected_unit == "crashed.service"
        assert storage.count_incidents() == 1

        # 2. Second telemetry run within dedup window -> 0 new incidents
        incidents2 = engine.process_telemetry(telemetry)
        assert len(incidents2) == 0
        assert storage.count_incidents() == 1

        # 3. Telemetry run with different failure type -> 1 new incident
        cpu_telemetry = generate_mock_cpu_overload_telemetry(cpu_percent=96.0)
        incidents3 = engine.process_telemetry(cpu_telemetry)
        assert len(incidents3) == 1
        assert incidents3[0].failure_type == FailureType.CPU_OVERLOAD
        assert storage.count_incidents() == 2
