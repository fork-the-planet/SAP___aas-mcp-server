"""
Tests for cli module.

Tests command-line interface argument parsing and configuration.
"""

import os
from unittest.mock import MagicMock, patch

from aas_mcp_server.cli import (
    main,
    COMPONENT_CONFIGS,
    ENV_VAR_MCP_TRANSPORT,
    ENV_VAR_AAS_MCP_ENABLE_WRITES,
    ENV_VAR_LOG_LEVEL,
    ENV_VAR_AAS_BASE_URL,
    ENV_VAR_AAS_OPENAPI_PATH,
    DEFAULT_TRANSPORT,
    DEFAULT_LOG_LEVEL,
    ENABLE_WRITES_TRUE_VALUE,
    CLI_PROGRAM_NAME,
    CONFIG_KEY_OPENAPI,
    CONFIG_KEY_DEFAULT_URL,
    CONFIG_KEY_DESCRIPTION,
)


class TestComponentConfigs:
    """Tests for COMPONENT_CONFIGS structure."""

    def test_has_aas_repo_component(self):
        """Test that aas-repo component is configured."""
        assert "aas-repo" in COMPONENT_CONFIGS

    def test_has_submodel_repo_component(self):
        """Test that submodel-repo component is configured."""
        assert "submodel-repo" in COMPONENT_CONFIGS

    def test_has_aas_registry_component(self):
        """Test that aas-registry component is configured."""
        assert "aas-registry" in COMPONENT_CONFIGS

    def test_has_submodel_registry_component(self):
        """Test that submodel-registry component is configured."""
        assert "submodel-registry" in COMPONENT_CONFIGS

    def test_each_component_has_openapi_path(self):
        """Test that each component has openapi specification path."""
        for component_name, config in COMPONENT_CONFIGS.items():
            assert CONFIG_KEY_OPENAPI in config
            assert isinstance(config[CONFIG_KEY_OPENAPI], str)
            assert len(config[CONFIG_KEY_OPENAPI]) > 0

    def test_each_component_has_default_url(self):
        """Test that each component has default URL."""
        for component_name, config in COMPONENT_CONFIGS.items():
            assert CONFIG_KEY_DEFAULT_URL in config
            assert isinstance(config[CONFIG_KEY_DEFAULT_URL], str)
            assert config[CONFIG_KEY_DEFAULT_URL].startswith("http")

    def test_each_component_has_description(self):
        """Test that each component has description."""
        for component_name, config in COMPONENT_CONFIGS.items():
            assert CONFIG_KEY_DESCRIPTION in config
            assert isinstance(config[CONFIG_KEY_DESCRIPTION], str)
            assert len(config[CONFIG_KEY_DESCRIPTION]) > 0

    def test_components_have_unique_default_ports(self):
        """Test that components have unique default ports."""
        urls = [config[CONFIG_KEY_DEFAULT_URL] for config in COMPONENT_CONFIGS.values()]
        # Extract ports (e.g., http://localhost:8080 -> 8080)
        ports = [url.split(":")[-1] for url in urls]
        assert len(ports) == len(set(ports))  # All unique


