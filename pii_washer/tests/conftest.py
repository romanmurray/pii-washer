"""Shared pytest fixtures for the PII-Washer test suite."""

import pytest


class MockDetectionEngine:
    """Lightweight mock that returns predictable detections without spaCy.

    The real Presidio+spaCy engine pulls a ~560MB model and is slow to init,
    so unit/integration tests inject this instead. It finds a fixed set of
    known PII strings by substring match.
    """

    def detect(self, text, confidence_threshold=0.3, language="en"):
        detections = []
        counter = 1
        test_patterns = [
            ("John Smith", "NAME"),
            ("Jane Doe", "NAME"),
            ("john@example.com", "EMAIL"),
            ("(555) 123-4567", "PHONE"),
            ("219-09-9999", "SSN"),
            ("Springfield", "ADDRESS"),
        ]
        for value, category in test_patterns:
            start = 0
            while True:
                pos = text.find(value, start)
                if pos == -1:
                    break
                detections.append({
                    "id": f"pii_{counter:03d}",
                    "category": category,
                    "original_value": value,
                    "positions": [{"start": pos, "end": pos + len(value)}],
                    "confidence": 0.85,
                })
                counter += 1
                start = pos + len(value)
        return detections


@pytest.fixture
def mock_engine():
    return MockDetectionEngine()
