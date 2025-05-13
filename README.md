# Actuamind: Autonomous Software Engineering Intelligence

## Overview
Actuamind is a revolutionary AI-powered platform that transforms how engineering teams understand and interact with their software ecosystems. It serves two essential functions:
- **Intelligent Knowledge System**: Actuamind creates a comprehensive, interconnected map of your entire software landscape by indexing, analyzing, and connecting information across code repositories, documentation, and team structures. This knowledge graph enables natural language queries about any aspect of your systems.
- **Autonomous Engineering Assistants**: Building on this deep understanding, Actuamind will actively participate in the software development lifecycle by automating routine tasks, implementing code changes, providing 24/7 operational support, and accelerating onboarding for team members across all roles.

By combining advanced knowledge representation with agentic capabilities, Actuamind dramatically reduces the cognitive burden on engineers, accelerates development cycles, and democratizes access to system knowledge throughout your organization. Whether you're a senior engineer debugging a complex issue, a new team member getting up to speed, or a manager needing technical context without code immersion, Actuamind provides the right information and assistance exactly when you need it.

*Note: These agentic capabilities are on our roadmap and not yet implemented in the current version.*

<div align="center">
  <a href="https://www.youtube.com/watch?v=TBjGveJrfo0">
    <img src="https://img.youtube.com/vi/TBjGveJrfo0/maxresdefault.jpg" alt="Actuamind - Autonomous Software Engineering Intelligence" width="600" />
  </a>
  <br>
  <a href="https://www.youtube.com/watch?v=TBjGveJrfo0">
    <img src="https://img.shields.io/badge/▶-Watch_Video-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="Watch Video" width="180">
  </a>
</div>

