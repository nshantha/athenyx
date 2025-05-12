"""
Specialized loader for handling microservices architecture in Neo4j.
"""
import logging
from typing import Dict, Any, List
from neo4j import GraphDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class MicroservicesLoader:
    def __init__(self, neo4j_uri: str = None, neo4j_user: str = None, neo4j_password: str = None):
        """
        Initialize the MicroservicesLoader with Neo4j connection parameters.
        If parameters are not provided, they will be loaded from settings.
        """
        # Use provided parameters or fall back to settings
        uri = neo4j_uri or settings.neo4j_uri
        user = neo4j_user or settings.neo4j_username
        password = neo4j_password or settings.neo4j_password
        
        logger.info(f"Connecting to Neo4j at {uri} with user {user}")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_service_node(self, tx, service_info: Dict[str, Any]):
        """Creates a Service node with its properties."""
        query = """
        MERGE (s:Service {name: $name})
        SET s.language = $language,
            s.description = $description,
            s.endpoints = $endpoints,
            s.service_type = $service_type
        RETURN s
        """
        return tx.run(query, **service_info)

    def create_service_relationships(self, tx, relationships: List[Dict[str, Any]]):
        """Creates relationships between services."""
        for rel in relationships:
            query = """
            MATCH (s1:Service {name: $source})
            MATCH (s2:Service {name: $target})
            MERGE (s1)-[r:CALLS {
                type: $call_type,
                protocol: $protocol,
                async: $is_async
            }]->(s2)
            """
            tx.run(query, **rel)

    def create_api_endpoint(self, tx, endpoint_info: Dict[str, Any]):
        """Creates an APIEndpoint node and links it to a service."""
        query = """
        MATCH (s:Service {name: $service_name})
        MERGE (e:APIEndpoint {
            path: $path,
            method: $method,
            protocol: $protocol
        })
        MERGE (s)-[r:EXPOSES]->(e)
        SET e.parameters = $parameters,
            e.response_type = $response_type,
            e.authentication = $authentication
        """
        tx.run(query, **endpoint_info)

    def create_data_model(self, tx, model_info: Dict[str, Any]):
        """Creates a DataModel node and its relationships."""
        query = """
        MERGE (m:DataModel {name: $name})
        SET m.schema = $schema,
            m.validation = $validation
        WITH m
        MATCH (s:Service {name: $service_name})
        MERGE (s)-[r:USES_MODEL]->(m)
        """
        tx.run(query, **model_info)

    def create_config_dependency(self, tx, config_info: Dict[str, Any]):
        """Creates configuration dependencies between services."""
        query = """
        MATCH (s:Service {name: $service_name})
        MERGE (c:Configuration {key: $key})
        SET c.type = $value_type,
            c.description = $description
        MERGE (s)-[r:REQUIRES_CONFIG]->(c)
        """
        tx.run(query, **config_info)

    def create_service_interface(self, tx, interface_info: Dict[str, Any]):
        """Creates a ServiceInterface node and its implementations."""
        query = """
        MERGE (i:ServiceInterface {name: $name})
        SET i.methods = $methods,
            i.description = $description
        WITH i
        MATCH (s:Service {name: $service_name})
        MERGE (s)-[r:IMPLEMENTS]->(i)
        """
        tx.run(query, **interface_info)

    def load_microservice_structure(self, parsed_data: Dict[str, Any]):
        """Main method to load microservice structure into Neo4j."""
        with self.driver.session() as session:
            # Create service node
            session.execute_write(self.create_service_node, {
                "name": parsed_data["service_name"],
                "language": parsed_data["language"],
                "description": parsed_data.get("description", ""),
                "endpoints": parsed_data.get("service_info", {}).get("endpoints", []),
                "service_type": parsed_data.get("service_info", {}).get("service_type")
            })

            # Create API endpoints
            for endpoint in parsed_data.get("api_info", []):
                session.execute_write(self.create_api_endpoint, endpoint)

            # Create service relationships
            for rel in parsed_data.get("relationships", {}).get("service_calls", []):
                session.execute_write(self.create_service_relationships, [rel])

            # Create data models
            for model in parsed_data.get("relationships", {}).get("data_dependencies", []):
                session.execute_write(self.create_data_model, model)

            # Create configuration dependencies
            for config in parsed_data.get("service_info", {}).get("config_values", []):
                session.execute_write(self.create_config_dependency, {
                    "service_name": parsed_data["service_name"],
                    "key": config["key"],
                    "value_type": config["type"],
                    "description": config.get("description", "")
                })

            # Create service interfaces
            if "service_interfaces" in parsed_data.get("relationships", {}):
                for interface in parsed_data["relationships"]["service_interfaces"]:
                    session.execute_write(self.create_service_interface, interface)

    def create_indices(self):
        """Creates necessary indices for better query performance."""
        with self.driver.session() as session:
            # Create indices for frequently queried properties
            session.run("CREATE INDEX service_name IF NOT EXISTS FOR (s:Service) ON (s.name)")
            session.run("CREATE INDEX endpoint_path IF NOT EXISTS FOR (e:APIEndpoint) ON (e.path)")
            session.run("CREATE INDEX model_name IF NOT EXISTS FOR (m:DataModel) ON (m.name)")
            session.run("CREATE INDEX config_key IF NOT EXISTS FOR (c:Configuration) ON (c.key)")
            session.run("CREATE INDEX interface_name IF NOT EXISTS FOR (i:ServiceInterface) ON (i.name)") 