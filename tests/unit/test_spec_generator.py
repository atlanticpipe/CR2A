"""
Unit tests for the SpecGenerator class.

Tests verify that the SpecGenerator correctly generates PyInstaller spec files
from BuildConfig instances.
"""

import pytest
from pathlib import Path
from build_tools.build import SpecGenerator, BuildConfig, CLI_CONFIG, GUI_CONFIG


class TestSpecGenerator:
    """Tests for SpecGenerator class."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project root for testing."""
        return tmp_path
    
    @pytest.fixture
    def generator(self, project_root):
        """Create a SpecGenerator instance."""
        return SpecGenerator(project_root)
    
    @pytest.fixture
    def simple_config(self):
        """Create a simple BuildConfig for testing."""
        return BuildConfig(
            name="TestApp",
            entry_point=Path("src/main.py"),
            output_name="TestApp",
            console_mode=True,
            onefile=True,
            icon_path=None,
            data_files=[("config/test.json", "config")],
            hidden_imports=["module1", "module2"],
            collect_packages=[],
            excludes=["pytest", "hypothesis"],
        )
    
    def test_generate_returns_string(self, generator, simple_config):
        """Test that generate() returns a string."""
        result = generator.generate(simple_config)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_generate_includes_header(self, generator, simple_config):
        """Test that generated spec includes header comments."""
        result = generator.generate(simple_config)
        assert "# -*- mode: python ; coding: utf-8 -*-" in result
        assert f"# Auto-generated spec file for {simple_config.name}" in result
    
    def test_generate_includes_analysis_block(self, generator, simple_config):
        """Test that generated spec includes Analysis block."""
        result = generator.generate(simple_config)
        assert "a = Analysis(" in result
        assert "pathex=" in result
        assert "binaries=[]" in result
        assert "datas=" in result
        assert "hiddenimports=" in result
        assert "excludes=" in result
    
    def test_generate_includes_pyz_block(self, generator, simple_config):
        """Test that generated spec includes PYZ block."""
        result = generator.generate(simple_config)
        assert "pyz = PYZ(" in result
        assert "a.pure" in result
        assert "a.zipped_data" in result
    
    def test_generate_includes_exe_block(self, generator, simple_config):
        """Test that generated spec includes EXE block."""
        result = generator.generate(simple_config)
        assert "exe = EXE(" in result
        assert f"name='{simple_config.output_name}'" in result
    
    def test_generate_console_mode_true(self, generator, simple_config):
        """Test that console mode is correctly set to True."""
        simple_config.console_mode = True
        result = generator.generate(simple_config)
        assert "console=True" in result
    
    def test_generate_console_mode_false(self, generator, simple_config):
        """Test that console mode is correctly set to False."""
        simple_config.console_mode = False
        result = generator.generate(simple_config)
        assert "console=False" in result
    
    def test_generate_includes_hidden_imports(self, generator, simple_config):
        """Test that hidden imports are included in the spec."""
        result = generator.generate(simple_config)
        for imp in simple_config.hidden_imports:
            assert f"'{imp}'" in result
    
    def test_generate_includes_excludes(self, generator, simple_config):
        """Test that excludes are included in the spec."""
        result = generator.generate(simple_config)
        for exc in simple_config.excludes:
            assert f"'{exc}'" in result
    
    def test_generate_includes_data_files(self, generator, simple_config):
        """Test that data files are included in the spec."""
        result = generator.generate(simple_config)
        # Data files should be in the datas section
        assert "config" in result  # destination folder
    
    def test_generate_onefile_mode(self, generator, simple_config):
        """Test that onefile mode includes binaries in EXE."""
        simple_config.onefile = True
        result = generator.generate(simple_config)
        assert "a.binaries" in result
        assert "a.zipfiles" in result
        assert "a.datas" in result
        # Should NOT have COLLECT block
        assert "coll = COLLECT(" not in result
    
    def test_generate_onedir_mode(self, generator, simple_config):
        """Test that onedir mode includes COLLECT block."""
        simple_config.onefile = False
        result = generator.generate(simple_config)
        assert "coll = COLLECT(" in result
    
    def test_generate_with_icon(self, generator, simple_config):
        """Test that icon path is included when specified."""
        simple_config.icon_path = Path("assets/icon.ico")
        result = generator.generate(simple_config)
        assert "icon=" in result
        assert "icon.ico" in result
    
    def test_generate_without_icon(self, generator, simple_config):
        """Test that icon is None when not specified."""
        simple_config.icon_path = None
        result = generator.generate(simple_config)
        assert "icon=None" in result
    
    def test_generate_with_collect_packages(self, generator, simple_config):
        """Test that collect_packages generates proper imports."""
        simple_config.collect_packages = ["transformers", "torch"]
        result = generator.generate(simple_config)
        assert "from PyInstaller.utils.hooks import collect_data_files, collect_submodules" in result
        assert "transformers_datas = collect_data_files('transformers')" in result
        assert "torch_datas = collect_data_files('torch')" in result
        assert "transformers_hiddenimports = collect_submodules('transformers')" in result
        assert "torch_hiddenimports = collect_submodules('torch')" in result


class TestSpecGeneratorWithRealConfigs:
    """Tests using the actual CLI_CONFIG and GUI_CONFIG."""
    
    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project root for testing."""
        return tmp_path
    
    @pytest.fixture
    def generator(self, project_root):
        """Create a SpecGenerator instance."""
        return SpecGenerator(project_root)
    
    def test_generate_cli_config(self, generator):
        """Test generating spec for CLI_CONFIG."""
        result = generator.generate(CLI_CONFIG)
        assert isinstance(result, str)
        assert "ContractAnalysisCLI" in result
        assert "console=True" in result
        assert "pdfminer" in result
    
    def test_generate_gui_config(self, generator):
        """Test generating spec for GUI_CONFIG."""
        result = generator.generate(GUI_CONFIG)
        assert isinstance(result, str)
        assert "CR2A" in result
        assert "console=False" in result
        # transformers and torch removed in OpenAI-only version
        assert "tokenizers" in result  # Still needed for OpenAI
        assert "icon.ico" in result
    
    def test_cli_config_includes_required_imports(self, generator):
        """Test that CLI spec includes all required document processing imports."""
        result = generator.generate(CLI_CONFIG)
        required_imports = ["pdfminer", "pdfminer.high_level", "docx", "openai", "jsonschema"]
        for imp in required_imports:
            assert f"'{imp}'" in result, f"Missing required import: {imp}"
    
    def test_gui_config_includes_ml_imports(self, generator):
        """Test that GUI spec includes required package imports."""
        result = generator.generate(GUI_CONFIG)
        # transformers and torch removed in OpenAI-only version
        required_imports = ["tokenizers", "cryptography"]  # Still needed for OpenAI
        for imp in required_imports:
            assert f"'{imp}'" in result, f"Missing required import: {imp}"
    
    def test_configs_exclude_test_packages(self, generator):
        """Test that both configs exclude test and dev packages."""
        cli_result = generator.generate(CLI_CONFIG)
        gui_result = generator.generate(GUI_CONFIG)
        
        for result in [cli_result, gui_result]:
            assert "'pytest'" in result
            assert "'hypothesis'" in result
            assert "'IPython'" in result
            assert "'jupyter'" in result
