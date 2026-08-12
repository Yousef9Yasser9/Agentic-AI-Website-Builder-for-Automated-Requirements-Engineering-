"""
PRE-RUN TEST SCRIPT
===================
Comprehensive test to verify everything works before the 20-30 minute run.
Run this script to check all components are ready.

Usage:
    python PRE_RUN_TEST.py
"""

import sys
import os
import json
import subprocess
from pathlib import Path
import requests

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

# Test Results
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def test_python_version():
    """Test 1: Check Python version"""
    print_header("TEST 1: Python Version")
    version = sys.version_info
    print_info(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 10:
        print_success("Python 3.10+ detected")
        test_results["passed"].append("Python version")
        return True
    else:
        print_error(f"Python 3.10+ required, found {version.major}.{version.minor}")
        test_results["failed"].append("Python version")
        return False

def test_project_structure():
    """Test 2: Check project structure"""
    print_header("TEST 2: Project Structure")
    
    required_dirs = [
        "builder",
        "generated_apps",
        "checkpoints",
        "routers",
        "templates"
    ]
    
    required_files = [
        "builder/app.py",
        "builder/ollama_client.py",
        "builder/checkpoint_manager.py",
        "builder/blueprint_generator.py",
        "builder/cleanup_manager.py",
        "builder/prompts.py",
        "generated_apps/generator/repo_generator.py",
        "generated_apps/generator/codegen_prompts.py"
    ]
    
    all_good = True
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print_success(f"Directory exists: {dir_name}/")
        else:
            print_error(f"Missing directory: {dir_name}/")
            all_good = False
    
    for file_name in required_files:
        if Path(file_name).exists():
            print_success(f"File exists: {file_name}")
        else:
            print_error(f"Missing file: {file_name}")
            all_good = False
    
    if all_good:
        test_results["passed"].append("Project structure")
    else:
        test_results["failed"].append("Project structure")
    
    return all_good

def test_dependencies():
    """Test 3: Check Python dependencies"""
    print_header("TEST 3: Python Dependencies")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "requests",
        "psutil",
        "jinja2"
    ]
    
    all_good = True
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"Package installed: {package}")
        except ImportError:
            print_error(f"Missing package: {package}")
            all_good = False
    
    if all_good:
        test_results["passed"].append("Python dependencies")
    else:
        test_results["failed"].append("Python dependencies")
        print_warning("Run: pip install -r requirements.txt")
    
    return all_good

def test_ollama_connection():
    """Test 4: Check Ollama connection"""
    print_header("TEST 4: Ollama Connection")
    
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print_success("Ollama is running")
            
            data = response.json()
            models = data.get("models", [])
            print_info(f"Found {len(models)} models")
            
            test_results["passed"].append("Ollama connection")
            return True
        else:
            print_error(f"Ollama returned status code: {response.status_code}")
            test_results["failed"].append("Ollama connection")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to Ollama at http://127.0.0.1:11434")
        print_warning("Start Ollama with: ollama serve")
        test_results["failed"].append("Ollama connection")
        return False
    except Exception as e:
        print_error(f"Error checking Ollama: {e}")
        test_results["failed"].append("Ollama connection")
        return False

def test_ollama_models():
    """Test 5: Check required Ollama models"""
    print_header("TEST 5: Ollama Models")
    
    required_models = ["llama3.1:8b", "qwen2.5-coder:14b"]
    
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        data = response.json()
        installed_models = [m["name"] for m in data.get("models", [])]
        
        all_good = True
        for model in required_models:
            # Check if model name is in any of the installed models
            found = any(model in installed for installed in installed_models)
            if found:
                print_success(f"Model available: {model}")
            else:
                print_error(f"Model missing: {model}")
                print_warning(f"Pull with: ollama pull {model}")
                all_good = False
        
        if all_good:
            test_results["passed"].append("Ollama models")
        else:
            test_results["failed"].append("Ollama models")
        
        return all_good
    except Exception as e:
        print_error(f"Error checking models: {e}")
        test_results["failed"].append("Ollama models")
        return False

