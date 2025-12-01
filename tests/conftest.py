"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_config(tmp_path: Path) -> Path:
    """Create a sample config file for testing."""
    config_path = tmp_path / "config.yaml"
    config_content = """
target_ring:
  name: "Test Ring"
  style_number: "TEST001"
  metal: "10K Yellow Gold"
  stones:
    - "Amethyst"
    - "Seed Pearls"
  size: 7

marketplaces:
  - name: shopgoodwill
    enabled: true
    priority: 1
    searches:
      - "amethyst pearl ring"

  - name: ebay
    enabled: true
    priority: 2
    searches:
      - "vintage gold ring"

known_leads:
  - url: https://example.com/lead1
    note: Test lead

scoring:
  thresholds:
    high: 70
    medium: 40

rate_limiting:
  min_delay_seconds: 0.01
  max_delay_seconds: 0.02

output:
  base_dir: output
  logs_dir: logs
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output = tmp_path / "output"
    output.mkdir()
    return output
