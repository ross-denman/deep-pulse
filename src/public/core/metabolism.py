#!/usr/bin/env python3
"""
The Chronicle - Resource Metabolism (Grid Tracking)

Tracks the 'Physiological Signals' of the regional infrastructure:
- Power Consumption (MW)
- Water Draw (MGD)
- Wastewater Capacity (MGD)

This module implements the 'Metabolic Signals' for the LEAP District audit,
allowing the mesh to detect 'Industrial Hunger' before it is public.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("metabolism")

# ─── Metabolism Models ───────────────────────────────────────────

class MetabolismPulse(BaseModel):
    """A point-in-time measurement of a resource grid."""
    resource: str  # 'power', 'water', 'wastewater'
    value: float
    unit: str      # 'MW', 'MGD'
    location: str  # 'Boone County', 'Lebanon', 'LEAP'
    source_cid: str # CID of the Public Chronicle entry providing this data
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GridState(BaseModel):
    """Current state and capacity of a specific grid."""
    resource: str
    current_load: float
    total_capacity: float
    utilization: float = 0.0

# ─── Metabolism Manager ──────────────────────────────────────────

class MetabolismManager:
    """Manages the tracking of resource consumption and grid capacity."""

    def __init__(self):
        self._pulses: List[MetabolismPulse] = []
        self._grid_caps: Dict[str, float] = {
            "power": 1000.0,   # Initial bootstrap assumption (MW)
            "water": 20.0,     # MGD
            "wastewater": 15.0 # MGD
        }

    def record_pulse(self, pulse: MetabolismPulse):
        """Record a new metabolism signal from the mesh."""
        self._pulses.append(pulse)
        logger.info(
            "Recorded metabolic pulse: %s %f %s at %s",
            pulse.resource, pulse.value, pulse.unit, pulse.location
        )
        
        # Check for capacity alerts
        self._check_capacity_alerts(pulse)

    def _check_capacity_alerts(self, pulse: MetabolismPulse):
        """Check if the latest pulse exceeds known grid capacity."""
        cap = self._grid_caps.get(pulse.resource.lower())
        if cap and pulse.value > cap:
            logger.warning(
                "🚨 GRID CAPACITY EXCEEDED: %s load %f%s exceeds cap %f%s",
                pulse.resource, pulse.value, pulse.unit, cap, pulse.unit
            )

    def get_grid_state(self, resource: str) -> Optional[GridState]:
        """Calculate the current state of a resource grid based on recent pulses."""
        recent_pulses = [p for p in self._pulses if p.resource.lower() == resource.lower()]
        if not recent_pulses:
            return None
            
        load = sum(p.value for p in recent_pulses[-3:]) / 3 # Sliding average of last 3
        cap = self._grid_caps.get(resource.lower(), 1.0)
        
        return GridState(
            resource=resource,
            current_load=load,
            total_capacity=cap,
            utilization=(load / cap) * 100
        )

# ─── Global Instance ──────────────────────────────────────────────
metabolism = MetabolismManager()
