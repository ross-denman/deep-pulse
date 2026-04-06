#!/usr/bin/env python3
"""
Deep Pulse — CLI Smoke Tests
"""

import unittest
import os
import asyncio
from src.core.identity import IdentityManager
from src.core.config import ConfigManager

class TestPulseNode(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager()
        self.identity = IdentityManager()

    def test_identity_exists(self):
        """Verify that a node identity is present."""
        node_id = self.identity.load_identity()
        self.assertIsNotNone(node_id, "Node ID should be initialized.")
        self.assertTrue(node_id.startswith("0x"), "Node ID should follow the 0x format.")

    def test_config_loading(self):
        """Verify that LLM configuration is loaded."""
        llm_config = self.config.get_llm_config()
        self.assertIn("provider", llm_config)
        self.assertIn("model", llm_config)

    def test_perimeter_loading(self):
        """Verify that a perimeter YAML can be parsed."""
        import yaml
        yaml_path = "templates/perimeters/technology.yaml"
        self.assertTrue(os.path.exists(yaml_path))
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
            self.assertEqual(data["id"], "tech_maneuvers")
            self.assertIn("Stargate", data["name"])

if __name__ == "__main__":
    unittest.main()
