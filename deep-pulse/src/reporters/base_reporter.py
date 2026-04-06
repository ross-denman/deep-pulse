#!/usr/bin/env python3
"""
Deep Pulse — Base Reporter

The abstract base class for intelligence delivery.
Manages the gather-format-deliver lifecycle.
"""

import abc
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BaseReporter(abc.ABC):
    """Abstract base class for intelligence reporters."""

    def __init__(self, bridge_client):
        self.bridge = bridge_client

    @abc.abstractmethod
    async def gather(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Gathers verified entries from the Ledger/Graph."""
        pass

    @abc.abstractmethod
    def format(self, entries: List[Dict[str, Any]]) -> Any:
        """Formats the data for the specific report type."""
        pass

    @abc.abstractmethod
    async def deliver(self, report: Any):
        """Delivers the report (CLI, file, webhook, etc)."""
        pass

    async def generate_report(self, criteria: Dict[str, Any]):
        """Executes the reporting workflow."""
        logger.info(f"Generating report with criteria: {criteria}")
        entries = await self.gather(criteria)
        if not entries:
            logger.info("No verified intelligence found for this report.")
            return

        formatted_report = self.format(entries)
        await self.deliver(formatted_report)
