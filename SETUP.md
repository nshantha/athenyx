# Setup Guide for Enterprise AI Knowledge Graph

## Neo4j Authentication Issue

The error in your logs indicates a Neo4j authentication failure:

```
{code: Neo.ClientError.Security.Unauthorized} {message: The client is unauthorized due to authentication failure.}
```

To fix this issue:

1. Create a `.env` file in the project root with the following content:

```
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_actual_password

# OpenAI API Key (required for embeddings)
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSIONS=1536
OPENAI_LLM_MODEL=gpt-3.5-turbo

# Backend API URL (for frontend)
BACKEND_API_URL=http://localhost:8000

# Repository to ingest
INGEST_REPO_URL=https://github.com/langchain-ai/langchain.git
INGEST_TARGET_EXTENSIONS=.py
FORCE_REINDEX=false
```

2. Replace `your_actual_password` with your Neo4j database password.

3. Make sure your Neo4j instance is running:
   ```
   neo4j start
   ```

## YAML Parsing Issue

The error logs show YAML parsing errors for Kubernetes manifest files:

```
Error parsing emailservice.yaml: expected a single document in the stream
```

This is because the code is using `yaml.safe_load()` which only handles single YAML documents, but the Kubernetes manifests contain multiple documents.

The fix has been applied to the `load_service_metadata` method in `ingestion/main.py` to use `yaml.safe_load_all()` instead.

## Running the Microservices Ingestion

To run the microservices ingestion:

1. Set the Neo4j password as an environment variable:
   ```
   export NEO4J_PASSWORD='your_actual_password'
   ```

2. Run the ingestion script:
   ```
   python ingestion/main.py
   ```

## Troubleshooting

If you still encounter issues:

1. Verify your Neo4j credentials by connecting to the database using the Neo4j Browser or CLI.

2. Check that the Neo4j service is running and accessible at the URI specified in your configuration.

3. If you see YAML parsing errors, make sure the YAML files are valid. The code now handles multiple documents in a single file, but other YAML syntax errors could still cause problems.

4. For debugging, you can add more detailed logging by setting the log level to DEBUG in your code or environment variables. 