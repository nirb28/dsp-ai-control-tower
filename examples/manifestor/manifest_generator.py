#!/usr/bin/env python3
"""
Manifest Generator CLI - Interactive tool for creating and managing Control Tower manifests
"""

import json
import re
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
    
    def _list_manifest_files(self) -> List[Path]:
        """List available manifest files in the project's manifests directory"""
        manifests_dir = Path(__file__).parent.parent.parent / "manifests"
        if not manifests_dir.exists():
            self.print_warning("Manifests directory not found")
            return []
        return sorted(manifests_dir.glob("*.json"))

    def _select_manifest_for_sync(self) -> Optional[str]:
        """Allow user to select a manifest to sync, or choose all. Returns project_id or 'ALL' or None."""
        manifests = self._list_manifest_files()
        if not manifests:
            return None
        self.print_header("SELECT MANIFEST FOR SYNC")
        print(f"{Fore.YELLOW}  0{Style.RESET_ALL}. Cancel")
        print(f"{Fore.YELLOW}  A{Style.RESET_ALL}. All manifests")
        for i, mpath in enumerate(manifests, 1):
            print(f"{Fore.YELLOW}{i:>3}{Style.RESET_ALL}. {mpath.name}")
        choice = self.get_input("\nSelect option")
        if choice.lower() == '0':
            return None
        if choice.lower() == 'a':
            return 'ALL'
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(manifests):
                return Path(manifests[idx]).stem
        except ValueError:
            pass
        self.print_error("Invalid selection")
        return None

    def sync_manifests(self):
        """Sync manifests to gateway via Front Door /admin/sync endpoint"""
        self.print_header("SYNC MANIFESTS TO GATEWAY")
        selection = self._select_manifest_for_sync()
        if selection is None:
            self.print_info("Sync cancelled")
            return
        base_url = self.get_input("Front Door base URL", "http://localhost:8080")
        # Lazy import requests to avoid hard dependency
        try:
            import requests  # type: ignore
        except Exception:
            self.print_error("The 'requests' package is required. Install with: pip install requests")
            return
        try:
            url = f"{base_url.rstrip('/')}/admin/sync"
            params = {}
            if selection != 'ALL':
                params = {"project_id": selection}
            resp = requests.post(url, params=params, timeout=60)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    data = {"text": resp.text}
                self.print_success("Sync completed successfully")
                self.print_info(f"Response summary: {str(data)[:500]}")
            else:
                self.print_error(f"Sync failed: {resp.status_code} - {resp.text[:500]}")
        except Exception as e:
            self.print_error(f"Failed to call sync endpoint: {e}")
    
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

    def _list_template_files(self) -> List[Path]:
        """List available template files in the templates directory"""
        templates_dir = Path(__file__).parent / "templates"
        if not templates_dir.exists():
            self.print_warning("No templates directory found (examples/manifestor/templates)")
            return []
        return sorted(templates_dir.glob("*.json"))

    def _extract_template_vars(self, content: str) -> List[str]:
        """Extract unique variable names matching ${t.<name>} from template content"""
        pattern = re.compile(r"\$\{t\.([a-zA-Z0-9_.-]+)\}")
        return sorted(set(m.group(1) for m in pattern.finditer(content)))

    def _render_template_content(self, content: str, values: Dict[str, str]) -> str:
        """Replace ${t.var} placeholders with provided values"""
        def repl(match: re.Match) -> str:
            key = match.group(1)
            return values.get(key, match.group(0))
        return re.sub(r"\$\{t\.([a-zA-Z0-9_.-]+)\}", repl, content)

    def create_from_template(self):
        """Create a manifest from a JSON template by substituting ${t.*} variables"""
        self.print_header("CREATE MANIFEST FROM TEMPLATE")

        templates = self._list_template_files()
        if not templates:
            return

        print("Available templates:")
        for i, tpath in enumerate(templates, 1):
            print(f"  {i}. {tpath.name}")

        choice = self.get_input("\nSelect template number (0 to cancel)")
        try:
            idx = int(choice) - 1
            if idx == -1:
                return
            if idx < 0 or idx >= len(templates):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        template_path = templates[idx]
        try:
            raw = template_path.read_text(encoding="utf-8")
        except Exception as e:
            self.print_error(f"Failed to read template: {e}")
            return

        vars_needed = self._extract_template_vars(raw)
        values: Dict[str, str] = {}
        if vars_needed:
            self.print_info("Provide values for template variables (press Enter to leave unchanged)")
        for var in vars_needed:
            prompt = var
            default = None
            # convenience defaults
            if var == "project_id":
                default = self.manifest.get("project_id") or ""
            if var == "environment":
                default = self.manifest.get("environment") or "development"
            values[var] = self.get_input(prompt, default)

        rendered = self._render_template_content(raw, values)

        # Validate JSON
        try:
            manifest_obj = json.loads(rendered)
        except json.JSONDecodeError as e:
            self.print_error(f"Rendered template is not valid JSON: {e}")
            return

        project_id = manifest_obj.get("project_id") or values.get("project_id") or ""
        if not project_id:
            self.print_error("project_id is required in the rendered manifest")
            return

        # Save to manifests directory
        manifests_dir = Path(__file__).parent.parent.parent / "manifests"
        manifests_dir.mkdir(exist_ok=True)
        filename = f"{project_id}.json"
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
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(manifest_obj, f, indent=2)
            self.print_success(f"Manifest generated from template and saved to: {filepath}")
        except Exception as e:
            self.print_error(f"Failed to save manifest: {e}")
    
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
            print(f"  {Fore.YELLOW}8{Style.RESET_ALL}. Create manifest from template")
            print(f"  {Fore.YELLOW}9{Style.RESET_ALL}. Sync manifests to gateway")
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
            elif choice == "8":
                self.create_from_template()
            elif choice == "9":
                self.sync_manifests()
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

    
