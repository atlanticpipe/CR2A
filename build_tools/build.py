"""
EXE Build System for CR2A Application.

This module provides a Python-based build automation tool that replaces the
failing build_cli.bat script. It provides a unified interface for building
both the CR2A GUI application and the ContractAnalysisCLI tool as standalone
Windows executables using PyInstaller.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class BuildConfig:
    """Configuration for a single build target.
    
    This dataclass holds all configuration needed to build a specific
    executable target using PyInstaller.
    
    Attributes:
        name: Target name (e.g., 'CR2A', 'ContractAnalysisCLI')
        entry_point: Main Python file path relative to project root
        output_name: Output executable name (without .exe extension)
        console_mode: True for console app, False for windowed (GUI)
        onefile: True for single-file mode, False for directory mode
        icon_path: Path to .ico file (GUI only), None for no icon
        data_files: List of (source, dest) pairs for bundled files
        hidden_imports: Modules to explicitly include that PyInstaller misses
        collect_packages: Packages to collect all data files from
        excludes: Packages to exclude from the bundle
    """
    name: str
    entry_point: Path
    output_name: str
    console_mode: bool
    onefile: bool
    icon_path: Optional[Path]
    data_files: List[Tuple[str, str]]
    hidden_imports: List[str]
    collect_packages: List[str]
    excludes: List[str]


@dataclass
class BuildResult:
    """Result of a build operation.
    
    This dataclass captures the outcome of a build attempt, including
    success/failure status, output information, and timing.
    
    Attributes:
        success: True if build completed successfully, False otherwise
        target_name: Name of the build target that was attempted
        output_path: Path to the generated executable (None if failed)
        output_size: Size of the executable in bytes (None if failed)
        error_message: Error description if build failed (None if succeeded)
        duration_seconds: Time taken for the build operation
    """
    success: bool
    target_name: str
    output_path: Optional[Path]
    output_size: Optional[int]
    error_message: Optional[str]
    duration_seconds: float


@dataclass
class InstallerConfig:
    """Configuration for NSIS installer generation.
    
    This dataclass holds all configuration needed to generate a Windows
    installer using NSIS (Nullsoft Scriptable Install System).
    
    Attributes:
        app_name: Display name of the application (e.g., "CR2A Contract Analysis")
        app_version: Version string (e.g., "1.0.0")
        publisher: Publisher name for registry entries
        exe_name: Main executable filename (e.g., "CR2A.exe")
        icon_path: Path to the application icon file
        nsis_script_path: Path to the NSIS script file
        input_dir: Directory containing the built application (dist/CR2A folder)
        output_dir: Directory for the generated installer (dist folder)
        output_name: Filename for the generated installer (e.g., "CR2A_Setup.exe")
    """
    app_name: str
    app_version: str
    publisher: str
    exe_name: str
    icon_path: Path
    nsis_script_path: Path
    input_dir: Path
    output_dir: Path
    output_name: str


# =============================================================================
# Build Configuration Instances
# =============================================================================

CLI_CONFIG = BuildConfig(
    name="ContractAnalysisCLI",
    entry_point=Path("analyzer/contract_analysis_cli.py"),
    output_name="ContractAnalysisCLI",
    console_mode=True,
    onefile=True,
    icon_path=None,
    data_files=[
        ("config/output_schemas_v1.json", "config"),
        ("config/validation_rules_v1.json", "config"),
    ],
    hidden_imports=[
        "pdfminer",
        "pdfminer.high_level",
        "pdfminer.layout",
        "pdfminer.pdfpage",
        "pdfminer.pdfparser",
        "pdfminer.pdfdocument",
        "pdfminer.pdfinterp",
        "pdfminer.converter",
        "docx",
        "openai",
        "jsonschema",
        "pytesseract",
        "pdf2image",
        "PIL",
        "PIL.Image",
        "analyzer",
        "analyzer.extract",
        "analyzer.openai_client",
        "analyzer.validator",
        "analyzer.contract_extractor",
    ],
    collect_packages=["pdfminer"],
    excludes=["pytest", "hypothesis", "IPython", "jupyter"],
)

GUI_CONFIG = BuildConfig(
    name="CR2A",
    entry_point=Path("src/qt_gui.py"),
    output_name="CR2A",
    console_mode=False,
    onefile=False,
    icon_path=Path("assets/icon.ico"),
    data_files=[
        ("assets", "assets"),
        ("config", "config"),
    ],
    hidden_imports=[
        # Core dependencies
        "tokenizers",
        "tkinter",
        "openai",
        "PyPDF2",
        "docx",
        "cryptography",
        # Cryptography submodules (often missed by PyInstaller)
        "cryptography.fernet",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.kdf",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.backends",
        "cryptography.hazmat.backends.openssl",
        "cryptography.hazmat.bindings",
        "cryptography.hazmat.bindings.openssl",
        "cryptography.hazmat.bindings._rust",
        "cryptography.x509",
        # All src modules
        "src.qt_gui",
        "src.application_controller",
        "src.config_manager",
        "src.gui_manager",
        "src.data_store",
        "src.json_loader",
        "src.error_handler",
        "src.upload_screen",
        "src.analysis_screen",
        "src.chat_screen",
        "src.analysis_engine",
        "src.analysis_models",
        "src.query_engine",
        "src.result_parser",
        "src.contract_uploader",
        "src.ui_styles",
        "src.settings_dialog",
        "src.openai_fallback_client",
        "src.contract_chat_ui",
    ],
    collect_packages=["tokenizers", "cryptography"],
    excludes=["pytest", "hypothesis", "pytest-cov", "IPython", "jupyter", "notebook"],
)

INSTALLER_CONFIG = InstallerConfig(
    app_name="CR2A Contract Analysis",
    app_version="1.0.0",
    publisher="CR2A",
    exe_name="CR2A.exe",
    icon_path=Path("assets/icon.ico"),
    nsis_script_path=Path("installer/cr2a_installer.nsi"),
    input_dir=Path("dist/CR2A"),
    output_dir=Path("dist"),
    output_name="CR2A_Setup.exe",
)


# =============================================================================
# Spec File Generator
# =============================================================================


class SpecGenerator:
    """Generates PyInstaller spec files from BuildConfig.
    
    This class creates PyInstaller .spec file content programmatically,
    ensuring consistent and maintainable build configurations.
    
    Attributes:
        project_root: Path to the project root directory for path calculations
    """
    
    def __init__(self, project_root: Path):
        """Initialize with project root for path calculations.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
    
    def generate(self, config: BuildConfig) -> str:
        """Generate spec file content for the given configuration.
        
        Creates a complete PyInstaller spec file that includes Analysis,
        PYZ, EXE, and optionally COLLECT blocks based on the configuration.
        
        Args:
            config: Build configuration containing all settings
            
        Returns:
            Complete spec file content as string
        """
        lines = []
        
        # Add header comment
        lines.append(f"# -*- mode: python ; coding: utf-8 -*-")
        lines.append(f"# Auto-generated spec file for {config.name}")
        lines.append(f"# Generated by EXE Build System")
        lines.append("")
        
        # Add Analysis block
        lines.append(self._generate_analysis_block(config))
        lines.append("")
        
        # Add PYZ block
        lines.append(self._generate_pyz_block())
        lines.append("")
        
        # Add EXE block
        lines.append(self._generate_exe_block(config))
        
        # Add COLLECT block if not onefile mode
        if not config.onefile:
            lines.append("")
            lines.append(self._generate_collect_block(config))
        
        return "\n".join(lines)
    
    def _generate_analysis_block(self, config: BuildConfig) -> str:
        """Generate the Analysis() block of the spec file.
        
        The Analysis block specifies the entry point, paths, data files,
        hidden imports, and exclusions for PyInstaller.
        
        Args:
            config: Build configuration
            
        Returns:
            Analysis block as string
        """
        # Calculate absolute path to entry point
        entry_point_abs = self.project_root / config.entry_point
        project_root_str = str(self.project_root).replace("\\", "/")
        entry_point_str = str(entry_point_abs).replace("\\", "/")
        
        # Format data files as list of tuples
        datas_list = []
        for source, dest in config.data_files:
            source_abs = str(self.project_root / source).replace("\\", "/")
            datas_list.append(f"    (r'{source_abs}', r'{dest}')")
        datas_str = "[\n" + ",\n".join(datas_list) + "\n]" if datas_list else "[]"
        
        # Format hidden imports
        hidden_imports_list = [f"    '{imp}'" for imp in config.hidden_imports]
        hidden_imports_str = "[\n" + ",\n".join(hidden_imports_list) + "\n]" if hidden_imports_list else "[]"
        
        # Format excludes
        excludes_list = [f"    '{exc}'" for exc in config.excludes]
        excludes_str = "[\n" + ",\n".join(excludes_list) + "\n]" if excludes_list else "[]"
        
        # Format collect_packages for collect_data_files and collect_submodules
        collect_calls = []
        for pkg in config.collect_packages:
            collect_calls.append(f"from PyInstaller.utils.hooks import collect_data_files, collect_submodules")
            break  # Only need to import once
        
        collect_datas = []
        collect_hiddenimports = []
        for pkg in config.collect_packages:
            collect_datas.append(f"collect_data_files('{pkg}')")
            collect_hiddenimports.append(f"collect_submodules('{pkg}')")
        
        # Build the Analysis block
        lines = []
        
        # Add collect imports if needed
        if config.collect_packages:
            lines.append("from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs")
            lines.append("")
            
            # Add collected data
            for pkg in config.collect_packages:
                lines.append(f"{pkg}_datas = collect_data_files('{pkg}')")
                lines.append(f"{pkg}_hiddenimports = collect_submodules('{pkg}')")
                lines.append(f"{pkg}_binaries = collect_dynamic_libs('{pkg}')")
            lines.append("")
        
        # Build binaries with collected packages
        if config.collect_packages:
            all_binaries = " + ".join([f"{pkg}_binaries" for pkg in config.collect_packages])
        else:
            all_binaries = "[]"
        
        # Build datas with collected packages
        if config.collect_packages:
            all_datas = datas_str
            for pkg in config.collect_packages:
                all_datas = f"{all_datas[:-1]} + {pkg}_datas" if all_datas != "[]" else f"{pkg}_datas"
            # Fix the syntax for combining lists
            if datas_list:
                combined_datas = "[\n" + ",\n".join(datas_list) + "\n]"
                for pkg in config.collect_packages:
                    combined_datas += f" + {pkg}_datas"
                all_datas = combined_datas
            else:
                all_datas = " + ".join([f"{pkg}_datas" for pkg in config.collect_packages])
        else:
            all_datas = datas_str
        
        # Build hiddenimports with collected packages
        if config.collect_packages:
            if hidden_imports_list:
                combined_hiddenimports = "[\n" + ",\n".join(hidden_imports_list) + "\n]"
                for pkg in config.collect_packages:
                    combined_hiddenimports += f" + {pkg}_hiddenimports"
                all_hiddenimports = combined_hiddenimports
            else:
                all_hiddenimports = " + ".join([f"{pkg}_hiddenimports" for pkg in config.collect_packages])
        else:
            all_hiddenimports = hidden_imports_str
        
        lines.append(f"a = Analysis(")
        lines.append(f"    [r'{entry_point_str}'],")
        lines.append(f"    pathex=[r'{project_root_str}'],")
        lines.append(f"    binaries={all_binaries},")
        lines.append(f"    datas={all_datas},")
        lines.append(f"    hiddenimports={all_hiddenimports},")
        lines.append(f"    hookspath=[],")
        lines.append(f"    hooksconfig={{}},")
        lines.append(f"    runtime_hooks=[],")
        lines.append(f"    excludes={excludes_str},")
        lines.append(f"    noarchive=False,")
        lines.append(f")")
        
        return "\n".join(lines)
    
    def _generate_pyz_block(self) -> str:
        """Generate the PYZ() block of the spec file.
        
        The PYZ block creates the Python archive containing bytecode.
        
        Returns:
            PYZ block as string
        """
        lines = [
            "pyz = PYZ(",
            "    a.pure,",
            "    a.zipped_data,",
            ")",
        ]
        return "\n".join(lines)
    
    def _generate_exe_block(self, config: BuildConfig) -> str:
        """Generate the EXE() block of the spec file.
        
        The EXE block specifies the executable settings including name,
        console mode, icon, and whether to create a single file.
        
        Args:
            config: Build configuration
            
        Returns:
            EXE block as string
        """
        # Determine console setting
        console_str = "True" if config.console_mode else "False"
        
        # Build icon line if specified
        if config.icon_path:
            icon_abs = str(self.project_root / config.icon_path).replace("\\", "/")
            icon_line = f"    icon=r'{icon_abs}',"
        else:
            icon_line = "    icon=None,"
        
        lines = [
            "exe = EXE(",
            "    pyz,",
            "    a.scripts,",
        ]
        
        # For onefile mode, include binaries, zipfiles, and datas in EXE
        if config.onefile:
            lines.extend([
                "    a.binaries,",
                "    a.zipfiles,",
                "    a.datas,",
            ])
        else:
            lines.append("    [],")
        
        lines.extend([
            f"    name='{config.output_name}',",
            "    debug=False,",
            "    bootloader_ignore_signals=False,",
            "    strip=False,",
            "    upx=True,",
            f"    console={console_str},",
            icon_line,
        ])
        
        # Add onefile-specific settings
        if config.onefile:
            lines.append("    upx_exclude=[],")
        
        lines.append(")")
        
        return "\n".join(lines)
    
    def _generate_collect_block(self, config: BuildConfig) -> str:
        """Generate the COLLECT() block for directory mode builds.
        
        The COLLECT block is only used when onefile=False, creating
        a directory with the executable and all dependencies.
        
        Args:
            config: Build configuration
            
        Returns:
            COLLECT block as string
        """
        lines = [
            "coll = COLLECT(",
            "    exe,",
            "    a.binaries,",
            "    a.zipfiles,",
            "    a.datas,",
            "    strip=False,",
            "    upx=True,",
            "    upx_exclude=[],",
            f"    name='{config.output_name}',",
            ")",
        ]
        return "\n".join(lines)


