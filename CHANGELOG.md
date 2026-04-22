# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open source release
- Support for 4 AAS components (AAS Repository, Submodel Repository, AAS Registry, Submodel Registry)
- OpenAPI-to-MCP bridge architecture
- Derived spec generation for specific implementations
- Runtime path filtering and overlay support
- Tool curation with allowlist and operation aliasing
- Read-only mode by default with optional write operations
- Configuration file support for curation settings
- Comprehensive test suite with 137+ test cases
- MCP Inspector integration for interactive testing
- Example configuration for SAP BNAC AAS Server

### Security
- No hardcoded credentials
- Environment variable-based authentication
- Input validation via OpenAPI schemas
- Pagination limits to prevent DoS
- Safe defaults (read-only mode)

## [0.1.0] - 2026-02-12

### Added
- Initial project structure
- Core MCP server implementation
- OpenAPI loader with filtering capabilities
- HTTP client with authentication support
- Tool curation module
- Command-line interface
- Documentation (README, CLAUDE.md, QUICKSTART)
- Test infrastructure
- Example OpenAPI specifications

[Unreleased]: https://github.com/SAP/aas-mcp-server/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SAP/aas-mcp-server/releases/tag/v0.1.0
