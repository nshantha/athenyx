# AI-Powered Software Knowledge Graph MVP

This project implements an AI-Powered Knowledge Graph system to index, connect, and query software project information (code structure, semantics) using Neo4j, LangChain, LangGraph, Tree-sitter, FastAPI, and Streamlit.

**Vision:** Empower engineering teams with instant, contextual insights into their software systems.

**MVP Focus:** Ingest a single Git repository (Python code), build a graph of its structure (Files, Functions, Classes) and semantic embeddings (Code Chunks) in Neo4j, and provide a Q&A interface using RAG and Web Search orchestrated by LangGraph.

## Architecture Overview

* **Data Layer:** Neo4j (Graph Database + Vector Index)
* **Ingestion Layer:** Python scripts (Git, Tree-sitter, LangChain Embeddings, Neo4j Loader)
* **Processing/Query Layer:** LangChain & LangGraph (Agent, Tools: RAG, Web Search)
* **API Layer:** FastAPI
* **Presentation Layer:** Streamlit

## Prerequisites

* [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
* [Python](https://www.python.org/downloads/) >= 3.10
* [Poetry](https://python-poetry.org/docs/#installation) (for dependency management)
* [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* C/C++ Compiler: Required by `tree-sitter` to build language grammars.
    * **Linux (Debian/Ubuntu):** `sudo apt-get update && sudo apt-get install build-essential`
    * **macOS:** Install Xcode Command Line Tools: `xcode-select --install`
    * **Windows:** Install Visual Studio with C++ build tools (Community Edition is free). Ensure `cl.exe` is in your PATH. [See Python docs for details](https://wiki.python.org/moin/WindowsCompilers).
* API Keys:
    * OpenAI API Key
    * Tavily API Key (for web search)

## Setup & Installation (Tree-sitter Focus)

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd ai-knowledge-graph
    ```

2.  **Install Tree-sitter & Build Grammars:**
    * **Crucial Step:** The `tree-sitter` Python package needs compiled language grammars. The `tree-sitter-languages` package helps manage this.
    * Ensure you have a C/C++ compiler installed (see Prerequisites).
    * Install Python dependencies using Poetry. This *should* trigger the grammar building via `tree-sitter-languages`:
        ```bash
        poetry install
        ```
    * **Verification (Optional but Recommended):** Check if the Python grammar was built correctly. You can run this Python snippet:
        ```python
        from tree_sitter_languages import get_language, get_parser
        try:
            language = get_language('python')
            parser = get_parser('python')
            print("Tree-sitter Python grammar loaded successfully.")
            # Try parsing a simple string
            tree = parser.parse(bytes("def hello():\n  pass", "utf8"))
            print("Basic parsing test successful.")
            # print(tree.root_node.sexp()) # Uncomment for detailed S-expression
        except Exception as e:
            print(f"Error loading or testing Tree-sitter Python grammar: {e}")
            print("Please ensure build tools are installed and `poetry install` completed without errors.")
            print("You might need to consult the tree-sitter and tree-sitter-languages documentation for troubleshooting.")
        ```
    * **Troubleshooting:** If `poetry install` fails during grammar building or the verification fails, double-check compiler installation. You might need to manually clone specific grammar repositories (e.g., `github.com/tree-sitter/tree-sitter-python`) and follow their build instructions if the helper package fails.

3.  **Configure Environment Variables:**
    * Copy the example environment file: `cp .env.example .env`
    * **Edit `.env`:** Fill in your actual `NEO4J_PASSWORD` (must match `docker-compose.yml`), `OPENAI_API_KEY`, `TAVILY_API_KEY`. Review other settings like `INGEST_REPO_URL`.

4.  **Start Services (Neo4j, Backend, Frontend):**
    ```bash
    docker-compose up --build -d
    ```
    * `-d` runs services in the background.
    * `--build` ensures images are rebuilt if Dockerfile or code changes.
    * Wait a minute for Neo4j to initialize fully (check logs: `docker-compose logs neo4j`).

5.  **Run Initial Ingestion:**
    * Execute the ingestion script *inside* the running backend container (as it has all dependencies installed):
    ```bash
    docker-compose exec backend poetry run ingest
    ```
    * Alternatively, if you installed dependencies locally (`poetry install`), you can run:
        ```bash
        poetry run ingest
        ```
    * This will clone the repo specified in `.env`, parse it, embed, and load into Neo4j. Monitor the console output. This might take some time depending on the repository size and API speeds.

## Usage

1.  **Access the UI:** Open your web browser to `http://localhost:8501`.
2.  **Ask Questions:** Type questions about the codebase you ingested (e.g., "What does the `parse` function in `parser.py` do?", "Find code related to API clients").
3.  **Access the API:** The FastAPI backend is available at `http://localhost:8000`. You can explore the interactive documentation at `http://localhost:8000/docs`.
4.  **Access Neo4j Browser:** Open `http://localhost:7474` to explore the graph directly using Cypher queries. Login with `neo4j` and the password set in `.env`/`docker-compose.yml`.

## Development

* Code changes in the mounted `/app` directory should trigger auto-reload for FastAPI and Streamlit within the running Docker containers.
* Run tests (placeholder): `docker-compose exec backend poetry run pytest`

## Project Structure (Brief)

* `app/`: FastAPI backend, agent logic, database interactions.
* `ingestion/`: Scripts and modules for data ingestion pipeline.
* `ui/`: Streamlit frontend application.
* `tests/`: Placeholder for automated tests.

## Next Steps / Future Enhancements

* Implement more robust error handling.
* Add more sophisticated graph queries as tools.
* Implement hybrid retrieval strategies.
* Support more programming languages.
* Add unit and integration tests.
* Implement incremental updates for ingestion.
* Add Confluence/Jira integration.

## Documentation for LLM Ingestion

This project uses a modular structure. Key components are:
* **Ingestion (`ingestion/`):** Clones Git repos (`git_loader.py`), uses Tree-sitter (`tree_sitter_parser.py`) for structural parsing (Files, Classes, Functions for Python), chunks code (`chunking.py`), generates embeddings via OpenAI (`embedding.py`), and loads data into Neo4j (`neo4j_loader.py`, `db/neo4j_manager.py`), including creating structural nodes/relationships and vector indexes. It checks the last indexed commit SHA before processing.
* **Database (`app/db/neo4j_manager.py`):** Handles Neo4j connection, runs Cypher queries (schema setup, data loading, vector search using `db.index.vector.queryNodes`). Uses async driver.
* **Agent (`app/agent/`):** Uses LangGraph (`graph.py`) to define a state machine. Tools (`tools.py`) include a Neo4j vector RAG retriever and a Tavily web search tool. The agent executor (`agent_executor.py`) compiles and runs the graph.
* **API (`app/api/endpoints.py`, `app/main.py`):** FastAPI application exposing a `/query` endpoint that takes a user question and returns the agent's synthesized answer. Uses Pydantic for validation (`app/schemas/models.py`).
* **UI (`ui/app.py`):** Streamlit application providing a simple chat interface that calls the FastAPI backend.
* **Configuration (`app/core/config.py`, `ingestion/config.py`, `.env`):** Settings loaded from environment variables using Pydantic Settings.
* **Containerization (`Dockerfile`, `docker-compose.yml`):** Defines how to build and run the application services (backend, frontend, Neo4j).