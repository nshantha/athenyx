#!/usr/bin/env python3
"""
Test script to verify that the enhanced ingestion system is used as the default.
"""
import os
import sys
import logging
import importlib
import inspect

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ingestion_imports():
    """Test that the proper imports are used in the ingestion system."""
    logger.info("Testing ingestion imports...")
    
    # Check main.py exports
    from ingestion.main import __all__
    logger.info(f"ingestion.main.__all__: {__all__}")
    assert "run_enhanced_ingestion" in __all__, "run_enhanced_ingestion should be exported from ingestion.main"
    assert "run_comprehensive_ingestion" not in __all__, "run_comprehensive_ingestion should not be exported from ingestion.main"
    
    # Check CLI module
    from ingestion.modules.cli import main
    cli_source = inspect.getsource(main)
    logger.info("Checking CLI main function...")
    assert "run_enhanced_ingestion" in cli_source, "CLI main function should use run_enhanced_ingestion"
    assert "EnhancedKnowledgeSystem" in cli_source, "CLI main function should use EnhancedKnowledgeSystem"
    
    # Check repository API
    from app.api.repository import _run_ingestion
    repo_source = inspect.getsource(_run_ingestion)
    logger.info("Checking repository API _run_ingestion function...")
    assert "enhanced ingestion" in repo_source.lower(), "Repository API should use enhanced ingestion"
    
    logger.info("All import tests passed!")
    return True

def test_ingestion_flow():
    """Test that the ingestion flow uses the enhanced system."""
    logger.info("Testing ingestion flow...")
    
    # Import the main ingestion function
    from ingestion.main import run_enhanced_ingestion
    
    # Check that it's the correct function
    assert run_enhanced_ingestion.__module__ == "ingestion.modules.enhanced_knowledge_system", \
        "run_enhanced_ingestion should be imported from enhanced_knowledge_system"
    
    # Check CLI module functions
    from ingestion.modules.cli import run_comprehensive_ingestion
    
    # Verify that run_comprehensive_ingestion now calls run_enhanced_ingestion
    cli_source = inspect.getsource(run_comprehensive_ingestion)
    assert "run_enhanced_ingestion" in cli_source, \
        "run_comprehensive_ingestion should call run_enhanced_ingestion"
    
    logger.info("All flow tests passed!")
    return True

if __name__ == "__main__":
    try:
        logger.info("Starting tests for enhanced ingestion system...")
        
        # Run the tests
        imports_ok = test_ingestion_imports()
        flow_ok = test_ingestion_flow()
        
        if imports_ok and flow_ok:
            logger.info("✅ All tests passed! The enhanced ingestion system is correctly set as the default.")
            sys.exit(0)
        else:
            logger.error("❌ Some tests failed. Please check the logs for details.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
        sys.exit(1) 