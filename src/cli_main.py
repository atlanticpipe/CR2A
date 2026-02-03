"""
CR2A CLI - Command Line Interface for Contract Analysis

A tkinter-free version that works via command line.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from contract_uploader import ContractUploader
from openai_fallback_client import OpenAIClient
from analysis_engine import AnalysisEngine
from query_engine import QueryEngine


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class CR2A_CLI:
    """Command-line interface for CR2A."""
    
    def __init__(self):
        """Initialize CLI."""
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            print("\n❌ ERROR: OPENAI_API_KEY environment variable not set")
            print("Please set it with: set OPENAI_API_KEY=sk-your-key-here")
            sys.exit(1)
        
        self.analysis_engine = None
        self.query_engine = None
        self.current_analysis = None
        self.current_file = None
        
    def analyze_contract(self, file_path: str) -> bool:
        """
        Analyze a contract file.
        
        Args:
            file_path: Path to contract file (PDF, DOCX, or TXT)
            
        Returns:
            True if analysis succeeded, False otherwise
        """
        print(f"\n📄 Analyzing contract: {file_path}")
        print("=" * 60)
        
        try:
            # Initialize analysis engine if needed
            if not self.analysis_engine:
                print("🔧 Initializing analysis engine...")
                self.analysis_engine = AnalysisEngine(openai_api_key=self.api_key)
            
            # Analyze the contract
            print("🤖 Sending to OpenAI for analysis...")
            print("⏳ This may take 30-60 seconds...")
            
            self.current_analysis = self.analysis_engine.analyze_contract(file_path)
            self.current_file = file_path
            
            print("\n✅ Analysis complete!")
            print("=" * 60)
            
            # Display summary
            self._display_summary()
            
            return True
            
        except Exception as e:
            print(f"\n❌ Analysis failed: {str(e)}")
            logger.error("Analysis error", exc_info=True)
            return False
    
    def _display_summary(self):
        """Display analysis summary."""
        if not self.current_analysis:
            return
        
        result = self.current_analysis
        
        print("\n📊 ANALYSIS SUMMARY")
        print("-" * 60)
        
        # Parties
        if result.parties:
            print("\n👥 PARTIES:")
            for key, value in result.parties.items():
                print(f"  • {key}: {value}")
        
        # Key terms
        if result.key_terms:
            print("\n📋 KEY TERMS:")
            for term in result.key_terms[:5]:  # Show first 5
                print(f"  • {term}")
            if len(result.key_terms) > 5:
                print(f"  ... and {len(result.key_terms) - 5} more")
        
        # Financial terms
        if result.financial_terms:
            print("\n💰 FINANCIAL TERMS:")
            for key, value in result.financial_terms.items():
                print(f"  • {key}: {value}")
        
        # Important dates
        if result.important_dates:
            print("\n📅 IMPORTANT DATES:")
            for key, value in result.important_dates.items():
                print(f"  • {key}: {value}")
        
        # Risks
        if result.identified_risks:
            print("\n⚠️  IDENTIFIED RISKS:")
            for risk in result.identified_risks[:3]:  # Show first 3
                severity = risk.get('severity', 'unknown')
                description = risk.get('description', 'No description')
                print(f"  • [{severity.upper()}] {description}")
            if len(result.identified_risks) > 3:
                print(f"  ... and {len(result.identified_risks) - 3} more")
        
        print("\n" + "=" * 60)
    
    def save_analysis(self, output_path: Optional[str] = None):
        """Save analysis to JSON file."""
        if not self.current_analysis:
            print("❌ No analysis to save")
            return
        
        if not output_path:
            # Generate output path from input file
            input_path = Path(self.current_file)
            output_path = input_path.parent / f"{input_path.stem}_analysis.json"
        
        try:
            # Convert to dict
            analysis_dict = {
                'parties': self.current_analysis.parties,
                'key_terms': self.current_analysis.key_terms,
                'financial_terms': self.current_analysis.financial_terms,
                'important_dates': self.current_analysis.important_dates,
                'identified_risks': self.current_analysis.identified_risks,
                'obligations': self.current_analysis.obligations,
                'clauses': self.current_analysis.clauses,
                'metadata': self.current_analysis.metadata
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_dict, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Analysis saved to: {output_path}")
            
        except Exception as e:
            print(f"❌ Failed to save analysis: {str(e)}")
    
    def load_analysis(self, json_path: str) -> bool:
        """Load analysis from JSON file."""
        try:
            print(f"\n📂 Loading analysis from: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create a mock analysis result
            from analysis_models import AnalysisResult
            self.current_analysis = AnalysisResult(
                parties=data.get('parties', {}),
                key_terms=data.get('key_terms', []),
                financial_terms=data.get('financial_terms', {}),
                important_dates=data.get('important_dates', {}),
                identified_risks=data.get('identified_risks', []),
                obligations=data.get('obligations', []),
                clauses=data.get('clauses', []),
                metadata=data.get('metadata', {})
            )
            
            self.current_file = json_path
            
            print("✅ Analysis loaded successfully")
            self._display_summary()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load analysis: {str(e)}")
            return False
    
    def query_contract(self, question: str) -> str:
        """
        Ask a question about the analyzed contract.
        
        Args:
            question: Question to ask
            
        Returns:
            Answer string
        """
        if not self.current_analysis:
            return "❌ No contract analyzed yet. Please analyze a contract first."
        
        try:
            # Initialize query engine if needed
            if not self.query_engine:
                openai_client = OpenAIClient(api_key=self.api_key)
                self.query_engine = QueryEngine(openai_client)
            
            # Convert analysis to dict for query engine
            analysis_dict = {
                'parties': self.current_analysis.parties,
                'key_terms': self.current_analysis.key_terms,
                'financial_terms': self.current_analysis.financial_terms,
                'important_dates': self.current_analysis.important_dates,
                'identified_risks': self.current_analysis.identified_risks,
                'obligations': self.current_analysis.obligations,
                'clauses': self.current_analysis.clauses,
            }
            
            # Process query
            print("\n🤔 Thinking...")
            response = self.query_engine.process_query(question, analysis_dict)
            
            return response
            
        except Exception as e:
            return f"❌ Query failed: {str(e)}"
    
    def interactive_mode(self):
        """Start interactive Q&A mode."""
        if not self.current_analysis:
            print("❌ No contract analyzed yet. Please analyze a contract first.")
            return
        
        print("\n💬 INTERACTIVE Q&A MODE")
        print("=" * 60)
        print("Ask questions about the contract (type 'exit' to quit)")
        print("=" * 60)
        
        while True:
            try:
                question = input("\n❓ Your question: ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if question.lower() in ['help', '?']:
                    self._show_help()
                    continue
                
                if question.lower() == 'summary':
                    self._display_summary()
                    continue
                
                # Process the question
                answer = self.query_contract(question)
                print(f"\n💡 Answer:\n{answer}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    def _show_help(self):
        """Show help message."""
        print("\n📖 HELP")
        print("-" * 60)
        print("Commands:")
        print("  • Type any question about the contract")
        print("  • 'summary' - Show analysis summary")
        print("  • 'help' or '?' - Show this help")
        print("  • 'exit' or 'quit' - Exit interactive mode")
        print("\nExample questions:")
        print("  • Who are the parties?")
        print("  • What is the contract value?")
        print("  • When does it expire?")
        print("  • What are the risks?")
        print("  • What are the payment terms?")


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  CR2A - Contract Review & Analysis (CLI)")
    print("=" * 60)
    
    # Check for command line arguments
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python src/cli_main.py <contract_file>")
        print("  python src/cli_main.py <analysis.json>")
        print("\nExamples:")
        print("  python src/cli_main.py test_contract.txt")
        print("  python src/cli_main.py contract.pdf")
        print("  python src/cli_main.py contract_analysis.json")
        print("\nSupported formats: PDF, DOCX, TXT, JSON")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"\n❌ File not found: {file_path}")
        sys.exit(1)
    
    # Initialize CLI
    cli = CR2A_CLI()
    
    # Check if it's a JSON file (pre-analyzed)
    if file_path.lower().endswith('.json'):
        if cli.load_analysis(file_path):
            cli.interactive_mode()
    else:
        # Analyze the contract
        if cli.analyze_contract(file_path):
            # Save analysis
            cli.save_analysis()
            # Start interactive mode
            cli.interactive_mode()


if __name__ == '__main__':
    main()
