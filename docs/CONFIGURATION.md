# Configuration Reference: HomeCare Agentic Framework

The framework is configured via environment variables, an `.env` file, or command-line flags.

---

## 1. Environment Variables

| Variable | Type | Default | Required | Description |
| -------- | ---- | ------- | -------- | ----------- |
| `OPENROUTER_API_KEY` | String | - | **Yes** | Your OpenRouter API key. |
| `OPENROUTER_MODEL` | String | `""` | No | Default fallback LLM model (e.g. `anthropic/claude-sonnet-4`). |
| `MODEL_ARCHITECTURE` | String | `""` | No | High-reasoning model for Architecture Analysis, Strategy, and ADRs (defaults to `OPENROUTER_MODEL`). |
| `MODEL_CODE` | String | `""` | No | Medium/low-cost model for Work Package code synthesis and test generation (e.g. `deepseek/deepseek-coder`). |
| `MODEL_REVIEW` | String | `""` | No | Model for pre-implementation and PR code reviews (defaults to `MODEL_ARCHITECTURE`). |
| `MODEL_INTAKE` | String | `""` | No | Model for feature intake and clarification loops. |
| `NODE_MODELS` | Dict/JSON | `{}` | No | Granular per-node mapping overriding specific LangGraph node names. |
| `OPENROUTER_VISION_MODEL` | String | `""` | No | Model used for wireframe analysis. Defaults to `OPENROUTER_MODEL`. |
| `OPENROUTER_BASE_URL` | String | `https://openrouter.ai/api/v1` | No | API endpoint for OpenRouter. |
| `MAX_TOKENS` | Integer | `16384` | No | Maximum token response budget per generation call. |
| `TEMPERATURE` | Float | `0.1` | No | Sampling temperature (low for code determinism). |
| `GITHUB_AUTH_MODE` | String | `pat` | No | `pat` for Personal Access Token, or `github_app`. |
| `GITHUB_TOKEN` | String | `""` | Optional | GitHub PAT with repo scope. |
| `GITHUB_APP_ID` | Integer | `0` | Optional | App ID for GitHub App auth. |
| `GITHUB_APP_PRIVATE_KEY_PATH`| Path | `""` | Optional | Path to `.pem` private key. |
| `GITHUB_APP_INSTALLATION_ID` | Integer | `0` | Optional | Installation ID for GitHub App. |
| `REPO_PATH` | Path | `.` | No | Local path to the target repository. |
| `REPO_URL` | String | `""` | No | Remote GitHub repository URL. |
| `REPO_DEFAULT_BRANCH` | String | `main` | No | Base branch name for feature branches and PRs. |
| `EXECUTION_MODE` | String | `parallel` | No | `parallel` (within waves) or `sequential`. |
| `MAX_PARALLEL_WORKERS` | Integer | `5` | No | Concurrency limit for parallel work package execution. |
| `MAX_RETRIES` | Integer | `3` | No | Retries for failed builds or LLM calls. |
| `CLARIFICATION_MODE` | String | `cli` | No | `cli` for terminal prompts or `web` for browser UI. |
| `LANGFUSE_ENABLED` | Boolean | `false` | No | Enables Langfuse execution tracing. |
| `LANGFUSE_PUBLIC_KEY` | String | `""` | Optional | Langfuse public project key. |
| `LANGFUSE_SECRET_KEY` | String | `""` | Optional | Langfuse secret project key. |
| `LANGFUSE_HOST` | String | `https://cloud.langfuse.com` | No | Langfuse backend host. |
| `GRADIO_SERVER_NAME` | String | `127.0.0.1` | No | Binding host for Web UI. |
| `GRADIO_SERVER_PORT` | Integer | `7860` | No | Port for Web UI. |
| `LOG_LEVEL` | String | `INFO` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

---

## 2. Model Selection Recommendations

| Model Identifier | Best Used For | Notes |
| ---------------- | ------------- | ----- |
| `anthropic/claude-sonnet-4` | Architecture, Code Review, Complex Logic | Exceptional reasoning and strict following of constraints. |
| `openai/gpt-4o` | Wireframe Vision Analysis & Strategy | Fast multimodal understanding and structured JSON. |
| `deepseek/deepseek-coder` | High-throughput Code Generation | Cost-effective generation for large repetitive files. |