## Table of Contents
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Beyond Knowledge: Future Agentic Capabilities](#beyond-knowledge-future-agentic-capabilities)
- [The Goal](#the-goal)
- [Why Actuamind?](#why-actuamind)
- [Current Features](#current-features)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Application](#running-the-application)
- [Using Actuamind](#using-actuamind)
- [Development](#development)
- [Troubleshooting](#troubleshooting-common-issues)
- [Project Structure](#project-structure-brief)
- [FAQ](#faq)
- [Next Steps / Future Enhancements](#next-steps--future-enhancements)

## The Problem
Navigating your company's software ecosystem is increasingly challenging due to:

- **Knowledge Fragmentation**: Documentation is often outdated, incomplete, or scattered across multiple systems
- **Context Loss**: Critical insights about code structure and decisions are lost during team transitions
- **Manual Overhead**: Engineers spend excessive time understanding code before making changes
- **Limited Automation**: Existing tools can detect issues but can't autonomously fix them
- **Operational Burden**: On-call rotations and support responsibilities create burnout and context switching
- **Siloed Expertise**: Knowledge of system behavior is concentrated among a few experienced engineers
- **Lengthy Onboarding**: New team members (engineers, managers, product owners, QA) take months to become productive, with both technical and non-technical staff struggling to navigate complex systems without years of institutional knowledge

These challenges not only slow down development and complicate problem-solving but also create significant cognitive load for engineering teams.

## The Solution
Actuamind provides a comprehensive solution through two integrated capabilities:

### 1. Intelligent Knowledge System
Actuamind functions as an "AI-powered Google Maps and City Guide" for your software ecosystem by:

- **Automatically mapping** code across repositories and languages, documentation from various sources, and team structures
- **Understanding connections** between interdependent services, documentation, and code
- **Comprehending meaning** beyond just structure
- **Enabling natural language queries** like "What services process customer orders?" or "Where are the authentication module design documents?"

### 2. Autonomous Engineering Assistant (Roadmap)
Building on this knowledge foundation, Actuamind will:

- **Automate repetitive tasks** by understanding context and acting on it appropriately
- **Implement code changes** with awareness of system-wide implications
- **Reduce operational burden** by resolving alerts and providing 24/7 support
- **Close the loop** between knowledge and action within the software development lifecycle

This dual approach creates a virtuous cycle: the more the system understands your codebase, the more effectively it can act on it, and the more it acts, the better it understands your evolving systems.

## Beyond Knowledge: Agentic Capabilities
Actuamind has a planned roadmap to leverage its comprehensive knowledge map to:

- **Autonomously execute code updates** by understanding context and implications
- **Complete Jira tasks independently** by connecting documentation requirements to code implementations
- **Act as a 24/7 on-call engineer** with full system context
- **Support technical questions** in support channels with accurate, contextual responses
- **Assist on-call engineers** by providing insights during system alerts and incidents

## The Goal
Actuamind aims to help engineering teams:

- Understand complex systems faster
- Build new features more efficiently
- Fix bugs more effectively
- Collaborate seamlessly
- Onboard new team members quickly
- Make better-informed technical decisions
- Reduce on-call burden through intelligent automation
- Accelerate incident response with contextual system understanding

## Why Actuamind?
Actuamind was created to address the growing complexity in modern software ecosystems. As codebases expand and team structures evolve, the knowledge of how everything fits together becomes increasingly siloed and fragmented. We built Actuamind to democratize this knowledge and create an intelligent assistant that not only understands your software but can also take action on it.

Key motivations:
- Reduce context-switching for developers
- Minimize knowledge loss during team transitions
- Accelerate onboarding of new team members
- Enable 24/7 support without burnout
- Create a single source of truth for all knowledge

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
  * `OPENAI_API_KEY`: Required for the LLM agent (e.g., GPT4.1-mini) and potentially embeddings if not using a local model. Get from [OpenAI Platform](https://platform.openai.com/api-keys).

### Local Execution

* [Python](https://www.python.org/downloads/) >= 3.10
* [Poetry](https://python-poetry.org/docs/#installation) (Python dependency manager)
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
* `NEO4J_URI`:
  * For Local: Use your local/cloud Neo4j URI (e.g., `bolt://localhost:7687` or AuraDB URI)
* `NEO4J_USERNAME`: Your Neo4j username (default `neo4j`)
* `NEO4J_PASSWORD`: Your Neo4j password. 
* `EMBEDDING_MODEL_NAME`: (If using local Sentence Transformers) e.g., `all-MiniLM-L6-v2`
* `EMBEDDING_DIMENSIONS`: Crucial. Set this to match your embedding model (e.g., 1536 for OpenAI `text-embedding-3-small`, 384 for `all-MiniLM-L6-v2`, 768 for `bge-base-en-v1.5`). The Neo4j index depends on this.
* `OPENAI_EMBEDDING_MODEL`: (If using OpenAI embeddings) e.g., `text-embedding-3-small`
* `OPENAI_LLM_MODEL`: The model for the agent, e.g., `gpt-4.1-mini`
* `INGEST_REPO_URL`: Optional default Git URL of a repository you want to index (e.g., `https://github.com/GoogleCloudPlatform/microservices-demo.git`)
* `INGEST_TARGET_EXTENSIONS`: Comma-separated list of file extensions to process (e.g., `.py,.go,.cs,.java,.js`)
* `BACKEND_API_URL`:
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

Requires managing the Neo4j instance and Python processes separately.

1. **Ensure Prerequisites**: Verify Python(3.12), Poetry, Compiler, and a running Neo4j instance are ready.

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

## Using Actuamind

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

* **Local**: Both `uvicorn --reload` and `streamlit run` automatically watch for changes in the relevant Python files and reload the servers.

## Troubleshooting Common Issues

<details>
<summary><b>ModuleNotFoundError</b></summary>
Usually means a dependency is missing. Run <code>poetry install</code>. Check <code>pyproject.toml</code>.
</details>

<details>
<summary><b>Tree-sitter Build Errors</b></summary>
Ensure C/C++ compiler is installed and accessible in your PATH. Consult tree-sitter and tree-sitter-languages documentation.
</details>

<details>
<summary><b>API Key Errors (OpenAI/Tavily)</b></summary>
Double-check variable names (<code>OPENAI_API_KEY</code>, <code>TAVILY_API_KEY</code>) and values in your <code>.env</code> file. Ensure the file is saved and located in the project root.
</details>

<details>
<summary><b>Neo4j Connection Errors</b></summary>
Verify <code>NEO4J_URI</code>, <code>NEO4J_USERNAME</code>, <code>NEO4J_PASSWORD</code> in <code>.env</code> match your running Neo4j instance. Ensure Neo4j is running and accessible (check firewall if needed). If using Docker, ensure the Neo4j container is healthy (<code>docker-compose ps</code>).
</details>

<details>
<summary><b>NameResolutionError: Failed to resolve 'backend' (UI)</b></summary>
You are likely running the UI locally but <code>BACKEND_API_URL</code> in <code>.env</code> is set to <code>http://backend:8000</code> (for Docker). Change it to <code>http://localhost:8000</code> for local runs.
</details>

<details>
<summary><b>Embedding Dimension Errors</b></summary>
Ensure <code>EMBEDDING_DIMENSIONS</code> in <code>.env</code> matches the output dimension of your chosen embedding model. If you change models/dimensions, you may need to DROP the old vector index in Neo4j (<code>DROP INDEX code_chunk_embeddings</code>) before re-running ingestion.
</details>

<details>
<summary><b>Rate Limit Errors (OpenAI)</b></summary>
The embedding step may take time or fail if you process large repositories. Solutions: Add delays (<code>ingestion/processing/embedding.py</code>), filter input files (<code>ingestion/main.py</code>), request higher OpenAI limits, or switch to a local embedding model.
</details>

<details>
<summary><b>Repository Not Showing After Adding</b></summary>
The UI automatically refreshes after adding a repository, but you can manually refresh by clicking "Check Status" in the ingestion progress area.
</details>

## Project Structure (Brief)

* `app/`: FastAPI backend, agent logic, database interactions
* `ingestion/`: Scripts and modules for data ingestion pipeline
* `ui/`: Streamlit frontend application
* `tests/`: Placeholder for automated tests
* `Dockerfile`, `docker-compose.yml`: Docker configuration
* `pyproject.toml`, `poetry.lock`: Dependency management
* `.env.example`, `.env`: Environment variables

## FAQ
**Q: Does Actuamind require access to my repository history?**  
A: Yes, Actuamind needs Git access to build a comprehensive knowledge graph of your codebase.

**Q: Can Actuamind work with private repositories?**  
A: Absolutely! All data is processed locally or within your infrastructure, ensuring security.

**Q: How does Actuamind differ from traditional documentation tools?**  
A: Actuamind not only indexes documentation but understands code semantics and can take autonomous actions based on this knowledge.

**Q: What programming languages are supported?**  
A: Currently Python, Go, C#, Java, and JavaScript. More languages will be added in future releases.

**Q: Do I need an OpenAI API key?**  
A: Yes, the current version requires an OpenAI API key for the LLM agent and potentially for embeddings.

## Next Steps / Future Enhancements

### Roadmap
* **External Systems Integration**
  * Implement JIRA ticket ingestion to connect code with task context
  * Add Confluence documentation integration for complete knowledge context
  * Create unified querying across code, tickets, and documentation
  * Build relationships between code changes and associated tickets/documentation
* **Agentic Capabilities Integration**
  * Implement AI agents to perform autonomous code analysis
  * Develop reasoning layer for connecting knowledge graph data to practical actions
  * Create foundation for proactive recommendations based on codebase knowledge
* **Autonomous Engineering Features** 
  * Build task execution agents that can complete Jira tickets based on knowledge context
  * Develop capabilities to connect documentation requirements to code implementations
  * Create support agents for answering technical questions in Slack channels
* **DevOps Integration**
  * Implement context-aware alert analysis and prioritization
  * Add CI/CD pipeline integration for deployment awareness
  * Design monitoring capabilities for system health insights
* **User Experience Improvements**
  * Design specialized UI for different user personas (developers, managers, SREs)
  * Implement visual graph exploration for code relationships
  * Create customizable dashboards for engineering insights
* **Advanced Autonomous Features**
  * Enable autonomous feature implementation from requirements documents
  * Develop predictive maintenance through codebase health monitoring
  * Create self-evolving knowledge system that learns from interactions
* **Cross-repository Intelligence**
  * Develop cross-company knowledge graphs for enterprise deployments
  * Implement code reuse recommendations across systems
  * Enable architecture optimization suggestions based on patterns across repositories

## Contributing
We welcome contributions to Actuamind! Whether it's bug reports, feature requests, or code contributions, your help is appreciated.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contact
Project Maintainer - [Nitesh Shantha Kumar](https://www.linkedin.com/in/niteshs1001/)
