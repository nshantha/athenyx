"""
Module for extracting and handling API information from code repositories.
"""
import logging
import re
from typing import Dict, Any, List, Tuple

from ingestion.parsing.tree_sitter_parser import TreeSitterParser

logger = logging.getLogger(__name__)

class ApiExtractor:
    """
    Class for extracting API endpoints and data models from parsed code.
    """
    
    @staticmethod
    def extract_api_and_data_models(parsed_data: List[Dict[str, Any]], repo_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract API definitions and data models from parsed code.
        
        Args:
            parsed_data: List of parsed file data dictionaries
            repo_url: Repository URL for reference
            
        Returns:
            Tuple of (api_definitions, data_models)
        """
        api_definitions = []
        data_models = []
        
        # Process each file's parsed data
        for file_data in parsed_data:
            if "parse_error" in file_data and file_data["parse_error"]:
                continue
                
            language = file_data.get("language", "")
            
            # Extract based on language
            if language == "python":
                file_apis, file_models = ApiExtractor._extract_python_apis(file_data, repo_url)
            elif language == "javascript" or language == "typescript":
                file_apis, file_models = ApiExtractor._extract_js_ts_apis(file_data, repo_url)
            elif language == "java":
                file_apis, file_models = ApiExtractor._extract_java_apis(file_data, repo_url)
            elif language == "go":
                file_apis, file_models = ApiExtractor._extract_go_apis(file_data, repo_url)
            elif language == "csharp":
                file_apis, file_models = ApiExtractor._extract_csharp_apis(file_data, repo_url)
            else:
                # Default empty for other languages
                file_apis, file_models = [], []
                
            # Add repository URL to each definition
            for api in file_apis:
                api["repo_url"] = repo_url
            for model in file_models:
                model["repo_url"] = repo_url
                
            api_definitions.extend(file_apis)
            data_models.extend(file_models)
        
        logger.info(f"Extracted {len(api_definitions)} API endpoints and {len(data_models)} data models from {repo_url}")
        return api_definitions, data_models
        
    @staticmethod
    def _extract_python_apis(file_data: Dict[str, Any], repo_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract API endpoints and data models from Python code."""
        api_definitions = []
        data_models = []
        
        file_path = file_data.get("path", "")
        
        # Check for FastAPI, Flask, Django, etc.
        is_fastapi = False
        is_flask = False
        is_django = False
        
        # Look for imports in the file
        if "imports" in file_data:
            for imp in file_data.get("imports", []):
                module = imp.get("module", "")
                if module == "fastapi":
                    is_fastapi = True
                elif module == "flask":
                    is_flask = True
                elif module == "django":
                    is_django = True
        
        # Process functions and classes based on the framework
        if is_fastapi:
            # Look for FastAPI route decorators
            # Example: @app.get("/users/{user_id}")
            for function in file_data.get("functions", []):
                if "decorators" in function:
                    for decorator in function.get("decorators", []):
                        if "@app." in decorator and any(x in decorator for x in ["get", "post", "put", "delete", "patch"]):
                            # Extract path from decorator
                            path_match = re.search(r'@app\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', decorator)
                            if path_match:
                                http_method = path_match.group(1).upper()
                                path = path_match.group(2)
                                
                                api_def = {
                                    "name": function.get("name", ""),
                                    "path": path,
                                    "method": http_method,
                                    "framework": "FastAPI",
                                    "file_path": file_path,
                                    "code": function.get("code", ""),
                                    "params": function.get("params", []),
                                    "return_type": function.get("return_type", ""),
                                    "repo_url": repo_url
                                }
                                api_definitions.append(api_def)
        
        elif is_flask:
            # Look for Flask route decorators
            # Example: @app.route("/users/<user_id>", methods=["GET"])
            for function in file_data.get("functions", []):
                if "decorators" in function:
                    for decorator in function.get("decorators", []):
                        if "@app.route" in decorator or any(f"@app.{m}" in decorator for m in ["get", "post", "put", "delete"]):
                            # Extract path from decorator
                            path_match = re.search(r'@app\.(?:route\([\'"]([^\'"]+)[\'"]|(?:get|post|put|delete)\([\'"]([^\'"]+)[\'"])', decorator)
                            if path_match:
                                path = path_match.group(1) or path_match.group(2)
                                
                                # Extract method from decorator
                                method = "GET"  # Default
                                if "methods=" in decorator:
                                    method_match = re.search(r'methods=\[[\'"](GET|POST|PUT|DELETE|PATCH)[\'"]', decorator)
                                    if method_match:
                                        method = method_match.group(1)
                                
                                api_def = {
                                    "name": function.get("name", ""),
                                    "path": path,
                                    "method": method,
                                    "framework": "Flask",
                                    "file_path": file_path,
                                    "code": function.get("code", ""),
                                    "params": function.get("params", []),
                                    "return_type": function.get("return_type", ""),
                                    "repo_url": repo_url
                                }
                                api_definitions.append(api_def)
        
        # Extract data models (Pydantic models for FastAPI, dataclasses, etc.)
        for cls in file_data.get("classes", []):
            # Check for Pydantic BaseModel inheritance
            is_pydantic_model = False
            for base in cls.get("bases", []):
                if "BaseModel" in base:
                    is_pydantic_model = True
                    break
            
            # Also check for dataclasses
            is_dataclass = False
            if "decorators" in cls:
                for decorator in cls.get("decorators", []):
                    if "@dataclass" in decorator:
                        is_dataclass = True
                        break
            
            if is_pydantic_model or is_dataclass:
                model_def = {
                    "name": cls.get("name", ""),
                    "type": "Pydantic" if is_pydantic_model else "Dataclass",
                    "file_path": file_path,
                    "fields": [],
                    "code": cls.get("code", ""),
                    "repo_url": repo_url
                }
                
                # Extract fields from the class
                for attr in cls.get("attributes", []):
                    field = {
                        "name": attr.get("name", ""),
                        "type": attr.get("type", ""),
                        "default": attr.get("value", ""),
                        "required": "= None" not in attr.get("code", "")
                    }
                    model_def["fields"].append(field)
                
                data_models.append(model_def)
        
        return api_definitions, data_models
        
    @staticmethod
    def _extract_js_ts_apis(file_data: Dict[str, Any], repo_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract API endpoints and data models from JavaScript/TypeScript code."""
        api_definitions = []
        data_models = []
        
        file_path = file_data.get("path", "")
        
        # Check for Express.js, Next.js API routes, etc.
        is_express = False
        is_nextjs = False
        
        # Look for imports in the file
        for imp in file_data.get("imports", []):
            module = imp.get("module", "")
            if module == "express":
                is_express = True
            elif module == "next" or "pages/api" in file_path:
                is_nextjs = True
        
        # Process Express.js routes
        # Example: app.get('/users/:id', (req, res) => { ... })
        if is_express:
            # Look for route pattern in function calls
            for func in file_data.get("functions", []):
                code = func.get("code", "")
                # Check for Express routes in the function body
                route_matches = re.finditer(r'(app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', code)
                for match in route_matches:
                    method = match.group(2).upper()
                    path = match.group(3)
                    
                    api_def = {
                        "name": f"{method}_{path.replace('/', '_')}",
                        "path": path,
                        "method": method,
                        "framework": "Express",
                        "file_path": file_path,
                        "code": func.get("code", ""),
                        "params": func.get("params", []),
                        "repo_url": repo_url
                    }
                    api_definitions.append(api_def)
        
        # Process Next.js API routes
        # Example: export default function handler(req, res) { ... }
        elif is_nextjs and "/pages/api/" in file_path:
            for func in file_data.get("functions", []):
                if func.get("name") == "handler" or func.get("is_default", False):
                    # Extract API path from file path
                    # e.g., pages/api/users/[id].js -> /api/users/[id]
                    api_path = file_path.split("pages")[1].split(".")[0]
                    
                    api_def = {
                        "name": func.get("name", "handler"),
                        "path": api_path,
                        "method": "ANY",  # Next.js handlers handle any method by default
                        "framework": "Next.js",
                        "file_path": file_path,
                        "code": func.get("code", ""),
                        "params": func.get("params", []),
                        "repo_url": repo_url
                    }
                    api_definitions.append(api_def)
        
        # Extract data models (TypeScript interfaces, types)
        if file_path.endswith(".ts") or file_path.endswith(".tsx"):
            for interface in file_data.get("interfaces", []):
                model_def = {
                    "name": interface.get("name", ""),
                    "type": "Interface",
                    "file_path": file_path,
                    "fields": [],
                    "code": interface.get("code", ""),
                    "repo_url": repo_url
                }
                
                # Extract fields
                for prop in interface.get("properties", []):
                    field = {
                        "name": prop.get("name", ""),
                        "type": prop.get("type", ""),
                        "required": "?" not in prop.get("code", "")
                    }
                    model_def["fields"].append(field)
                
                data_models.append(model_def)
                
            # Also look for type aliases
            for type_alias in file_data.get("type_aliases", []):
                model_def = {
                    "name": type_alias.get("name", ""),
                    "type": "Type",
                    "file_path": file_path,
                    "code": type_alias.get("code", ""),
                    "repo_url": repo_url
                }
                data_models.append(model_def)
        
        return api_definitions, data_models
        
    @staticmethod
    def _extract_java_apis(file_data: Dict[str, Any], repo_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract API endpoints and data models from Java code."""
        api_definitions = []
        data_models = []
        
        file_path = file_data.get("path", "")
        
        # Check for Spring annotations
        is_spring_controller = False
        for cls in file_data.get("classes", []):
            if "annotations" in cls:
                for annotation in cls.get("annotations", []):
                    if any(a in annotation for a in ["@RestController", "@Controller", "@RequestMapping"]):
                        is_spring_controller = True
                        
                        # Extract base path from class annotation
                        base_path = ""
                        for ann in cls.get("annotations", []):
                            path_match = re.search(r'@RequestMapping\([\'"]([^\'"]+)[\'"]', ann)
                            if path_match:
                                base_path = path_match.group(1)
                                break
                        
                        # Process methods with annotations
                        for method in cls.get("methods", []):
                            http_method = "GET"  # Default
                            path = ""
                            
                            # Check method annotations
                            for ann in method.get("annotations", []):
                                if "@GetMapping" in ann:
                                    http_method = "GET"
                                    path_match = re.search(r'@GetMapping\(?[\'"]?([^\'"]+)[\'"]?\)?', ann)
                                    if path_match:
                                        path = path_match.group(1)
                                elif "@PostMapping" in ann:
                                    http_method = "POST"
                                    path_match = re.search(r'@PostMapping\(?[\'"]?([^\'"]+)[\'"]?\)?', ann)
                                    if path_match:
                                        path = path_match.group(1)
                                elif "@PutMapping" in ann:
                                    http_method = "PUT"
                                    path_match = re.search(r'@PutMapping\(?[\'"]?([^\'"]+)[\'"]?\)?', ann)
                                    if path_match:
                                        path = path_match.group(1)
                                elif "@DeleteMapping" in ann:
                                    http_method = "DELETE"
                                    path_match = re.search(r'@DeleteMapping\(?[\'"]?([^\'"]+)[\'"]?\)?', ann)
                                    if path_match:
                                        path = path_match.group(1)
                                elif "@RequestMapping" in ann:
                                    # Extract method and path
                                    method_match = re.search(r'method\s*=\s*RequestMethod\.([A-Z]+)', ann)
                                    if method_match:
                                        http_method = method_match.group(1)
                                    
                                    path_match = re.search(r'value\s*=\s*[\'"]([^\'"]+)[\'"]', ann)
                                    if path_match:
                                        path = path_match.group(1)
                            
                            # Combine with base path
                            if path:
                                full_path = base_path
                                if full_path and not full_path.endswith("/") and not path.startswith("/"):
                                    full_path += "/"
                                full_path += path
                                
                                api_def = {
                                    "name": method.get("name", ""),
                                    "path": full_path,
                                    "method": http_method,
                                    "framework": "Spring",
                                    "file_path": file_path,
                                    "code": method.get("code", ""),
                                    "params": method.get("params", []),
                                    "return_type": method.get("return_type", ""),
                                    "repo_url": repo_url
                                }
                                api_definitions.append(api_def)
        
        # Extract data models (POJOs, DTOs)
        for cls in file_data.get("classes", []):
            # Look for model classes
            is_model = False
            
            # Check if this looks like a model class
            if any(ann in str(cls.get("annotations", [])) for ann in ["@Entity", "@Data", "@Lombok", "@JsonIgnoreProperties"]):
                is_model = True
            
            # Or if it has typical model name suffixes
            for suffix in ["DTO", "Entity", "Model", "Request", "Response", "Payload"]:
                if cls.get("name", "").endswith(suffix):
                    is_model = True
                    break
            
            if is_model:
                model_def = {
                    "name": cls.get("name", ""),
                    "type": "JavaBean",
                    "file_path": file_path,
                    "fields": [],
                    "code": cls.get("code", ""),
                    "repo_url": repo_url
                }
                
                # Extract fields from the class
                for field in cls.get("fields", []):
                    field_def = {
                        "name": field.get("name", ""),
                        "type": field.get("type", ""),
                        "annotations": field.get("annotations", [])
                    }
                    model_def["fields"].append(field_def)
                
                data_models.append(model_def)
        
        return api_definitions, data_models
        
    @staticmethod
    def _extract_go_apis(file_data: Dict[str, Any], repo_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract API endpoints and data models from Go code."""
        api_definitions = []
        data_models = []
        
        file_path = file_data.get("path", "")
        
        # Check for common Go web frameworks (Gin, Echo, etc.)
        is_gin = False
        is_echo = False
        is_mux = False
        
        for imp in file_data.get("imports", []):
            if "gin" in imp.get("path", ""):
                is_gin = True
            elif "echo" in imp.get("path", ""):
                is_echo = True
            elif "gorilla/mux" in imp.get("path", ""):
                is_mux = True
        
        # Extract Gin routes
        if is_gin:
            for func in file_data.get("functions", []):
                code = func.get("code", "")
                # Look for router.GET/POST patterns
                route_matches = re.finditer(r'(?:r|router|g|gin|e|engine)\.(GET|POST|PUT|DELETE|PATCH|HEAD)\([\'"]([^\'"]+)[\'"]', code)
                for match in route_matches:
                    method = match.group(1).upper()
                    path = match.group(2)
                    
                    api_def = {
                        "name": f"{method}_{path.replace('/', '_')}",
                        "path": path,
                        "method": method,
                        "framework": "Gin",
                        "file_path": file_path,
                        "code": func.get("code", ""),
                        "params": func.get("params", []),
                        "repo_url": repo_url
                    }
                    api_definitions.append(api_def)
        
        # Extract Echo routes
        elif is_echo:
            for func in file_data.get("functions", []):
                code = func.get("code", "")
                # Look for e.GET/POST patterns
                route_matches = re.finditer(r'(?:e|echo)\.(GET|POST|PUT|DELETE|PATCH|HEAD)\([\'"]([^\'"]+)[\'"]', code)
                for match in route_matches:
                    method = match.group(1).upper()
                    path = match.group(2)
                    
                    api_def = {
                        "name": f"{method}_{path.replace('/', '_')}",
                        "path": path,
                        "method": method,
                        "framework": "Echo",
                        "file_path": file_path,
                        "code": func.get("code", ""),
                        "params": func.get("params", []),
                        "repo_url": repo_url
                    }
                    api_definitions.append(api_def)
        
        # Extract Gorilla Mux routes
        elif is_mux:
            for func in file_data.get("functions", []):
                code = func.get("code", "")
                # Look for router.HandleFunc patterns
                route_matches = re.finditer(r'(?:r|router)\.HandleFunc\([\'"]([^\'"]+)[\'"]', code)
                for match in route_matches:
                    path = match.group(1)
                    # Try to determine HTTP method
                    method_match = re.search(r'Methods\([\'"]([A-Z]+)[\'"]', code)
                    method = method_match.group(1) if method_match else "GET"
                    
                    api_def = {
                        "name": f"{method}_{path.replace('/', '_')}",
                        "path": path,
                        "method": method,
                        "framework": "GorillaMux",
                        "file_path": file_path,
                        "code": func.get("code", ""),
                        "params": func.get("params", []),
                        "repo_url": repo_url
                    }
                    api_definitions.append(api_def)
        
        # Extract data models (structs)
        for struct in file_data.get("structs", []):
            model_def = {
                "name": struct.get("name", ""),
                "type": "Struct",
                "file_path": file_path,
                "fields": [],
                "code": struct.get("code", ""),
                "repo_url": repo_url
            }
            
            # Extract fields
            for field in struct.get("fields", []):
                field_def = {
                    "name": field.get("name", ""),
                    "type": field.get("type", ""),
                    "tags": field.get("tags", [])
                }
                model_def["fields"].append(field_def)
            
            data_models.append(model_def)
        
        return api_definitions, data_models
        
    @staticmethod
    def _extract_csharp_apis(file_data: Dict[str, Any], repo_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract API endpoints and data models from C# code."""
        api_definitions = []
        data_models = []
        
        file_path = file_data.get("path", "")
        
        # Check for ASP.NET Core annotations
        is_controller = False
        for cls in file_data.get("classes", []):
            # Check if class is a controller
            is_api_controller = False
            controller_base_path = ""
            
            if "attributes" in cls:
                for attr in cls.get("attributes", []):
                    if "[ApiController]" in attr or "[Controller]" in attr:
                        is_api_controller = True
                    if "[Route" in attr:
                        route_match = re.search(r'\[Route\([\'"]([^\'"]+)[\'"]', attr)
                        if route_match:
                            controller_base_path = route_match.group(1)
            
            # Check class name suffix
            if cls.get("name", "").endswith("Controller"):
                is_api_controller = True
            
            if is_api_controller:
                # Process controller methods
                for method in cls.get("methods", []):
                    http_method = "GET"  # Default
                    path = ""
                    
                    if "attributes" in method:
                        for attr in method.get("attributes", []):
                            if "[HttpGet" in attr:
                                http_method = "GET"
                                path_match = re.search(r'\[HttpGet\(?[\'"]?([^\'"]+)[\'"]?\)?', attr)
                                if path_match:
                                    path = path_match.group(1)
                            elif "[HttpPost" in attr:
                                http_method = "POST"
                                path_match = re.search(r'\[HttpPost\(?[\'"]?([^\'"]+)[\'"]?\)?', attr)
                                if path_match:
                                    path = path_match.group(1)
                            elif "[HttpPut" in attr:
                                http_method = "PUT"
                                path_match = re.search(r'\[HttpPut\(?[\'"]?([^\'"]+)[\'"]?\)?', attr)
                                if path_match:
                                    path = path_match.group(1)
                            elif "[HttpDelete" in attr:
                                http_method = "DELETE"
                                path_match = re.search(r'\[HttpDelete\(?[\'"]?([^\'"]+)[\'"]?\)?', attr)
                                if path_match:
                                    path = path_match.group(1)
                            elif "[Route" in attr:
                                path_match = re.search(r'\[Route\([\'"]([^\'"]+)[\'"]', attr)
                                if path_match:
                                    path = path_match.group(1)
                    
                    # Combine with controller base path
                    if path or controller_base_path:
                        full_path = controller_base_path
                        if full_path and not full_path.endswith("/") and path and not path.startswith("/"):
                            full_path += "/"
                        if path:
                            full_path += path
                        
                        api_def = {
                            "name": method.get("name", ""),
                            "path": full_path,
                            "method": http_method,
                            "framework": "ASP.NET Core",
                            "file_path": file_path,
                            "code": method.get("code", ""),
                            "params": method.get("params", []),
                            "return_type": method.get("return_type", ""),
                            "repo_url": repo_url
                        }
                        api_definitions.append(api_def)
        
        # Extract data models (classes with properties)
        for cls in file_data.get("classes", []):
            # Skip controllers
            if cls.get("name", "").endswith("Controller"):
                continue
                
            # Check if this looks like a model class
            is_model = False
            
            # Look for data annotation attributes
            if "attributes" in cls:
                for attr in cls.get("attributes", []):
                    if any(a in attr for a in ["[Table", "[DataContract", "[Serializable"]):
                        is_model = True
                        break
            
            # Or check typical model name suffixes
            for suffix in ["DTO", "Model", "Entity", "Request", "Response", "Payload", "Dto"]:
                if cls.get("name", "").endswith(suffix):
                    is_model = True
                    break
            
            # Also check if the class has mostly just properties
            properties_count = len(cls.get("properties", []))
            methods_count = len(cls.get("methods", []))
            if properties_count > 0 and properties_count > methods_count:
                is_model = True
            
            if is_model:
                model_def = {
                    "name": cls.get("name", ""),
                    "type": "Class",
                    "file_path": file_path,
                    "fields": [],
                    "code": cls.get("code", ""),
                    "repo_url": repo_url
                }
                
                # Extract properties
                for prop in cls.get("properties", []):
                    prop_def = {
                        "name": prop.get("name", ""),
                        "type": prop.get("type", ""),
                        "attributes": prop.get("attributes", [])
                    }
                    model_def["fields"].append(prop_def)
                
                data_models.append(model_def)
        
        return api_definitions, data_models 