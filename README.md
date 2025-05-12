# Athenyx - Enterprise AI Knowledge Platform

Athenyx is an AI-Powered Knowledge Graph system that indexes, connects, and queries software project information (code structure, semantics) using Neo4j, LangChain, LangGraph, Tree-sitter, FastAPI, and Streamlit.

**Vision:** Empower engineering teams with instant, contextual insights into their software systems across multiple repositories.

<div align="center">
  <a href="https://www.youtube.com/watch?v=TBjGveJrfo0">
    <img src="https://img.youtube.com/vi/TBjGveJrfo0/maxresdefault.jpg" alt="Athenyx - Enterprise AI Knowledge Platform" width="600" />
  </a>
  <br>
  <a href="https://www.youtube.com/watch?v=TBjGveJrfo0">
    <img src="https://img.shields.io/badge/▶-Watch_Video-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Watch Video" width="180">
  </a>
</div>

## Current Features

* **Multi-Repository Management:**
  * Add and manage multiple code repositories in one knowledge graph
  * Switch active repository context for targeted queries
  * Track ingestion progress for newly added repositories
* **Advanced Code Analysis:**
  * Ingests Git repositories (with branch selection)
  * Performs structural parsing (Files, Functions, Classes/Structs/Interfaces) for multiple languages:
    * Python
    * Go
    * C#
    * Java
    * JavaScript
* **Knowledge Processing:**
  * Chunks code into semantic units
  * Generates vector embeddings for code chunks (using OpenAI API or configurable for local models)
  * Loads structural data and vector embeddings into Neo4j (Graph + Vector Index)
* **Intelligent Interface:**
  * Provides a FastAPI backend API (`/api/query`)
  * Features a LangGraph agent orchestrating:
    * Retrieval-Augmented Generation (RAG) using semantic vector search on code chunks
    * Context-aware responses based on active repository
    * Web search via Tavily (optional, requires API key)
  * Streams the agent's final answer token-by-token
  * Offers a streamlined Streamlit web UI for interaction
* **Deployment Options:**
  * Includes Docker Compose setup for easier deployment
  * Supports local development environment

## Architecture Overview

* **Data Layer:** Neo4j (Graph Database + Vector Index)
* **Ingestion Layer:** Python scripts (`ingestion/`) using GitPython, Tree-sitter, Sentence-Transformers/OpenAI client, Neo4j driver
* **Processing/Query Layer:** LangChain & LangGraph (`app/agent/`) defining the agent workflow and tools
* **API Layer:** FastAPI (`app/main.py`, `app/api/`) serving the agent
* **Presentation Layer:** Streamlit (`ui/app.py`) providing the web interface

## Prerequisites

### Core Requirements (All Setups)

