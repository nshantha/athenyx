# Ingestion Report: microservices-demo

## Summary

This report compares what has been ingested into the Neo4j database versus what exists in the actual `microservices-demo` repository.

## API Endpoints

**Database:** 1 API endpoint detected
- POST / -> talkToGemini (in src/shoppingassistantservice/shoppingassistantservice.py, framework: Flask)

**Repository:** The repository has at least 1 Flask route in the shoppingassistantservice, which matches what's in the database.

## Documentation Files

**Database:** 0 documentation files detected
- README.md not found in the database
- No other documentation files found

**Repository:** 30 README.md files and 101 YAML/YML configuration files

## Data Models

**Database:** 0 data models detected

## Relationships

**Database:** 4 relationship types found
- BELONGS_TO: 1791 relationships
- CONTAINS: 1673 relationships
- INHERITS_FROM: 4 relationships
- IMPORTS: 3 relationships

## Inheritance Relationships

**Database:** 4 inheritance relationships detected
- EmailService inherits from BaseEmailService (repeated 3 times)
- DummyEmailService inherits from BaseEmailService

**Repository:** The repository contains inheritance relationships in the email service, which are correctly identified.

## Node Types

**Database:** 5 node types found
- CodeChunk: 1210 nodes
- Function: 384 nodes
- Class: 79 nodes
- File: 59 nodes
- ApiEndpoint: 1 node

## File Types

**Database:** 5 file extensions
- go: 29 files
- py: 13 files
- cs: 9 files
- js: 6 files
- java: 2 files

**Repository:** Same file extensions and counts as in the database

## Import Relationships

**Database:** 3 import relationships
- src/frontend/handlers.go -> src/checkoutservice/money/money.go (import name: money)
- src/frontend/handlers.go -> src/frontend/validator/validator.go (import name: validator)
- src/checkoutservice/main.go -> src/checkoutservice/money/money.go (import name: money)

**Repository:** These import relationships are correctly identified in the actual Go files.

## Issues

1. **Documentation Not Ingested:** None of the documentation files (README.md, etc.) or configuration files (YAML/YML) have been ingested despite being present in the repository.

2. **No Data Models Detected:** No data models have been extracted, though it's possible the repository doesn't contain explicit data models that match the detection patterns.

3. **File Count Discrepancy:** The database contains 59 files, but there are likely many more files in the repository when counting documentation and configuration files.

## Conclusion

The code ingestion process is working correctly for source code files (Go, Python, C#, JavaScript, Java) and correctly identifies API endpoints, classes, functions, and code chunks. It successfully extracts relationships like inheritance and imports.

However, the system is not currently ingesting documentation files (README.md) or configuration files (YAML/YML), which is a gap in the knowledge representation. Adding support for ingesting these file types would make the knowledge graph more complete. 