class TestMain:
    """Tests for main CLI function."""

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo"])
    def test_main_builds_server_with_component_defaults(self, mock_build_server):
        """Test that main builds server with component default values."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        expected_config = COMPONENT_CONFIGS["aas-repo"]
        mock_build_server.assert_called_once_with(
            base_url=expected_config[CONFIG_KEY_DEFAULT_URL],
            openapi_path=expected_config[CONFIG_KEY_OPENAPI],
            enable_writes=False,
            log_level=DEFAULT_LOG_LEVEL,
            component_name="aas-repo",
            curation_settings=None,
        )
        mock_mcp.run.assert_called_once_with(transport=DEFAULT_TRANSPORT)

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo", "--base-url", "http://custom:9000"])
    def test_main_uses_custom_base_url_from_arg(self, mock_build_server):
        """Test that main uses custom base URL from command line."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["base_url"] == "http://custom:9000"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch.dict(os.environ, {ENV_VAR_AAS_BASE_URL: "http://env-server:8888"})
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo"])
    def test_main_uses_base_url_from_env(self, mock_build_server):
        """Test that main uses base URL from environment variable."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["base_url"] == "http://env-server:8888"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch.dict(os.environ, {ENV_VAR_AAS_BASE_URL: "http://env-server:8888"})
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo", "--base-url", "http://arg-server:7777"])
    def test_main_prioritizes_arg_over_env_for_base_url(self, mock_build_server):
        """Test that command line arg takes precedence over env var."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["base_url"] == "http://arg-server:7777"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo", "--openapi", "custom-spec.yaml"])
    def test_main_uses_custom_openapi_path_from_arg(self, mock_build_server):
        """Test that main uses custom OpenAPI path from command line."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["openapi_path"] == "custom-spec.yaml"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch.dict(os.environ, {ENV_VAR_AAS_OPENAPI_PATH: "env-spec.yaml"})
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo"])
    def test_main_uses_openapi_path_from_env(self, mock_build_server):
        """Test that main uses OpenAPI path from environment variable."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["openapi_path"] == "env-spec.yaml"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo", "--enable-writes"])
    def test_main_enables_writes_from_arg(self, mock_build_server):
        """Test that main enables writes when flag is provided."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["enable_writes"] is True

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch.dict(os.environ, {ENV_VAR_AAS_MCP_ENABLE_WRITES: ENABLE_WRITES_TRUE_VALUE})
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo"])
    def test_main_enables_writes_from_env(self, mock_build_server):
        """Test that main enables writes from environment variable."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["enable_writes"] is True

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch.dict(os.environ, {ENV_VAR_AAS_MCP_ENABLE_WRITES: "0"})
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo"])
    def test_main_disables_writes_when_env_not_1(self, mock_build_server):
        """Test that writes are disabled when env var is not '1'."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["enable_writes"] is False

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo", "--log-level", "DEBUG"])
    def test_main_uses_custom_log_level_from_arg(self, mock_build_server):
        """Test that main uses custom log level from command line."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["log_level"] == "DEBUG"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch.dict(os.environ, {ENV_VAR_LOG_LEVEL: "WARNING"})
    @patch("sys.argv", ["aas-mcp-server", "--component", "aas-repo"])
    def test_main_uses_log_level_from_env(self, mock_build_server):
        """Test that main uses log level from environment variable."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["log_level"] == "WARNING"

    @patch("aas_mcp_server.cli.build_mcp_server")
    @patch("sys.argv", ["aas-mcp-server", "--component", "submodel-repo"])
    def test_main_works_with_different_components(self, mock_build_server):
        """Test that main works with different component choices."""
        mock_mcp = MagicMock()
        mock_build_server.return_value = mock_mcp

        main()

        call_args = mock_build_server.call_args
        assert call_args.kwargs["component_name"] == "submodel-repo"
        expected_config = COMPONENT_CONFIGS["submodel-repo"]
        assert call_args.kwargs["openapi_path"] == expected_config[CONFIG_KEY_OPENAPI]


class TestConstants:
    """Tests for module constants."""

    def test_env_var_names_are_correct(self):
        """Test that environment variable names are correct."""
        assert ENV_VAR_MCP_TRANSPORT == "MCP_TRANSPORT"
        assert ENV_VAR_AAS_MCP_ENABLE_WRITES == "AAS_MCP_ENABLE_WRITES"
        assert ENV_VAR_LOG_LEVEL == "LOG_LEVEL"
        assert ENV_VAR_AAS_BASE_URL == "AAS_BASE_URL"
        assert ENV_VAR_AAS_OPENAPI_PATH == "AAS_OPENAPI_PATH"

    def test_default_values_are_correct(self):
        """Test that default values are correct."""
        assert DEFAULT_TRANSPORT == "stdio"
        assert DEFAULT_LOG_LEVEL == "INFO"
        assert ENABLE_WRITES_TRUE_VALUE == "1"

    def test_cli_constants_are_correct(self):
        """Test that CLI constants are correct."""
        assert CLI_PROGRAM_NAME == "aas-mcp-server"
        assert "AAS" in str(COMPONENT_CONFIGS)  # CLI description mentions AAS

    def test_config_keys_are_correct(self):
        """Test that config key constants are correct."""
        assert CONFIG_KEY_OPENAPI == "openapi"
        assert CONFIG_KEY_DEFAULT_URL == "default_url"
        assert CONFIG_KEY_DESCRIPTION == "description"
