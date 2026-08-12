"""
Diagnostics Module for AI Website Builder
==========================================
Provides comprehensive health checks for AUTH, SEED, and SERVER operations.
Used to validate generated applications before and during runtime.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class DiagnosticResult:
    """Result of a diagnostic check"""
    def __init__(self, name: str, passed: bool, message: str, details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
    
    def __str__(self):
        symbol = "✅" if self.passed else "❌"
        return f"{symbol} {self.name}: {self.message}"


class AuthDiagnostics:
    """Validates authentication system in generated app"""
    
    @staticmethod
    def check_auth_files_exist(repo_path: Path) -> List[DiagnosticResult]:
        """Check that all required auth files exist"""
        results = []
        required_files = [
            "app/auth.py",
            "app/routers/auth.py",
            "app/deps.py"
        ]
        
        for file_path in required_files:
            full_path = repo_path / file_path
            exists = full_path.exists()
            results.append(DiagnosticResult(
                f"Auth file: {file_path}",
                exists,
                "File exists" if exists else "File missing",
                f"Path: {full_path}"
            ))
        
        return results
    
    @staticmethod
    def check_auth_imports(repo_path: Path) -> List[DiagnosticResult]:
        """Check that auth.py has required imports"""
        results = []
        auth_file = repo_path / "app/auth.py"
        
        if not auth_file.exists():
            return [DiagnosticResult("Auth imports check", False, "auth.py not found")]
        
        content = auth_file.read_text(encoding="utf-8")
        required_imports = {
            "jose": "JWT token handling",
            "bcrypt": "Password hashing",
            "datetime": "Token expiration"
        }
        
        for import_name, description in required_imports.items():
            has_import = import_name in content
            results.append(DiagnosticResult(
                f"Auth import: {import_name}",
                has_import,
                f"{description} - imported" if has_import else f"{description} - NOT imported"
            ))
        
        return results
    
    @staticmethod
    def check_auth_routes(repo_path: Path) -> List[DiagnosticResult]:
        """Check that auth routes are properly defined"""
        results = []
        auth_router = repo_path / "app/routers/auth.py"
        main_file = repo_path / "app/main.py"
        
        if not auth_router.exists():
            return [DiagnosticResult("Auth routes", False, "auth.py router not found")]
        
        router_content = auth_router.read_text(encoding="utf-8")
        main_content = main_file.read_text(encoding="utf-8") if main_file.exists() else ""
        
        required_routes = {
            "/api/auth/register": "User registration",
            "/api/auth/login": "User login",
            "/api/auth/me": "Get current user"
        }
        
        for route, description in required_routes.items():
            # Check if route is defined
            path_defined = f'"{route}"' in router_content or f"'{route}'" in router_content
            results.append(DiagnosticResult(
                f"Auth route: {route}",
                path_defined,
                f"{description} - defined" if path_defined else f"{description} - NOT defined"
            ))
        
        # Check if router is included in main.py
        router_included = "include_router(auth_router" in main_content or "include_router(router" in main_content
        results.append(DiagnosticResult(
            "Auth router registration",
            router_included,
            "Router registered in main.py" if router_included else "Router NOT registered in main.py"
        ))
        
        return results
    
    @staticmethod
    def check_jwt_config(repo_path: Path) -> List[DiagnosticResult]:
        """Check that JWT is properly configured"""
        results = []
        auth_file = repo_path / "app/auth.py"
        env_file = repo_path / ".env" or repo_path / ".env.example"
        
        if not auth_file.exists():
            return [DiagnosticResult("JWT config", False, "auth.py not found")]
        
        content = auth_file.read_text(encoding="utf-8")
        
        required_configs = {
            "SECRET_KEY": "JWT secret key",
            "ALGORITHM": "JWT algorithm",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "Token expiration"
        }
        
        for config, description in required_configs.items():
            has_config = config in content
            results.append(DiagnosticResult(
                f"JWT config: {config}",
                has_config,
                f"{description} - configured" if has_config else f"{description} - NOT configured"
            ))
        
        return results


class SeedDiagnostics:
    """Validates seed script in generated app"""
    
    @staticmethod
    def check_seed_file_exists(repo_path: Path) -> DiagnosticResult:
        """Check that seed.py exists"""
        seed_file = repo_path / "seed.py"
        exists = seed_file.exists()
        return DiagnosticResult(
            "Seed file exists",
            exists,
            "seed.py found" if exists else "seed.py not found"
        )
    
    @staticmethod
    def check_seed_creates_admin(repo_path: Path) -> DiagnosticResult:
        """Check that seed.py creates admin user"""
        seed_file = repo_path / "seed.py"
        
        if not seed_file.exists():
            return DiagnosticResult("Seed creates admin", False, "seed.py not found")
        
        content = seed_file.read_text(encoding="utf-8")
        creates_admin = "Admin" in content or "admin" in content or "password" in content
        
        return DiagnosticResult(
            "Seed creates admin user",
            creates_admin,
            "Seed creates user/admin" if creates_admin else "Seed does NOT create admin user",
            content[:500] if not creates_admin else ""
        )
    
    @staticmethod
    def check_seed_imports(repo_path: Path) -> List[DiagnosticResult]:
        """Check that seed.py has required imports"""
        results = []
        seed_file = repo_path / "seed.py"
        
        if not seed_file.exists():
            return [DiagnosticResult("Seed imports", False, "seed.py not found")]
        
        content = seed_file.read_text(encoding="utf-8")
        required_imports = {
            "models": "SQLAlchemy models",
            "SessionLocal": "Database session",
            "Base": "Base class for models"
        }
        
        for import_name, description in required_imports.items():
            has_import = import_name in content
            results.append(DiagnosticResult(
                f"Seed import: {import_name}",
                has_import,
                f"{description} - imported" if has_import else f"{description} - NOT imported"
            ))
        
        return results
    
    @staticmethod
    def validate_seed_script(repo_path: Path, python_exe: str) -> DiagnosticResult:
        """Actually run seed.py and check for errors"""
        seed_file = repo_path / "seed.py"
        
        if not seed_file.exists():
            return DiagnosticResult("Seed script validation", False, "seed.py not found")
        
        try:
            result = subprocess.run(
                [python_exe, "seed.py"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return DiagnosticResult(
                    "Seed script validation",
                    True,
                    "Seed script runs successfully",
                    result.stdout[:500]
                )
            else:
                return DiagnosticResult(
                    "Seed script validation",
                    False,
                    f"Seed script failed with exit code {result.returncode}",
                    (result.stdout + result.stderr)[-1000:]
                )
        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                "Seed script validation",
                False,
                "Seed script timed out (>30s)"
            )
        except Exception as e:
            return DiagnosticResult(
                "Seed script validation",
                False,
                f"Error running seed: {str(e)}"
            )


class ServerDiagnostics:
    """Validates server configuration in generated app"""
    
    @staticmethod
    def check_fastapi_main(repo_path: Path) -> DiagnosticResult:
        """Check that main.py exists and has FastAPI app"""
        main_file = repo_path / "app/main.py"
        
        if not main_file.exists():
            return DiagnosticResult("FastAPI main", False, "app/main.py not found")
        
        content = main_file.read_text(encoding="utf-8")
        has_fastapi = "FastAPI" in content and "app =" in content
        
        return DiagnosticResult(
            "FastAPI app initialization",
            has_fastapi,
            "FastAPI app found" if has_fastapi else "FastAPI app NOT properly initialized"
        )
    
    @staticmethod
    def check_database_connection(repo_path: Path) -> DiagnosticResult:
        """Check that database connection is configured"""
        db_file = repo_path / "app/db.py"
        
        if not db_file.exists():
            return DiagnosticResult("Database config", False, "app/db.py not found")
        
        content = db_file.read_text(encoding="utf-8")
        has_db_url = "DATABASE_URL" in content or "sqlite" in content
        has_engine = "create_engine" in content
        
        passed = has_db_url and has_engine
        return DiagnosticResult(
            "Database configuration",
            passed,
            "Database properly configured" if passed else "Database NOT properly configured"
        )
    
    @staticmethod
    def check_router_registration(repo_path: Path) -> List[DiagnosticResult]:
        """Check that all routers are registered in main.py"""
        results = []
        main_file = repo_path / "app/main.py"
        
        if not main_file.exists():
            return [DiagnosticResult("Router registration", False, "app/main.py not found")]
        
        content = main_file.read_text(encoding="utf-8")
        
        expected_routers = {
            "auth_router": "Auth router",
            "generic_crud": "CRUD router"
        }
        
        for router_name, description in expected_routers.items():
            registered = f"include_router({router_name}" in content or f'include_router({router_name.replace("_", "")}' in content
            results.append(DiagnosticResult(
                f"Router: {router_name}",
                registered,
                f"{description} - registered" if registered else f"{description} - NOT registered"
            ))
        
        return results
    
    @staticmethod
    def check_server_startup(repo_path: Path, python_exe: str, port: int = 8000) -> DiagnosticResult:
        """Try to start the server and check if it responds"""
        try:
            # Set environment variables
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_path)
            env["PYTHONUTF8"] = "1"
            
            # Start server with timeout
            process = subprocess.Popen(
                [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", f"--port", str(port)],
                cwd=str(repo_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Give it 5 seconds to start
            import time
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                # Process is running
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                return DiagnosticResult(
                    "Server startup",
                    True,
                    f"Server started successfully on port {port}"
                )
            else:
                # Process exited
                stdout, stderr = process.communicate()
                return DiagnosticResult(
                    "Server startup",
                    False,
                    f"Server failed to start",
                    f"Error: {(stdout + stderr).decode()[-500:]}"
                )
        
        except Exception as e:
            return DiagnosticResult(
                "Server startup",
                False,
                f"Error starting server: {str(e)}"
            )


class ComprehensiveDiagnostics:
    """Run all diagnostics and provide a report"""
    
    @staticmethod
    def run_all_checks(repo_path: Path, python_exe: str) -> Dict:
        """Run all diagnostic checks"""
        repo_path = Path(repo_path)
        
        report = {
            "project_path": str(repo_path),
            "timestamp": str(__import__('datetime').datetime.now().isoformat()),
            "auth_checks": [],
            "seed_checks": [],
            "server_checks": [],
            "summary": {}
        }
        
        # Auth checks
        report["auth_checks"].extend(AuthDiagnostics.check_auth_files_exist(repo_path))
        report["auth_checks"].extend(AuthDiagnostics.check_auth_imports(repo_path))
        report["auth_checks"].extend(AuthDiagnostics.check_auth_routes(repo_path))
        report["auth_checks"].extend(AuthDiagnostics.check_jwt_config(repo_path))
        
        # Seed checks
        report["seed_checks"].append(SeedDiagnostics.check_seed_file_exists(repo_path))
        report["seed_checks"].append(SeedDiagnostics.check_seed_creates_admin(repo_path))
        report["seed_checks"].extend(SeedDiagnostics.check_seed_imports(repo_path))
        report["seed_checks"].append(SeedDiagnostics.validate_seed_script(repo_path, python_exe))
        
        # Server checks
        report["server_checks"].append(ServerDiagnostics.check_fastapi_main(repo_path))
        report["server_checks"].append(ServerDiagnostics.check_database_connection(repo_path))
        report["server_checks"].extend(ServerDiagnostics.check_router_registration(repo_path))
        report["server_checks"].append(ServerDiagnostics.check_server_startup(repo_path, python_exe))
        
        # Calculate summary
        all_checks = report["auth_checks"] + report["seed_checks"] + report["server_checks"]
        passed = sum(1 for check in all_checks if check.passed)
        total = len(all_checks)
        
        report["summary"] = {
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "status": "✅ PASS" if passed == total else "⚠️ PARTIAL PASS" if passed > total/2 else "❌ FAIL"
        }
        
        return report
    
    @staticmethod
    def print_report(report: Dict):
        """Pretty print the diagnostic report"""
        print("\n" + "="*70)
        print("DIAGNOSTIC REPORT - AI Website Builder Generated Application")
        print("="*70 + "\n")
        
        print(f"Project: {report['project_path']}")
        print(f"Time: {report['timestamp']}\n")
        
        print("📋 AUTH CHECKS:")
        print("-" * 70)
        for check in report["auth_checks"]:
            print(f"  {check}")
        
        print("\n📋 SEED CHECKS:")
        print("-" * 70)
        for check in report["seed_checks"]:
            print(f"  {check}")
        
        print("\n📋 SERVER CHECKS:")
        print("-" * 70)
        for check in report["server_checks"]:
            print(f"  {check}")
        
        print("\n" + "="*70)
        summary = report["summary"]
        print(f"SUMMARY: {summary['status']}")
        print(f"Passed: {summary['passed']}/{summary['total_checks']} ({summary['pass_rate']})")
        print("="*70 + "\n")
        
        return summary["passed"] == summary["total_checks"]


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        repo = Path(sys.argv[1])
        py_exe = sys.argv[2] if len(sys.argv) > 2 else sys.executable
        report = ComprehensiveDiagnostics.run_all_checks(repo, py_exe)
        ComprehensiveDiagnostics.print_report(report)
    else:
        print("Usage: python diagnostics.py <repo_path> [python_exe]")