# =============================================================================
# Artifact Cleaner
# =============================================================================


class ArtifactCleaner:
    """Handles cleanup of PyInstaller build artifacts.
    
    This class manages the removal of temporary build files and directories
    created during the PyInstaller build process. It provides safe cleanup
    operations that log warnings on failure but never raise exceptions.
    
    Attributes:
        project_root: Path to the project root directory
    """
    
    def __init__(self, project_root: Path):
        """Initialize with project root directory.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
    
    def clean_pre_build(self, target_name: str) -> None:
        """Remove artifacts from previous builds of this target.
        
        Cleans up the existing executable in dist/ and the target's
        build subfolder to ensure a fresh build. Never removes the
        dist/ directory itself.
        
        Args:
            target_name: Name of the build target (e.g., 'CR2A', 'ContractAnalysisCLI')
        """
        # Remove existing exe in dist/ (but never the dist/ directory itself)
        exe_path = self.project_root / "dist" / f"{target_name}.exe"
        if exe_path.exists():
            self._safe_remove(exe_path)
        
        # Remove target's build subfolder
        build_subfolder = self.project_root / "build" / target_name
        if build_subfolder.exists():
            self._safe_remove(build_subfolder)
    
    def clean_post_build(self, target_name: str) -> None:
        """Remove temporary build artifacts after successful build.
        
        Cleans up the build/ directory and any generated .spec files
        from the project root. Never removes the dist/ directory.
        
        Args:
            target_name: Name of the build target (e.g., 'CR2A', 'ContractAnalysisCLI')
        """
        # Remove build/ directory
        build_dir = self.project_root / "build"
        if build_dir.exists():
            self._safe_remove(build_dir)
        
        # Remove generated .spec files from project root
        for spec_file in self.project_root.glob("*.spec"):
            self._safe_remove(spec_file)
    
    def _safe_remove(self, path: Path) -> bool:
        """Safely remove a file or directory, returning success status.
        
        Attempts to remove the specified path. If removal fails for any
        reason (permissions, file in use, etc.), logs a warning but does
        not raise an exception.
        
        Args:
            path: Path to the file or directory to remove
            
        Returns:
            True if removal succeeded, False otherwise
        """
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except Exception as e:
            print(f"Warning: Could not remove {path}: {e}")
            return False


# =============================================================================
# Installer Builder
# =============================================================================


class InstallerBuilder:
    """Handles NSIS installer compilation.
    
    This class manages the compilation of NSIS scripts into Windows installers.
    It verifies prerequisites (NSIS installation and built application) and
    executes the NSIS compiler to generate the installer executable.
    
    Attributes:
        project_root: Path to the project root directory
    """
    
    def __init__(self, project_root: Path):
        """Initialize with project root directory.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
    
    def _find_nsis(self) -> Optional[Path]:
        """Locate makensis.exe on the system.
        
        Searches for the NSIS compiler in the following locations:
        1. PATH environment variable
        2. Common installation directories (Program Files)
        
        Returns:
            Path to makensis.exe if found, None otherwise
        """
        # First, check if makensis is in PATH
        nsis_in_path = shutil.which("makensis")
        if nsis_in_path:
            return Path(nsis_in_path)
        
        # Check common installation locations
        common_locations = [
            Path("C:/Program Files/NSIS/makensis.exe"),
            Path("C:/Program Files (x86)/NSIS/makensis.exe"),
        ]
        
        for location in common_locations:
            if location.exists():
                return location
        
        return None
    
    def verify_prerequisites(self) -> bool:
        """Check that NSIS is installed and the application is built.
        
        Verifies that all prerequisites for building the installer are met:
        1. NSIS (makensis.exe) is installed and accessible
        2. The CR2A application has been built (dist/CR2A/CR2A.exe exists)
        
        Returns:
            True if all prerequisites are met, False otherwise.
            Error messages are printed to stdout when checks fail.
        """
        all_checks_passed = True
        
        # Check if NSIS is installed
        nsis_path = self._find_nsis()
        if nsis_path is None:
            print("ERROR: NSIS is not installed or not found.")
            print("Please install NSIS from https://nsis.sourceforge.io/")
            print("Or ensure makensis.exe is in your PATH.")
            all_checks_passed = False
        
        # Check if CR2A application is built
        app_exe_path = self.project_root / "dist" / "CR2A" / "CR2A.exe"
        if not app_exe_path.exists():
            print(f"ERROR: CR2A application not found at {app_exe_path}")
            print("Please build the application first with:")
            print("  python build_tools/build.py --target gui")
            all_checks_passed = False
        
        return all_checks_passed
    
    def build(self, config: InstallerConfig) -> BuildResult:
        """Compile NSIS script into installer.
        
        Executes the NSIS compiler (makensis.exe) with the specified
        configuration to generate the Windows installer.
        
        Args:
            config: InstallerConfig containing paths and settings
            
        Returns:
            BuildResult with success/failure info, output path, size, and timing
        """
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"Building Installer: {config.output_name}")
        print(f"{'='*60}")
        
        # Step 1: Find NSIS compiler
        print(f"[1/3] Locating NSIS compiler...")
        nsis_path = self._find_nsis()
        if nsis_path is None:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name="installer",
                output_path=None,
                output_size=None,
                error_message="NSIS compiler (makensis.exe) not found",
                duration_seconds=duration
            )
        print(f"      Found: {nsis_path}")
        
        # Step 2: Verify NSIS script exists
        nsis_script_path = self.project_root / config.nsis_script_path
        if not nsis_script_path.exists():
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name="installer",
                output_path=None,
                output_size=None,
                error_message=f"NSIS script not found: {nsis_script_path}",
                duration_seconds=duration
            )
        
        # Step 3: Execute NSIS compiler
        print(f"[2/3] Compiling NSIS script...")
        try:
            result = subprocess.run(
                [
                    str(nsis_path),
                    str(nsis_script_path)
                ],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                duration = time.time() - start_time
                error_output = result.stderr if result.stderr else result.stdout
                print(f"\nNSIS compilation failed with exit code {result.returncode}")
                print(f"Error output:\n{error_output}")
                return BuildResult(
                    success=False,
                    target_name="installer",
                    output_path=None,
                    output_size=None,
                    error_message=f"NSIS compilation failed with exit code {result.returncode}: {error_output}",
                    duration_seconds=duration
                )
        except FileNotFoundError:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name="installer",
                output_path=None,
                output_size=None,
                error_message=f"NSIS compiler not found at: {nsis_path}",
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name="installer",
                output_path=None,
                output_size=None,
                error_message=f"Failed to execute NSIS compiler: {e}",
                duration_seconds=duration
            )
        
        # Step 4: Verify output and get file size
        print(f"[3/3] Verifying output...")
        output_path = self.project_root / config.output_dir / config.output_name
        
        if not output_path.exists():
            duration = time.time() - start_time
            print(f"\nERROR: Compilation completed but installer not found: {output_path}")
            return BuildResult(
                success=False,
                target_name="installer",
                output_path=None,
                output_size=None,
                error_message=f"Compilation completed but installer not found: {output_path}",
                duration_seconds=duration
            )
        
        output_size = output_path.stat().st_size
        duration = time.time() - start_time
        
        # Report success
        print(f"\n{'='*60}")
        print(f"BUILD SUCCESSFUL: {config.output_name}")
        print(f"Output: {output_path}")
        print(f"Size: {output_size / (1024*1024):.2f} MB")
        print(f"Duration: {duration:.1f} seconds")
        print(f"{'='*60}\n")
        
        return BuildResult(
            success=True,
            target_name="installer",
            output_path=output_path,
            output_size=output_size,
            error_message=None,
            duration_seconds=duration
        )


