"""
Command line interface for the ingestion system.
"""
import argparse
import asyncio
import json
import logging
import os
import tempfile
from typing import Dict, Any, Optional, List

from ingestion.config import ingestion_settings
from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem, run_enhanced_ingestion

logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Enterprise AI Software Knowledge System Ingestion"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--repos", 
        type=str, 
        nargs='+',
        help="List of repository URLs to ingest (space-separated)"
    )
    parser.add_argument(
        "--microservices-repo", 
        type=str, 
        help="URL of microservices repository to analyze"
    )
    
    return parser.parse_args()

def run_comprehensive_ingestion(config_path: Optional[str] = None) -> None:
    """
    Synchronous entry point for the enhanced ingestion pipeline.
    
    This is the ingestion method that provides proper ontology structure
    with accurate relationships between files, classes, functions, and code chunks.
    
    Args:
        config_path: Path to configuration file (optional)
    """
    try:
        asyncio.run(run_enhanced_ingestion(config_path))
    except Exception as e:
        logger.critical(f"Unhandled exception in enhanced ingestion: {e}", exc_info=True)

def main() -> None:
    """
    Main entry point for CLI usage.
    
    This uses the enhanced ingestion pipeline, which provides proper ontology structure
    with accurate relationships between files, classes, functions, and code chunks.
    """
    # Debug environment variables
    logger.info("Debugging environment variables:")
    logger.info(f"INGEST_REPO_URL = {os.getenv('INGEST_REPO_URL')}")
    
    args = parse_args()
    
    # Create a config dictionary if repos are provided
    config = None
    if args.repos or args.microservices_repo:
        config = {}
            
        if args.microservices_repo:
            config["microservices_repo_url"] = args.microservices_repo
            
        if args.repos:
            config["repositories"] = []
            for repo_url in args.repos:
                config["repositories"].append({
                    "url": repo_url,
                    "service_name": repo_url.split('/')[-1].replace('.git', '')
                })
    
    logger.info("Using enhanced knowledge system (EnhancedKnowledgeSystem) for ingestion")
    if config:
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config, f)
            temp_config_path = f.name
        
        try:
            # Create and run the enhanced knowledge system
            knowledge_system = EnhancedKnowledgeSystem(temp_config_path)
            asyncio.run(knowledge_system.run_enhanced_ingestion())
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_config_path)
            except:
                pass
    else:
        # Create and run the enhanced knowledge system with the provided config
        knowledge_system = EnhancedKnowledgeSystem(args.config)
        asyncio.run(knowledge_system.run_enhanced_ingestion()) 