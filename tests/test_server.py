# SPDX-FileCopyrightText: 2026 SAP SE or an SAP affiliate company and aas-mcp-server contributors
# SPDX-License-Identifier: Apache-2.0

"""
Tests for server module.

Tests the MCP server builder orchestration.
"""

from unittest.mock import MagicMock, patch

from aas_mcp_server.server import (
    build_mcp_server,
    DEFAULT_LOG_LEVEL,
    DEFAULT_COMPONENT_NAME,
    SERVER_NAME_FORMAT,
)


class TestBuildMcpServer:
    """Tests for build_mcp_server function."""

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_calls_configure_logging_with_provided_level(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that configure_logging is called with provided log level."""
        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
            log_level="DEBUG",
        )

        mock_configure_logging.assert_called_once_with("DEBUG")

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_calls_configure_logging_with_default_level(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that configure_logging uses default log level when not provided."""
        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
        )

        mock_configure_logging.assert_called_once_with(DEFAULT_LOG_LEVEL)

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_loads_openapi_spec_with_component_name(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that load_and_process_openapi is called with correct arguments."""
        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
            component_name="aas-repo",
        )

        mock_load_openapi.assert_called_once_with("test.yaml", "aas-repo")

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_loads_openapi_spec_with_default_component(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that load_and_process_openapi uses default component name."""
        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
        )

        mock_load_openapi.assert_called_once_with("test.yaml", DEFAULT_COMPONENT_NAME)

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_curates_spec_with_enable_writes_false(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that curate_openapi_spec is called with enable_writes=False."""
        mock_spec = {"paths": {}}
        mock_load_openapi.return_value = mock_spec

        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
        )

        mock_curate.assert_called_once_with(mock_spec, enable_writes=False, curation_settings=None)

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_curates_spec_with_enable_writes_true(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that curate_openapi_spec is called with enable_writes=True."""
        mock_spec = {"paths": {}}
        mock_load_openapi.return_value = mock_spec

        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=True,
        )

        mock_curate.assert_called_once_with(mock_spec, enable_writes=True, curation_settings=None)

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_builds_http_client_with_base_url(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that build_async_client is called with correct base_url."""
        build_mcp_server(
            base_url="http://prod-server:9000",
            openapi_path="test.yaml",
            enable_writes=False,
        )

        mock_build_client.assert_called_once_with(base_url="http://prod-server:9000")

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_creates_fastmcp_server_with_curated_spec(
        self,
        mock_fastmcp_class,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that FastMCP.from_openapi is called with curated spec."""
        mock_spec = {"paths": {}}
        mock_curated_spec = {"paths": {"/shells": {}}}
        mock_load_openapi.return_value = mock_spec
        mock_curate.return_value = mock_curated_spec
        mock_client = MagicMock()
        mock_build_client.return_value = mock_client

        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
            component_name="aas-repo",
        )

        mock_fastmcp_class.from_openapi.assert_called_once_with(
            openapi_spec=mock_curated_spec,
            client=mock_client,
            name=SERVER_NAME_FORMAT.format(component_name="aas-repo"),
        )

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_returns_fastmcp_instance(
        self,
        mock_fastmcp_class,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that build_mcp_server returns a FastMCP instance."""
        mock_mcp_instance = MagicMock()
        mock_fastmcp_class.from_openapi.return_value = mock_mcp_instance

        result = build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
        )

        assert result == mock_mcp_instance

    @patch("aas_mcp_server.server.configure_logging")
    @patch("aas_mcp_server.server.load_and_process_openapi")
    @patch("aas_mcp_server.server.curate_openapi_spec")
    @patch("aas_mcp_server.server.build_async_client")
    @patch("aas_mcp_server.server.FastMCP")
    def test_pipeline_execution_order(
        self,
        mock_fastmcp,
        mock_build_client,
        mock_curate,
        mock_load_openapi,
        mock_configure_logging,
    ):
        """Test that pipeline steps execute in correct order."""
        call_order = []

        def track_configure_logging(*args):
            call_order.append("configure_logging")

        def track_load_openapi(*args):
            call_order.append("load_openapi")
            return {"paths": {}}

        def track_curate(*args, **kwargs):
            call_order.append("curate")
            return {"paths": {}}

        def track_build_client(*args, **kwargs):
            call_order.append("build_client")
            return MagicMock()

        def track_fastmcp(*args, **kwargs):
            call_order.append("fastmcp")
            return MagicMock()

        mock_configure_logging.side_effect = track_configure_logging
        mock_load_openapi.side_effect = track_load_openapi
        mock_curate.side_effect = track_curate
        mock_build_client.side_effect = track_build_client
        mock_fastmcp.from_openapi.side_effect = track_fastmcp

        build_mcp_server(
            base_url="http://localhost:8080",
            openapi_path="test.yaml",
            enable_writes=False,
        )

        assert call_order == [
            "configure_logging",
            "load_openapi",
            "curate",
            "build_client",
            "fastmcp",
        ]


class TestConstants:
    """Tests for module constants."""

    def test_default_log_level_is_info(self):
        """Test that default log level is INFO."""
        assert DEFAULT_LOG_LEVEL == "INFO"

    def test_default_component_name_is_aas_repo(self):
        """Test that default component name is aas-repo."""
        assert DEFAULT_COMPONENT_NAME == "aas-repo"

    def test_server_name_format_has_placeholder(self):
        """Test that server name format has component_name placeholder."""
        assert "{component_name}" in SERVER_NAME_FORMAT

    def test_server_name_format_produces_correct_name(self):
        """Test that server name format produces expected string."""
        result = SERVER_NAME_FORMAT.format(component_name="test-component")
        assert "AAS MCP Server" in result
        assert "test-component" in result
