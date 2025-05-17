#!/usr/bin/env python3
"""
Script to fix imports in files that have been moved to utils/ and tests/ directories.
"""
import os
import re
import sys

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Don't modify files that don't have imports
    if 'import' not in content:
        return 0
    
    # Track changes
    changes_made = 0
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        original_line = line
        
        # Fix relative imports for files moved to utils/
        if file_path.startswith('utils/'):
            # Add parent directory to import paths for module imports
            if re.match(r'^\s*from\s+(app|ingestion|knowledge_graph)\s+import', line):
                new_lines.append(line)
                continue
            
            # Fix direct imports from these modules
            if re.match(r'^\s*import\s+(app|ingestion|knowledge_graph)', line):
                new_lines.append(line)
                continue
            
            # Fix relative imports from the current directory
            if re.match(r'^\s*from\s+\.\s+import', line) or re.match(r'^\s*from\s+\.\w+\s+import', line):
                line = re.sub(r'from\s+\.', 'from utils', line)
                changes_made += 1
            
            # Fix imports from check_ files
            if re.match(r'^\s*from\s+check_', line):
                line = re.sub(r'from\s+check_', 'from utils.check_', line)
                changes_made += 1
            
            if re.match(r'^\s*import\s+check_', line):
                line = re.sub(r'import\s+check_', 'import utils.check_', line)
                changes_made += 1
                
            # Fix imports for other utility files
            if re.match(r'^\s*from\s+(fix_|clean_|update_)', line):
                match = re.match(r'^\s*from\s+(fix_\w+|clean_\w+|update_\w+)', line)
                if match:
                    module = match.group(1)
                    line = re.sub(f'from\\s+{module}', f'from utils.{module}', line)
                    changes_made += 1
            
            if re.match(r'^\s*import\s+(fix_|clean_|update_)', line):
                match = re.match(r'^\s*import\s+(fix_\w+|clean_\w+|update_\w+)', line)
                if match:
                    module = match.group(1)
                    line = re.sub(f'import\\s+{module}', f'import utils.{module}', line)
                    changes_made += 1
            
        # Fix relative imports for files moved to tests/
        elif file_path.startswith('tests/'):
            # Add parent directory to import paths for module imports
            if re.match(r'^\s*from\s+(app|ingestion|knowledge_graph)\s+import', line):
                new_lines.append(line)
                continue
            
            # Fix direct imports from these modules
            if re.match(r'^\s*import\s+(app|ingestion|knowledge_graph)', line):
                new_lines.append(line)
                continue
            
            # Fix relative imports from the current directory
            if re.match(r'^\s*from\s+\.\s+import', line) or re.match(r'^\s*from\s+\.\w+\s+import', line):
                line = re.sub(r'from\s+\.', 'from tests', line)
                changes_made += 1
            
            # Fix imports from utils files
            if re.match(r'^\s*from\s+(check_|fix_|clean_|update_)', line):
                match = re.match(r'^\s*from\s+(check_\w+|fix_\w+|clean_\w+|update_\w+)', line)
                if match:
                    module = match.group(1)
                    line = re.sub(f'from\\s+{module}', f'from utils.{module}', line)
                    changes_made += 1
            
            if re.match(r'^\s*import\s+(check_|fix_|clean_|update_)', line):
                match = re.match(r'^\s*import\s+(check_\w+|fix_\w+|clean_\w+|update_\w+)', line)
                if match:
                    module = match.group(1)
                    line = re.sub(f'import\\s+{module}', f'import utils.{module}', line)
                    changes_made += 1
                    
            # Fix imports from test_ files
            if re.match(r'^\s*from\s+test_', line):
                line = re.sub(r'from\s+test_', 'from tests.test_', line)
                changes_made += 1
            
            if re.match(r'^\s*import\s+test_', line):
                line = re.sub(r'import\s+test_', 'import tests.test_', line)
                changes_made += 1
                
            # Fix import for run_enhanced_ingestion
            if re.match(r'^\s*from\s+run_enhanced_ingestion\s+import', line):
                line = re.sub(r'from\s+run_enhanced_ingestion', 'from tests.run_enhanced_ingestion', line)
                changes_made += 1
                
            if re.match(r'^\s*import\s+run_enhanced_ingestion', line):
                line = re.sub(r'import\s+run_enhanced_ingestion', 'import tests.run_enhanced_ingestion', line)
                changes_made += 1
        
        # Check if the line has changed
        if line != original_line:
            changes_made += 1
        
        new_lines.append(line)
    
    # Write changes back to the file if any were made
    if changes_made > 0:
        with open(file_path, 'w') as f:
            f.write('\n'.join(new_lines))
        print(f"Fixed {changes_made} imports in {file_path}")
    
    return changes_made

def main():
    """Find and fix imports in all Python files in utils/ and tests/ directories."""
    total_changes = 0
    total_files = 0
    
    # Process utils/ directory
    for root, _, files in os.walk('utils'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                changes = fix_imports_in_file(file_path)
                if changes > 0:
                    total_changes += changes
                    total_files += 1
    
    # Process tests/ directory
    for root, _, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                changes = fix_imports_in_file(file_path)
                if changes > 0:
                    total_changes += changes
                    total_files += 1
    
    print(f"Total: Fixed {total_changes} imports in {total_files} files.")

if __name__ == "__main__":
    main() 