def test_ollama_inference():
    """Test 6: Test Ollama inference"""
    print_header("TEST 6: Ollama Inference Test")
    
    try:
        print_info("Sending test request to Ollama...")
        
        payload = {
            "model": "llama3.1:8b",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OK' if you can hear me."}
            ],
            "options": {
                "temperature": 0.1,
                "num_predict": 10,
                "num_ctx": 2048,
                "num_gpu": 999
            },
            "stream": False
        }
        
        response = requests.post(
            "http://127.0.0.1:11434/api/chat",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("message", {}).get("content", "")
            print_success(f"Ollama responded: {content[:50]}")
            test_results["passed"].append("Ollama inference")
            return True
        else:
            print_error(f"Ollama inference failed with status: {response.status_code}")
            test_results["failed"].append("Ollama inference")
            return False
    except Exception as e:
        print_error(f"Ollama inference test failed: {e}")
        test_results["failed"].append("Ollama inference")
        return False

def test_file_imports():
    """Test 7: Test Python imports"""
    print_header("TEST 7: Python Module Imports")
    
    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "builder"))
    
    modules_to_test = [
        ("ollama_client", "builder/ollama_client.py"),
        ("checkpoint_manager", "builder/checkpoint_manager.py"),
        ("blueprint_generator", "builder/blueprint_generator.py"),
        ("cleanup_manager", "builder/cleanup_manager.py"),
        ("prompts", "builder/prompts.py")
    ]
    
    all_good = True
    
    for module_name, file_path in modules_to_test:
        try:
            __import__(module_name)
            print_success(f"Import successful: {module_name}")
        except Exception as e:
            print_error(f"Import failed: {module_name} - {e}")
            all_good = False
    
    if all_good:
        test_results["passed"].append("Python imports")
    else:
        test_results["failed"].append("Python imports")
    
    return all_good

def test_disk_space():
    """Test 8: Check available disk space"""
    print_header("TEST 8: Disk Space")
    
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        
        free_gb = free / (1024**3)
        print_info(f"Free disk space: {free_gb:.2f} GB")
        
        if free_gb > 5:
            print_success("Sufficient disk space available")
            test_results["passed"].append("Disk space")
            return True
        elif free_gb > 2:
            print_warning(f"Low disk space: {free_gb:.2f} GB (recommend 5+ GB)")
            test_results["warnings"].append("Low disk space")
            return True
        else:
            print_error(f"Insufficient disk space: {free_gb:.2f} GB (need at least 2 GB)")
            test_results["failed"].append("Disk space")
            return False
    except Exception as e:
        print_warning(f"Could not check disk space: {e}")
        test_results["warnings"].append("Disk space check failed")
        return True

def test_write_permissions():
    """Test 9: Check write permissions"""
    print_header("TEST 9: Write Permissions")
    
    test_dirs = ["checkpoints", "generated_apps"]
    
    all_good = True
    
    for dir_name in test_dirs:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        
        test_file = dir_path / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            print_success(f"Write permission OK: {dir_name}/")
        except Exception as e:
            print_error(f"No write permission: {dir_name}/ - {e}")
            all_good = False
    
    if all_good:
        test_results["passed"].append("Write permissions")
    else:
        test_results["failed"].append("Write permissions")
    
    return all_good

def print_summary():
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    total_tests = len(test_results["passed"]) + len(test_results["failed"])
    
    print(f"\n{Colors.BOLD}Total Tests: {total_tests}{Colors.END}")
    print(f"{Colors.GREEN}Passed: {len(test_results['passed'])}{Colors.END}")
    print(f"{Colors.RED}Failed: {len(test_results['failed'])}{Colors.END}")
    print(f"{Colors.YELLOW}Warnings: {len(test_results['warnings'])}{Colors.END}")
    
    if test_results["passed"]:
        print(f"\n{Colors.GREEN}✓ Passed Tests:{Colors.END}")
        for test in test_results["passed"]:
            print(f"  • {test}")
    
    if test_results["failed"]:
        print(f"\n{Colors.RED}✗ Failed Tests:{Colors.END}")
        for test in test_results["failed"]:
            print(f"  • {test}")
    
    if test_results["warnings"]:
        print(f"\n{Colors.YELLOW}⚠ Warnings:{Colors.END}")
        for warning in test_results["warnings"]:
            print(f"  • {warning}")
    
    print("\n" + "="*60)
    
    if len(test_results["failed"]) == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.END}")
        print(f"{Colors.GREEN}Your project is ready for the 20-30 minute run.{Colors.END}\n")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.END}")
        print(f"{Colors.RED}Please fix the issues above before running.{Colors.END}\n")
        return False

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         AI WEBSITE BUILDER - PRE-RUN TEST SUITE           ║")
    print("║                                                            ║")
    print("║  This will verify all components before your long run     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Run all tests
    test_python_version()
    test_project_structure()
    test_dependencies()
    test_ollama_connection()
    test_ollama_models()
    test_ollama_inference()
    test_file_imports()
    test_disk_space()
    test_write_permissions()
    
    # Print summary
    success = print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