# =============================================================================
# Build Manager
# =============================================================================


class BuildManager:
    """Orchestrates the build process for CR2A executables.
    
    This class coordinates the SpecGenerator and ArtifactCleaner components
    to execute PyInstaller builds for the specified targets. It handles
    the complete build lifecycle including pre-build cleanup, spec file
    generation, PyInstaller execution, and post-build cleanup.
    
    Attributes:
        project_root: Path to the project root directory
        spec_generator: SpecGenerator instance for creating spec files
        artifact_cleaner: ArtifactCleaner instance for managing build artifacts
    """
    
    def __init__(self, project_root: Path):
        """Initialize with project root directory.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self.spec_generator = SpecGenerator(project_root)
        self.artifact_cleaner = ArtifactCleaner(project_root)
    
    def verify_prerequisites(self) -> bool:
        """Check that PyInstaller and required files exist.
        
        Verifies that all prerequisites for building are met:
        1. PyInstaller is installed and importable
        2. Entry point files exist for both CLI and GUI configurations
        
        Returns:
            True if all prerequisites are met, False otherwise.
            Error messages are printed to stdout when checks fail.
        """
        all_checks_passed = True
        
        # Check if PyInstaller is importable
        try:
            import PyInstaller
        except ImportError:
            print("ERROR: PyInstaller is not installed.")
            print("Install with: pip install pyinstaller")
            all_checks_passed = False
        
        # Check if entry point files exist for both configurations
        for config in [CLI_CONFIG, GUI_CONFIG]:
            entry_path = self.project_root / config.entry_point
            if not entry_path.exists():
                print(f"ERROR: Entry point not found: {entry_path}")
                all_checks_passed = False
        
        return all_checks_passed
    
    def build(self, target: str) -> BuildResult:
        """Execute build for specified target.
        
        Builds the specified target(s) by coordinating spec generation,
        artifact cleanup, and PyInstaller execution. For 'all' target,
        builds both GUI and CLI sequentially.
        
        Args:
            target: One of 'gui', 'cli', or 'all'
            
        Returns:
            BuildResult with success/failure info. For 'all' target,
            returns the result of the last build (CLI), with success=True
            only if both builds succeeded.
        """
        target = target.lower()
        
        if target == 'gui':
            return self._build_target(GUI_CONFIG)
        elif target == 'cli':
            return self._build_target(CLI_CONFIG)
        elif target == 'all':
            # Build both targets sequentially
            gui_result = self._build_target(GUI_CONFIG)
            if not gui_result.success:
                return gui_result
            
            cli_result = self._build_target(CLI_CONFIG)
            
            # Return combined result - success only if both succeeded
            return BuildResult(
                success=cli_result.success,
                target_name='all',
                output_path=cli_result.output_path,
                output_size=cli_result.output_size,
                error_message=cli_result.error_message,
                duration_seconds=gui_result.duration_seconds + cli_result.duration_seconds
            )
        elif target == 'installer':
            # Build Windows installer using NSIS
            installer_builder = InstallerBuilder(self.project_root)
            if not installer_builder.verify_prerequisites():
                return BuildResult(
                    success=False,
                    target_name='installer',
                    output_path=None,
                    output_size=None,
                    error_message="Installer prerequisites not met. See errors above.",
                    duration_seconds=0.0
                )
            return installer_builder.build(INSTALLER_CONFIG)
        else:
            return BuildResult(
                success=False,
                target_name=target,
                output_path=None,
                output_size=None,
                error_message=f"Invalid target: '{target}'. Must be 'gui', 'cli', 'all', or 'installer'.",
                duration_seconds=0.0
            )
    
    def _build_target(self, config: BuildConfig) -> BuildResult:
        """Build a single target using the provided configuration.
        
        Executes the complete build process for a single target:
        1. Pre-build cleanup of previous artifacts
        2. Generate PyInstaller spec file
        3. Write spec file to temp location
        4. Execute PyInstaller via subprocess
        5. Post-build cleanup on success
        
        Args:
            config: Build configuration for the target
            
        Returns:
            BuildResult with success/failure info, output path, size, and timing
        """
        start_time = time.time()
        
        # Step 1: Pre-build cleanup
        print(f"\n{'='*60}")
        print(f"Building {config.name}")
        print(f"{'='*60}")
        print(f"[1/4] Cleaning previous build artifacts...")
        self.artifact_cleaner.clean_pre_build(config.name)
        
        # Step 2: Generate spec file content
        print(f"[2/4] Generating PyInstaller spec file...")
        spec_content = self.spec_generator.generate(config)
        
        # Step 3: Write spec file to temp location
        spec_file_path = self.project_root / f"{config.name}.spec"
        try:
            spec_file_path.write_text(spec_content, encoding='utf-8')
        except Exception as e:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name=config.name,
                output_path=None,
                output_size=None,
                error_message=f"Failed to write spec file: {e}",
                duration_seconds=duration
            )
        
        # Step 4: Execute PyInstaller via subprocess
        print(f"[3/4] Running PyInstaller...")
        try:
            result = subprocess.run(
                [
                    'pyinstaller',
                    '--clean',
                    '--noconfirm',
                    str(spec_file_path)
                ],
                cwd=str(self.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                duration = time.time() - start_time
                error_output = result.stderr if result.stderr else result.stdout
                print(f"\nPyInstaller failed with exit code {result.returncode}")
                print(f"Error output:\n{error_output}")
                return BuildResult(
                    success=False,
                    target_name=config.name,
                    output_path=None,
                    output_size=None,
                    error_message=f"PyInstaller failed with exit code {result.returncode}: {error_output}",
                    duration_seconds=duration
                )
        except FileNotFoundError:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name=config.name,
                output_path=None,
                output_size=None,
                error_message="PyInstaller not found. Install with: pip install pyinstaller",
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            return BuildResult(
                success=False,
                target_name=config.name,
                output_path=None,
                output_size=None,
                error_message=f"Failed to execute PyInstaller: {e}",
                duration_seconds=duration
            )
        
        # Step 5: Verify output and get file size
        print(f"[4/4] Verifying output...")
        
        # For folder-based builds, check for folder/exe, otherwise check for exe
        if config.onefile:
            output_path = self.project_root / "dist" / f"{config.output_name}.exe"
        else:
            output_path = self.project_root / "dist" / config.output_name / f"{config.output_name}.exe"
        
        if not output_path.exists():
            duration = time.time() - start_time
            print(f"\nERROR: Build completed but output file not found: {output_path}")
            return BuildResult(
                success=False,
                target_name=config.name,
                output_path=None,
                output_size=None,
                error_message=f"Build completed but output file not found: {output_path}",
                duration_seconds=duration
            )
        
        output_size = output_path.stat().st_size
        
        # Step 6: Post-build cleanup
        print(f"      Cleaning up build artifacts...")
        self.artifact_cleaner.clean_post_build(config.name)
        
        duration = time.time() - start_time
        
        # Report success
        print(f"\n{'='*60}")
        print(f"BUILD SUCCESSFUL: {config.name}")
        
        if config.onefile:
            # For single-file builds, show file path and size
            print(f"Output: {output_path}")
            print(f"Size: {output_size / (1024*1024):.2f} MB")
        else:
            # For folder-based builds, show folder path, exe path, and total folder size
            folder_path = output_path.parent
            total_size = sum(f.stat().st_size for f in folder_path.rglob('*') if f.is_file())
            print(f"Output Folder: {folder_path}")
            print(f"Executable: {output_path}")
            print(f"Total Size: {total_size / (1024*1024):.2f} MB")
        
        print(f"Duration: {duration:.1f} seconds")
        print(f"{'='*60}\n")
        
        return BuildResult(
            success=True,
            target_name=config.name,
            output_path=output_path,
            output_size=output_size,
            error_message=None,
            duration_seconds=duration
        )


# =============================================================================
# CLI Interface
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Creates an argument parser for the build script with the --target
    argument that accepts 'gui', 'cli', or 'all' as valid choices.
    
    Returns:
        Parsed arguments namespace with 'target' attribute
    """
    parser = argparse.ArgumentParser(
        prog='build.py',
        description='Build CR2A executables using PyInstaller.',
        epilog='''
Examples:
  python build.py --target gui       Build only the GUI application (CR2A.exe)
  python build.py --target cli       Build only the CLI tool (ContractAnalysisCLI.exe)
  python build.py --target all       Build both executables
  python build.py --target installer Build the Windows installer (CR2A_Setup.exe)
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--target',
        choices=['gui', 'cli', 'all', 'installer'],
        required=True,
        help='Build target: gui (CR2A.exe), cli (ContractAnalysisCLI.exe), all (both), or installer (CR2A_Setup.exe)'
    )
    
    # If no arguments provided, print help and exit
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for build script.
    
    Parses command-line arguments, creates a BuildManager, verifies
    prerequisites, and executes the build for the specified target.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Determine project root (parent of build_tools directory)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    # Create build manager
    manager = BuildManager(project_root)
    
    # Verify prerequisites before building
    if not manager.verify_prerequisites():
        return 1
    
    # Execute build
    result = manager.build(args.target)
    
    # Return appropriate exit code
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
