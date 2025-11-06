#!/usr/bin/env python3
"""
Manifest Generator CLI - Interactive tool for creating and managing Control Tower manifests
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        GREEN = RED = YELLOW = CYAN = BLUE = MAGENTA = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""

from manifest_templates import ModuleTemplates


class ManifestGenerator:
    """Interactive manifest generator with templates and dependency management"""
    
    # Module type definitions with descriptions
    MODULE_TYPES = {
        "1": ("jwt_config", "JWT Authentication & Authorization", "dsp_ai_jwt"),
        "2": ("rag_config", "RAG Configuration (Document Retrieval)", "dsp_ai_rag2"),
        "3": ("rag_service", "RAG Service Module", "dsp_ai_rag2"),
        "4": ("model_server", "Model Server (Embeddings, Reranking)", "model_server"),
        "5": ("api_gateway", "API Gateway (Generic)", "router"),
        "6": ("api_gateway_apisix", "API Gateway (APISIX)", "apisix"),
        "7": ("inference_endpoint", "LLM Inference Endpoint", "llm_service"),
        "8": ("security", "Security & Compliance", "security"),
        "9": ("monitoring", "Monitoring & Observability", "monitoring"),
        "10": ("model_registry", "Model Registry (MLflow, W&B)", "mlflow"),
        "11": ("data_pipeline", "Data Pipeline (ETL/ELT)", "pipeline"),
        "12": ("deployment", "Deployment Configuration", "deployment"),
        "13": ("resource_management", "Resource Management", "resources"),
        "14": ("notifications", "Notifications & Alerts", "notifications"),
        "15": ("backup_recovery", "Backup & Recovery", "backup"),
        "16": ("vault", "HashiCorp Vault Integration", "vault"),
        "17": ("langgraph_workflow", "LangGraph Workflow", "langgraph"),
    }
    
    def __init__(self):
        self.manifest: Dict[str, Any] = {}
        self.modules: List[Dict[str, Any]] = []
        self.environments: Dict[str, Dict[str, Any]] = {}
        self.templates = ModuleTemplates(self)
        
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*70}")
        print(f"{text:^70}")
        print(f"{'='*70}{Style.RESET_ALL}\n")
    
    def print_success(self, text: str):
        print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")
    
    def print_error(self, text: str):
        print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")
    
    def print_warning(self, text: str):
        print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")
    
    def print_info(self, text: str):
        print(f"{Fore.BLUE}ℹ {text}{Style.RESET_ALL}")
    
    def get_input(self, prompt: str, default: Optional[str] = None) -> str:
        """Get user input with optional default"""
        if default:
            prompt = f"{prompt} [{Fore.YELLOW}{default}{Style.RESET_ALL}]: "
        else:
            prompt = f"{prompt}: "
        
        value = input(prompt).strip()
        return value if value else (default or "")
    
    def get_choice(self, prompt: str, choices: List[str], default: Optional[str] = None) -> str:
        """Get user choice from a list"""
        while True:
            value = self.get_input(prompt, default)
            if value in choices:
                return value
            self.print_error(f"Invalid choice. Please select from: {', '.join(choices)}")
    
    def create_new_manifest(self):
        """Create a new manifest interactively"""
        self.print_header("CREATE NEW MANIFEST")
        
        self.manifest["project_id"] = self.get_input("Project ID (unique identifier)")
        self.manifest["project_name"] = self.get_input("Project Name")
        self.manifest["owner"] = self.get_input("Owner/Team", "AI Team")
        self.manifest["description"] = self.get_input("Description (optional)", "")
        self.manifest["version"] = self.get_input("Version", "1.0.0")
        self.manifest["environment"] = self.get_choice(
            "Target Environment",
            ["development", "staging", "production"],
            "development"
        )
        
        tags_input = self.get_input("Tags (comma-separated, optional)", "")
        self.manifest["tags"] = [t.strip() for t in tags_input.split(",") if t.strip()]
        
        self.modules = []
        self.environments = self.create_default_environments()
        
        self.print_success(f"Manifest '{self.manifest['project_id']}' initialized!")
    
    def create_default_environments(self) -> Dict[str, Dict[str, Any]]:
        """Create default environment configurations"""
        return {
            "common": {"secrets": {}, "urls": {}},
            "development": {"secrets": {}, "urls": {"api_base_url": "http://localhost:8000"}},
            "staging": {"secrets": {}, "urls": {"api_base_url": "https://staging-api.example.com"}},
            "production": {"secrets": {}, "urls": {"api_base_url": "https://api.example.com"}}
        }
    
    def show_module_menu(self):
        """Display module type selection menu"""
        self.print_header("SELECT MODULE TYPE")
        
        for key, (module_type, description, _) in self.MODULE_TYPES.items():
            print(f"{Fore.YELLOW}{key:>3}{Style.RESET_ALL}. {Fore.WHITE}{description:<40}{Style.RESET_ALL} ({Fore.CYAN}{module_type}{Style.RESET_ALL})")
        
        print(f"\n{Fore.YELLOW}  0{Style.RESET_ALL}. {Fore.WHITE}Return to main menu{Style.RESET_ALL}")
    
    def add_module(self):
        """Add a module to the manifest"""
        self.show_module_menu()
        
        choice = self.get_input("\nSelect module type")
        
        if choice == "0":
            return
        
        if choice not in self.MODULE_TYPES:
            self.print_error("Invalid selection!")
            return
        
        module_type, description, default_name = self.MODULE_TYPES[choice]
        
        if choice == "6":
            module_type = "api_gateway"
        
        self.print_header(f"CONFIGURE {description.upper()}")
        
        module_name = self.get_input("Module name", default_name)
        
        if any(m["name"] == module_name for m in self.modules):
            self.print_error(f"Module '{module_name}' already exists!")
            return
        
        config = self.templates.get_config(module_type, module_name, choice == "6")
        dependencies = self.get_module_dependencies()
        
        module = {
            "module_type": module_type,
            "name": module_name,
            "config": config
        }
        
        if dependencies:
            module["dependencies"] = dependencies
        
        self.modules.append(module)
        self.print_success(f"Module '{module_name}' added successfully!")
    
    def get_module_dependencies(self) -> List[str]:
        """Get module dependencies from user"""
        if not self.modules:
            return []
        
        print(f"\n{Fore.CYAN}Available modules for dependencies:{Style.RESET_ALL}")
        for i, module in enumerate(self.modules, 1):
            print(f"  {i}. {module['name']} ({module['module_type']})")
        
        deps_input = self.get_input("\nDependencies (comma-separated numbers, or leave empty)", "")
        
        if not deps_input:
            return []
        
        dependencies = []
        for dep_num in deps_input.split(","):
            try:
                idx = int(dep_num.strip()) - 1
                if 0 <= idx < len(self.modules):
                    dependencies.append(self.modules[idx]["name"])
            except ValueError:
                pass
        
        return dependencies
    
    def list_modules(self):
        """List all modules in the manifest"""
        if not self.modules:
            self.print_warning("No modules in manifest")
            return
        
        self.print_header("CURRENT MODULES")
        
        for i, module in enumerate(self.modules, 1):
            deps = module.get("dependencies", [])
            deps_str = f" → depends on: {', '.join(deps)}" if deps else ""
            print(f"{Fore.YELLOW}{i:>3}{Style.RESET_ALL}. {Fore.WHITE}{module['name']:<30}{Style.RESET_ALL} ({Fore.CYAN}{module['module_type']}{Style.RESET_ALL}){deps_str}")
    
    def remove_module(self):
        """Remove a module and its dependents"""
        if not self.modules:
            self.print_warning("No modules to remove")
            return
        
        self.list_modules()
        
        choice = self.get_input("\nSelect module number to remove (0 to cancel)")
        
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(self.modules):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return
        
        module_to_remove = self.modules[idx]
        module_name = module_to_remove["name"]
        
        dependents = self.find_dependents(module_name)
        
        if dependents:
            self.print_warning(f"The following modules depend on '{module_name}':")
            for dep in dependents:
                print(f"  - {dep}")
            
            confirm = self.get_choice(
                "\nRemove all dependent modules as well?",
                ["yes", "no"],
                "no"
            )
            
            if confirm == "no":
                self.print_info("Removal cancelled")
                return
            
            for dep_name in dependents:
                self.modules = [m for m in self.modules if m["name"] != dep_name]
                self.print_success(f"Removed dependent module: {dep_name}")
        
        self.modules = [m for m in self.modules if m["name"] != module_name]
        self.print_success(f"Removed module: {module_name}")
    
    def find_dependents(self, module_name: str, visited: Optional[Set[str]] = None) -> List[str]:
        """Find all modules that depend on the given module (recursively)"""
        if visited is None:
            visited = set()
        
        dependents = []
        
        for module in self.modules:
            if module["name"] in visited:
                continue
            
            deps = module.get("dependencies", [])
            if module_name in deps:
                visited.add(module["name"])
                dependents.append(module["name"])
                dependents.extend(self.find_dependents(module["name"], visited))
        
        return dependents
    
    def preview_manifest(self):
        """Preview the current manifest"""
        manifest = self.build_manifest()
        
        self.print_header("MANIFEST PREVIEW")
        print(json.dumps(manifest, indent=2))
    
    def build_manifest(self) -> Dict[str, Any]:
        """Build the complete manifest"""
        manifest = {
            "project_id": self.manifest.get("project_id", ""),
            "project_name": self.manifest.get("project_name", ""),
            "owner": self.manifest.get("owner", ""),
            "environment": self.manifest.get("environment", "development"),
            "modules": self.modules
        }
        
        if self.manifest.get("description"):
            manifest["description"] = self.manifest["description"]
        if self.manifest.get("version"):
            manifest["version"] = self.manifest["version"]
        if self.manifest.get("tags"):
            manifest["tags"] = self.manifest["tags"]
        if self.environments:
            manifest["environments"] = self.environments
        
        return manifest
    
    def save_manifest(self):
        """Save the manifest to file"""
        if not self.manifest.get("project_id"):
            self.print_error("Cannot save: project_id is required")
            return
        
        manifest = self.build_manifest()
        
        # Save to manifests directory (two levels up from examples/manifestor)
        manifests_dir = Path(__file__).parent.parent.parent / "manifests"
        manifests_dir.mkdir(exist_ok=True)
        filename = f"{self.manifest['project_id']}.json"
        filepath = manifests_dir / filename
        
        if filepath.exists():
            confirm = self.get_choice(
                f"\nFile '{filename}' already exists. Overwrite?",
                ["yes", "no"],
                "no"
            )
            if confirm == "no":
                self.print_info("Save cancelled")
                return
        
        try:
            with open(filepath, 'w') as f:
                json.dump(manifest, f, indent=2)
            self.print_success(f"Manifest saved to: {filepath}")
        except Exception as e:
            self.print_error(f"Failed to save manifest: {e}")
    
    def load_manifest(self):
        """Load an existing manifest"""
        # Load from manifests directory (two levels up from examples/manifestor)
        manifests_dir = Path(__file__).parent.parent.parent / "manifests"
        if not manifests_dir.exists():
            self.print_warning("Manifests directory not found")
            return
        json_files = list(manifests_dir.glob("*.json"))
        
        if not json_files:
            self.print_warning("No manifest files found")
            return
        
        self.print_header("AVAILABLE MANIFESTS")
        for i, filepath in enumerate(json_files, 1):
            print(f"{Fore.YELLOW}{i:>3}{Style.RESET_ALL}. {filepath.name}")
        
        choice = self.get_input("\nSelect manifest number to load (0 to cancel)")
        
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(json_files):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return
        
        filepath = json_files[idx]
        
        try:
            with open(filepath, 'r') as f:
                manifest_data = json.load(f)
            
            self.manifest = {
                "project_id": manifest_data.get("project_id", ""),
                "project_name": manifest_data.get("project_name", ""),
                "owner": manifest_data.get("owner", ""),
                "description": manifest_data.get("description", ""),
                "version": manifest_data.get("version", "1.0.0"),
                "environment": manifest_data.get("environment", "development"),
                "tags": manifest_data.get("tags", [])
            }
            
            self.modules = manifest_data.get("modules", [])
            self.environments = manifest_data.get("environments", self.create_default_environments())
            
            self.print_success(f"Loaded manifest: {filepath.name}")
        except Exception as e:
            self.print_error(f"Failed to load manifest: {e}")
    
    def run(self):
        """Main application loop"""
        self.print_header("CONTROL TOWER MANIFEST GENERATOR")
        print(f"{Fore.WHITE}Interactive tool for creating and managing project manifests{Style.RESET_ALL}\n")
        
        while True:
            print(f"\n{Fore.CYAN}Main Menu:{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}1{Style.RESET_ALL}. Create new manifest")
            print(f"  {Fore.YELLOW}2{Style.RESET_ALL}. Load existing manifest")
            print(f"  {Fore.YELLOW}3{Style.RESET_ALL}. Add module")
            print(f"  {Fore.YELLOW}4{Style.RESET_ALL}. Remove module")
            print(f"  {Fore.YELLOW}5{Style.RESET_ALL}. List modules")
            print(f"  {Fore.YELLOW}6{Style.RESET_ALL}. Preview manifest")
            print(f"  {Fore.YELLOW}7{Style.RESET_ALL}. Save manifest")
            print(f"  {Fore.YELLOW}0{Style.RESET_ALL}. Exit")
            
            choice = self.get_input("\nSelect option")
            
            if choice == "1":
                self.create_new_manifest()
            elif choice == "2":
                self.load_manifest()
            elif choice == "3":
                if not self.manifest.get("project_id"):
                    self.print_error("Please create or load a manifest first")
                else:
                    self.add_module()
            elif choice == "4":
                if not self.manifest.get("project_id"):
                    self.print_error("Please create or load a manifest first")
                else:
                    self.remove_module()
            elif choice == "5":
                self.list_modules()
            elif choice == "6":
                if not self.manifest.get("project_id"):
                    self.print_error("Please create or load a manifest first")
                else:
                    self.preview_manifest()
            elif choice == "7":
                self.save_manifest()
            elif choice == "0":
                print(f"\n{Fore.GREEN}Goodbye!{Style.RESET_ALL}\n")
                break
            else:
                self.print_error("Invalid option")


if __name__ == "__main__":
    try:
        generator = ManifestGenerator()
        generator.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}\n")
        sys.exit(0)