* [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* API Keys (Store in `.env` file):
  * `OPENAI_API_KEY`: Required for the LLM agent (e.g., GPT-4o-mini) and potentially embeddings if not using a local model. Get from [OpenAI Platform](https://platform.openai.com/api-keys).
  * `TAVILY_API_KEY`: Optional, only needed if you want the agent to perform web searches via Tavily. Get from [Tavily AI](https://tavily.com/).

### For Docker Execution (Recommended)

* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

### For Local Execution

* [Python](https://www.python.org/downloads/) >= 3.10
* [Poetry](https://python-poetry.org/docs/#installation) (Python dependency manager)
* **C/C++ Compiler:** Required by the `tree-sitter` package to build language grammars during `poetry install`.
  * *Linux (Debian/Ubuntu):* `sudo apt-get update && sudo apt-get install build-essential`
  * *macOS:* Install Xcode Command Line Tools: `xcode-select --install`
  * *Windows:* Install "Build Tools for Visual Studio" (select C++ build tools workload). Community version is free. Ensure compiler (`cl.exe`) is in your system's PATH. [See Python docs for details](https://wiki.python.org/moin/WindowsCompilers).
* **Neo4j Database Instance:** A running Neo4j database accessible from your local machine.
  * *Local:* Install [Neo4j Desktop](https://neo4j.com/download/) or Neo4j Community/Enterprise Server. Start the database. The default connection URI is usually `bolt://localhost:7687`.
  * *Cloud:* Use [Neo4j AuraDB](https://neo4j.com/cloud/platform/aura-database/) (offers a free tier). Create an instance and note its connection URI, username, and password.

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url> # Or the URL of this project
cd enterprise-ai     # Or your project directory name
```

### 2. Configure Environment (.env file)

Copy the example environment file:
```bash
# Linux/macOS
cp .env.example .env

# Windows CMD
copy .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Edit the `.env` file with your specific settings:
* `OPENAI_API_KEY`: Your key (required)
* `TAVILY_API_KEY`: Your key (optional)
* `NEO4J_URI`:
  * For Docker: Use `bolt://neo4j:7687` (connects to the Neo4j container)
  * For Local: Use your local/cloud Neo4j URI (e.g., `bolt://localhost:7687` or AuraDB URI)
* `NEO4J_USERNAME`: Your Neo4j username (default `neo4j`)
* `NEO4J_PASSWORD`: Your Neo4j password. Must match the one set in `docker-compose.yml` if using Docker
* `EMBEDDING_MODEL_NAME`: (If using local Sentence Transformers) e.g., `all-MiniLM-L6-v2`
* `EMBEDDING_DIMENSIONS`: Crucial. Set this to match your embedding model (e.g., 1536 for OpenAI `text-embedding-3-small`, 384 for `all-MiniLM-L6-v2`, 768 for `bge-base-en-v1.5`). The Neo4j index depends on this.
* `OPENAI_EMBEDDING_MODEL`: (If using OpenAI embeddings) e.g., `text-embedding-3-small`
* `OPENAI_LLM_MODEL`: The model for the agent, e.g., `gpt-4o-mini`
* `INGEST_REPO_URL`: Optional default Git URL of a repository you want to index (e.g., `https://github.com/GoogleCloudPlatform/microservices-demo.git`)
* `INGEST_TARGET_EXTENSIONS`: Comma-separated list of file extensions to process (e.g., `.py,.go,.cs,.java,.js`)
* `BACKEND_API_URL`:
  * For Docker: Use `http://backend:8000` (the frontend container connects to the backend container)
  * For Local: Use `http://localhost:8000` (the frontend process connects to the backend process)

### 3. Install Dependencies & Build Grammars

This step uses Poetry to install Python packages and attempts to build Tree-sitter grammars for the supported languages (Python, Go, C#, Java, JS).
Ensure C/C++ compiler prerequisite is met.

Run in the project root:
```bash
brew install python@3.12
export PATH="/usr/local/opt/python@3.12/bin:$PATH"
poetry env use python3.12
poetry install
```

Monitor Output: Check for errors during installation, especially during steps involving tree-sitter-languages or building specific grammars. If builds fail, consult the compiler setup instructions and Tree-sitter documentation.

## Running the Application

Choose one of the following methods:

### Option 1: Running with Docker (Recommended)

Manages Neo4j, backend, and frontend services together.

#### Build and Start Services

```bash
docker-compose up --build -d
```
* `-d`: Runs services in detached (background) mode
* `--build`: Rebuilds Docker images if code or Dockerfiles have changed

Wait ~1 minute for Neo4j to initialize on the first run. Check status: `docker-compose ps` or logs: `docker-compose logs neo4j`.

#### Access Services

* Frontend UI: http://localhost:8501
* Backend API Docs: http://localhost:8000/docs
* Neo4j Browser: http://localhost:7474 (Login with `NEO4J_USERNAME` / `NEO4J_PASSWORD` from `.env`)

#### Stopping Services

```bash
docker-compose down
```

To remove the Neo4j data volume (deletes all graph data): `docker-compose down -v`

### Option 2: Running Locally (Requires Manual Setup)

Requires managing the Neo4j instance and Python processes separately.

1. **Ensure Prerequisites**: Verify Python, Poetry, Compiler, and a running Neo4j instance are ready.

2. **Install Dependencies**: Run `poetry install` (if not already done). Check for Tree-sitter grammar build success.

3. **Configure .env**: Make sure `NEO4J_URI` points to your local/cloud Neo4j instance and `BACKEND_API_URL` is `http://localhost:8000`.

4. **Run Backend API**:
   * Open a new terminal
   * Run: `poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
   * Keep this terminal running

5. **Run Frontend UI**:
   * Open a third terminal
   * Run: `poetry run streamlit run ui/app.py --server.port 8501`
   * Keep this terminal running

6. **Access Services**:
   * Frontend UI: http://localhost:8501
   * Backend API Docs: http://localhost:8000/docs
   * Neo4j Browser: Access your local/cloud instance directly via its specific URL/port

## Using Athenyx

1. **Adding Repositories**:
   * Navigate to the Streamlit UI (usually http://localhost:8501)
   * In the sidebar, click "➕ Add New Repository"
   * Enter the repository URL (e.g., https://github.com/GoogleCloudPlatform/microservices-demo.git)
   * Optionally specify a branch and description
   * Click "Add Repository" and wait for ingestion to complete

2. **Managing Repositories**:
   * View all indexed repositories in the sidebar dropdown
   * Set the active repository by selecting it and clicking "Set as Active"
   * The active repository context is displayed at the top of the chat interface

3. **Querying the Knowledge Graph**:
   * Enter questions about the active repository in the chat input
   * The AI assistant will respond with information scoped to the active repository
   * Questions can be about architecture, code structure, functionality, or specific files/components

4. **Starting New Conversations**:
   * Click "New Chat" to reset the conversation history
   * Repository context is maintained across new chats

## Development

* **Docker**: If using `docker-compose up`, changes to Python files within the project directory (mounted into `/app`) should trigger automatic reloading for both the Uvicorn (backend) and Streamlit (frontend) servers. If you change dependencies (`pyproject.toml`) or the Dockerfile, you'll need to rebuild the images (`docker-compose build` or `docker-compose up --build`).
* **Local**: Both `uvicorn --reload` and `streamlit run` automatically watch for changes in the relevant Python files and reload the servers.

## Troubleshooting Common Issues

* **ModuleNotFoundError**: Usually means a dependency is missing. Run `poetry install`. Check `pyproject.toml`.
* **Tree-sitter Build Errors**: Ensure C/C++ compiler is installed and accessible in your PATH. Consult tree-sitter and tree-sitter-languages documentation.
* **API Key Errors (OpenAI/Tavily)**: Double-check variable names (`OPENAI_API_KEY`, `TAVILY_API_KEY`) and values in your `.env` file. Ensure the file is saved and located in the project root.
* **Neo4j Connection Errors**: Verify `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `.env` match your running Neo4j instance. Ensure Neo4j is running and accessible (check firewall if needed). If using Docker, ensure the Neo4j container is healthy (`docker-compose ps`).
* **NameResolutionError: Failed to resolve 'backend' (UI)**: You are likely running the UI locally but `BACKEND_API_URL` in `.env` is set to `http://backend:8000` (for Docker). Change it to `http://localhost:8000` for local runs.
* **Embedding Dimension Errors**: Ensure `EMBEDDING_DIMENSIONS` in `.env` matches the output dimension of your chosen embedding model. If you change models/dimensions, you may need to DROP the old vector index in Neo4j (`DROP INDEX code_chunk_embeddings`) before re-running ingestion.
* **Rate Limit Errors (OpenAI)**: The embedding step may take time or fail if you process large repositories. Solutions: Add delays (`ingestion/processing/embedding.py`), filter input files (`ingestion/main.py`), request higher OpenAI limits, or switch to a local embedding model.
* **Repository Not Showing After Adding**: The UI automatically refreshes after adding a repository, but you can manually refresh by clicking "Check Status" in the ingestion progress area.

## Project Structure (Brief)

* `app/`: FastAPI backend, agent logic, database interactions
* `ingestion/`: Scripts and modules for data ingestion pipeline
* `ui/`: Streamlit frontend application
* `tests/`: Placeholder for automated tests
* `Dockerfile`, `docker-compose.yml`: Docker configuration
* `pyproject.toml`, `poetry.lock`: Dependency management
* `.env.example`, `.env`: Environment variables

## Next Steps / Future Enhancements

* Implement more robust error handling throughout
* Add dedicated graph query tools to the agent (e.g., finding callers/callees)
* Implement advanced hybrid retrieval strategies (Graph RAG)
* Refine Tree-sitter parsers for deeper analysis (imports, specific calls)
* Add comprehensive unit and integration tests
* Implement efficient incremental updates for the ingestion pipeline
* Integrate Confluence/Jira data sources
* Improve UI/UX (display context, chat history, graph visualizations)
* Optimize performance (embedding speed, query speed)
* Enhanced repository comparison and cross-repository analysis
* Team collaboration features (shared notes, insights)
