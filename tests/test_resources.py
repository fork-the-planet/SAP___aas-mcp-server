# SPDX-FileCopyrightText: 2026 SAP SE or an SAP affiliate company and aas-mcp-server contributors
# SPDX-License-Identifier: Apache-2.0

"""
Tests for resources module.

Tests resource descriptions and documentation strings.
"""

from aas_mcp_server.resources import (
    AAS_MCP_RESOURCE_INTRO,
    ENV_VAR_ENABLE_WRITES,
    ENV_VAR_ENABLE_WRITES_VALUE,
)


class TestResourceStrings:
    """Tests for resource description strings."""

    def test_resource_intro_is_non_empty(self):
        """Test that resource intro string is not empty."""
        assert len(AAS_MCP_RESOURCE_INTRO) > 0

    def test_resource_intro_is_string(self):
        """Test that resource intro is a string."""
        assert isinstance(AAS_MCP_RESOURCE_INTRO, str)

    def test_resource_intro_mentions_readonly_default(self):
        """Test that resource intro mentions readonly-by-default behavior."""
        assert "readonly" in AAS_MCP_RESOURCE_INTRO.lower() or "read-only" in AAS_MCP_RESOURCE_INTRO.lower()

    def test_resource_intro_mentions_enable_writes_env_var(self):
        """Test that resource intro mentions the enable writes env var."""
        assert ENV_VAR_ENABLE_WRITES in AAS_MCP_RESOURCE_INTRO

    def test_resource_intro_mentions_enable_writes_value(self):
        """Test that resource intro mentions how to enable writes."""
        assert ENV_VAR_ENABLE_WRITES_VALUE in AAS_MCP_RESOURCE_INTRO

    def test_resource_intro_mentions_pagination_limit(self):
        """Test that resource intro mentions pagination limit."""
        assert "limit" in AAS_MCP_RESOURCE_INTRO.lower() or "pagination" in AAS_MCP_RESOURCE_INTRO.lower()

    def test_resource_intro_is_formatted_correctly(self):
        """Test that resource intro can be used as documentation."""
        # Should not have leading/trailing whitespace issues
        lines = AAS_MCP_RESOURCE_INTRO.split("\n")
        # All lines should be present (not just empty)
        assert any(len(line.strip()) > 0 for line in lines)


class TestConstants:
    """Tests for module constants."""

    def test_env_var_enable_writes_is_correct(self):
        """Test that enable writes env var name is correct."""
        assert ENV_VAR_ENABLE_WRITES == "AAS_MCP_ENABLE_WRITES"

    def test_env_var_enable_writes_value_is_correct(self):
        """Test that enable writes value is '1'."""
        assert ENV_VAR_ENABLE_WRITES_VALUE == "1"

    def test_env_var_names_match_across_modules(self):
        """Test that env var names are consistent with other modules."""
        # This constant should match what's used in cli.py
        from aas_mcp_server.cli import ENV_VAR_AAS_MCP_ENABLE_WRITES

        assert ENV_VAR_ENABLE_WRITES == ENV_VAR_AAS_MCP_ENABLE_WRITES
