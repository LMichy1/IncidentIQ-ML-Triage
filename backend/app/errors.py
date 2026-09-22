"""Structured application errors, mapped to consistent JSON error responses
in main.py's exception handlers."""

from __future__ import annotations


class IncidentNotFoundError(Exception):
    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        super().__init__(f"Incident {incident_id!r} not found")


class ModelUnavailableError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Model unavailable: {reason}")
