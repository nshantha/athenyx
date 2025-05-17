#!/usr/bin/env python3
"""
Test script for verifying import extraction and relationship creation.
This script tests the enhanced import extraction and relationship creation functionality.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, List

from app.db.neo4j_manager import db_manager
from ingestion.parsing.enhanced_parser import EnhancedParser
from ingestion.sources.git_loader import GitLoader
from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


async def test_import_extraction():
    """Test the import extraction functionality."""
    logger.info("Testing import extraction...")
    
    # Test Python imports
    python_code = """
import os
import sys, json
from datetime import datetime
from typing import Dict, List, Optional
from testslocal_module import function
from ..parent_module import Class
"""
    python_imports = EnhancedParser._extract_imports(python_code, 'python')
    logger.info(f"Python imports: {len(python_imports)}")
    for imp in python_imports:
        logger.info(f"  {imp}")
    
    # Test JavaScript imports
    js_code = """
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import './styles.css';
const axios = require('axios');
require('dotenv').config();
"""
    try:
        js_imports = EnhancedParser._extract_imports(js_code, 'javascript')
        logger.info(f"JavaScript imports: {len(js_imports)}")
        for imp in js_imports:
            logger.info(f"  {imp}")
    except Exception as e:
        logger.error(f"Error extracting JavaScript imports: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Test Go imports
    go_code = """
package main

import (
    "fmt"
    "os"
    log "github.com/sirupsen/logrus"
)

import "net/http"
"""
    go_imports = EnhancedParser._extract_imports(go_code, 'go')
    logger.info(f"Go imports: {len(go_imports)}")
    for imp in go_imports:
        logger.info(f"  {imp}")
    
    # Test Java imports
    java_code = """
package com.example.demo;

import java.util.List;
import java.util.Map;
import java.io.*;
import static java.lang.Math.*;
import org.springframework.boot.SpringApplication;
"""
    java_imports = EnhancedParser._extract_imports(java_code, 'java')
    logger.info(f"Java imports: {len(java_imports)}")
    for imp in java_imports:
        logger.info(f"  {imp}")
    
    # Test C# imports
    csharp_code = """
using System;
using System.Collections.Generic;
using static System.Math;
using MyAlias = Company.Product.Module;
"""
    csharp_imports = EnhancedParser._extract_imports(csharp_code, 'csharp')
    logger.info(f"C# imports: {len(csharp_imports)}")
    for imp in csharp_imports:
        logger.info(f"  {imp}")


async def test_import_relationships(repo_url: str):
    """
    Test the creation of import relationships in the database.
    
    Args:
        repo_url: URL of the repository to test
    """
    logger.info(f"Testing import relationships for repo: {repo_url}")
    
    # Connect to the database
    await db_manager.connect()
    
    # Query for IMPORTS relationships
    query = """
    MATCH (source:File)-[r:IMPORTS]->(target:File)
    WHERE r.repo_url = $repo_url
    RETURN source.path as source_path, target.path as target_path, 
           r.import_name as import_name, r.line as line
    LIMIT 20
    """
    
    result = await db_manager.run_query(query, {"repo_url": repo_url})
    
    logger.info(f"Found {len(result)} IMPORTS relationships:")
    for row in result:
        logger.info(f"  {row['source_path']} -> {row['target_path']} ({row['import_name']})")
    
    # Count relationships by file extension
    query_by_ext = """
    MATCH (source:File)-[r:IMPORTS]->(target:File)
    WHERE r.repo_url = $repo_url
    WITH source.path as source_path, 
         CASE 
           WHEN source.path ENDS WITH '.py' THEN 'Python'
           WHEN source.path ENDS WITH '.go' THEN 'Go'
           WHEN source.path ENDS WITH '.js' OR source.path ENDS WITH '.jsx' THEN 'JavaScript'
           WHEN source.path ENDS WITH '.ts' OR source.path ENDS WITH '.tsx' THEN 'TypeScript'
           WHEN source.path ENDS WITH '.java' THEN 'Java'
           WHEN source.path ENDS WITH '.cs' THEN 'C#'
           ELSE 'Other'
         END as language,
         count(r) as rel_count
    RETURN language, count(source_path) as file_count, sum(rel_count) as total_relationships
    ORDER BY total_relationships DESC
    """
    
    result_by_ext = await db_manager.run_query(query_by_ext, {"repo_url": repo_url})
    
    logger.info("IMPORTS relationships by language:")
    for row in result_by_ext:
        logger.info(f"  {row['language']}: {row['file_count']} files, {row['total_relationships']} relationships")


async def main():
    """Main function."""
    # Test import extraction
    await test_import_extraction()
    
    # If a repository URL is provided, test import relationships
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
        await test_import_relationships(repo_url)
    else:
        logger.info("No repository URL provided. Skipping relationship testing.")
        logger.info("Usage: python test_imports.py <repository_url>")


if __name__ == "__main__":
    asyncio.run(main()) 