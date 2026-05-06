# CHANGELOG

<!-- version list -->

## v1.7.0 (2026-05-06)

### Features

- **client**: Support FIREFLY_III_VERIFY_SSL to allow self-signed certs
  ([`22fd124`](https://github.com/Armgd/firefly-iii-mcp/commit/22fd12491ba2ed47e421ad7570721bdb696e87a6))


## v1.6.0 (2026-05-06)

### Bug Fixes

- **prompts**: Drop deferred annotations on prompt modules
  ([`0976bad`](https://github.com/Armgd/firefly-iii-mcp/commit/0976badad100bcc5ae8d08cf1372d57f3d6cc4b6))

### Documentation

- **plans**: Implementation plan for prompt set rewrite
  ([`bc7c4c3`](https://github.com/Armgd/firefly-iii-mcp/commit/bc7c4c3d821e1f3fea12d0f817b4af4361028b36))

- **prompts**: Design for hybrid prompt set (9 macro playbooks + 6 baseline templates)
  ([`004a37b`](https://github.com/Armgd/firefly-iii-mcp/commit/004a37bc0b240df24c3fbaed761d67f0c505579e))

- **prompts**: Note future-annotations constraint
  ([`d3a0881`](https://github.com/Armgd/firefly-iii-mcp/commit/d3a08811e69c82d33eb5a2211f8f99a24df60fcf))

### Features

- **prompts**: Add 9 macro methodology playbooks
  ([`ede8e65`](https://github.com/Armgd/firefly-iii-mcp/commit/ede8e656edac2f522cf9a544bc27d1daa3650f06))

- **prompts**: Add baseline question templates
  ([`6c2933b`](https://github.com/Armgd/firefly-iii-mcp/commit/6c2933b73dd31bd193b5ed60dc288f8af339695a))

- **prompts**: Add prompts package skeleton
  ([`799a830`](https://github.com/Armgd/firefly-iii-mcp/commit/799a830675e5258fd78df624377f1cb79155df67))

- **prompts**: Add shared methodology constants and body composer
  ([`8bf9f11`](https://github.com/Armgd/firefly-iii-mcp/commit/8bf9f114f74c3a1411822008460e94cdfe0fe162))

### Refactoring

- **server**: Wire new prompt modules and drop inline prompts
  ([`128ee75`](https://github.com/Armgd/firefly-iii-mcp/commit/128ee7577aab6fe286f78ecd7504862c95b63ff0))


## v1.5.0 (2026-05-05)

### Features

- Rebuild MCP server with explicit tool handlers
  ([`b1ec65d`](https://github.com/Armgd/fireflyiii-mcp/commit/b1ec65d3791ea625ea894185c4064485443c29de))


## v1.4.0 (2025-08-14)

### Chores

- **dependencies**: Update fastmcp dependency to version 2.11 for improvements and bug fixes
  ([`a49c430`](https://github.com/Armgd/fireflyiii-mcp/commit/a49c430211074b9f982da736cf9b23c38668d22e))

### Features

- **.env.example**: Add example environment file to guide configuration
  ([`8d0f14e`](https://github.com/Armgd/fireflyiii-mcp/commit/8d0f14e5e62a22704689ab97e4a5d73875cb5531))

- **Dockerfile**: Change CMD to use uvicorn for better performance and concurrency in serving the
  application
  ([`ea96a48`](https://github.com/Armgd/fireflyiii-mcp/commit/ea96a48cb4aa7112a58e73061af13d84e58b71d3))

- **docs**: Add GEMINI.md file to provide project overview and setup instructions for the MCP server
  ([`b92b7c0`](https://github.com/Armgd/fireflyiii-mcp/commit/b92b7c0c7e638b88f4b533d2f8950054dfd07243))

- **main.py**: Add health check endpoint to verify server status
  ([`309611b`](https://github.com/Armgd/fireflyiii-mcp/commit/309611b1f6becf5a33874934245d6a699269384c))


## v1.3.0 (2025-08-13)

### Features

- Enhance GitHub Actions workflow to include Docker Buildx setup and configuration validation
  ([`58aea99`](https://github.com/Armgd/fireflyiii-mcp/commit/58aea99e49f501ec954cbee7f22b8514b6b900e3))


## v1.2.0 (2025-08-07)

### Chores

- **build.yaml**: Refactor GitHub Actions workflow for better tagging conventions and organization
  ([`6b8a9e5`](https://github.com/Armgd/fireflyiii-mcp/commit/6b8a9e5539a77838d156bb5120223c0c56bd7ab8))

- **ci**: Update Docker image name in GitHub Actions workflow to reflect correct repository name for
  building process
  ([`a71e5ca`](https://github.com/Armgd/fireflyiii-mcp/commit/a71e5ca38e222b02b85afa12b6b08ea7416dd9f3))

### Continuous Integration

- **workflow**: Enhance Docker build workflow for better tag management and conditional DockerHub
  login
  ([`cf54f11`](https://github.com/Armgd/fireflyiii-mcp/commit/cf54f11eaa4359f14bf5081431ca7d9466289dcc))

### Features

- **gemini**: Add Gemini CLI and related workflows for automated issue triage and PR review
  processes to improve repository maintenance efficiency.
  ([`841e0d9`](https://github.com/Armgd/fireflyiii-mcp/commit/841e0d957512be99b672ed27e675481ebf28a882))


## v1.1.0 (2025-07-15)

### Bug Fixes

- **pyproject.toml**: Update uv dependency version from 0.7.12 to 0.7.21 to ensure compatibility and
  receive bug fixes
  ([`184f0af`](https://github.com/Armgd/fireflyiii-mcp/commit/184f0afda1d5b1dba2bd3c16a6f71b20bdeb8d8e))

### Features

- **github**: Add a GitHub Actions workflow for linting with Ruff
  ([`c3c166d`](https://github.com/Armgd/fireflyiii-mcp/commit/c3c166d7d33750caacefad5e8e6b4d2826ed4383))

- **pyproject.toml**: Add dev dependency group for ruff to improve linting process
  ([`92d8ba4`](https://github.com/Armgd/fireflyiii-mcp/commit/92d8ba4f9ea3f81baf076c96af9b4dd9d115b690))


## v1.0.0 (2025-07-15)

- Initial Release
