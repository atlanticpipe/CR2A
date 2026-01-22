"""Pattern detection for security and configuration issues."""

import re
from typing import Dict, List, Optional, Pattern, Tuple
from .models import Finding, IssueType, Severity
from .file_scanner import FileScanner


class PatternDetector:
    """Detects security and configuration issues using regex patterns.
    
    This class scans file content for various issue types including:
    - Hardcoded file paths (absolute and relative)
    - Secrets (API keys, tokens, passwords, private keys)
    - Configuration variables (URLs, connection strings, feature flags)
    - API calls (HTTP requests, SDK instantiations)
    """
    
    def __init__(self, custom_patterns: Optional[Dict[str, List[str]]] = None):
        """Initialize PatternDetector with detection patterns.
        
        Args:
            custom_patterns: Optional dictionary of custom patterns by category
        """
        self.patterns = self._build_patterns()
        
        # Add custom patterns if provided
        if custom_patterns:
            for category, pattern_list in custom_patterns.items():
                if category in self.patterns:
                    self.patterns[category].extend([re.compile(p) for p in pattern_list])
                else:
                    self.patterns[category] = [re.compile(p) for p in pattern_list]
    
    def _build_patterns(self) -> Dict[str, List[Pattern]]:
        """Build the default pattern dictionary for all issue types.
        
        Returns:
            Dictionary mapping issue categories to compiled regex patterns
        """
        patterns = {
            'hardcoded_path': [
                # Unix absolute paths (starting with /)
                re.compile(r'["\'](/[^"\']+)["\']'),
                # Windows absolute paths (drive letter: C:\, D:\, etc.)
                re.compile(r'["\']([A-Z]:\\[^"\']+)["\']'),
                # Problematic relative paths (multiple parent directory references)
                re.compile(r'\.\.\/(?:\.\.\/){2,}'),
            ],
            'secret': [
                # API keys and secrets
                re.compile(r'(?:api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
                # Passwords
                re.compile(r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
                # Tokens and auth tokens
                re.compile(r'(?:token|auth[_-]?token|access[_-]?token|bearer[_-]?token)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
                # Private keys (BEGIN PRIVATE KEY, BEGIN RSA PRIVATE KEY, etc.)
                re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'),
                # Certificates
                re.compile(r'-----BEGIN\s+CERTIFICATE-----'),
                # Connection strings with passwords
                re.compile(r'(?:mongodb|mysql|postgresql|postgres)://[^:]+:[^@]+@', re.IGNORECASE),
                # AWS access keys (pattern: AKIA followed by 16 alphanumeric chars)
                re.compile(r'AKIA[0-9A-Z]{16}'),
                # Generic secret patterns (secret=, secret:)
                re.compile(r'(?:secret|credential)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
            ],
            'config': [
                # URLs and endpoints (http/https)
                re.compile(r'https?://[^\s"\']+'),
                # Database connection parameters (host, hostname, server)
                re.compile(r'(?:host|hostname|server|db_host|database_host)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
                # Database names
                re.compile(r'(?:database|db_name|dbname)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
                # Port numbers
                re.compile(r'(?:port|db_port|database_port)\s*[:=]\s*["\']?\d+["\']?', re.IGNORECASE),
                # Feature flags
                re.compile(r'(?:feature[_-]?flag|enable[_-]?feature|flag)\s*[:=]\s*(?:true|false|["\'](?:true|false|enabled|disabled)["\'])', re.IGNORECASE),
                # Environment/stage configuration
                re.compile(r'(?:environment|env|stage)\s*[:=]\s*["\'](?:dev|development|prod|production|staging|test)["\']', re.IGNORECASE),
            ],
            'api_call': [
                # JavaScript/TypeScript fetch API
                re.compile(r'\bfetch\s*\('),
                # Axios library
                re.compile(r'\baxios\s*\.(?:get|post|put|delete|patch|request)\s*\('),
                re.compile(r'\baxios\s*\('),
                # Python requests library
                re.compile(r'\brequests\s*\.(?:get|post|put|delete|patch|request)\s*\('),
                # jQuery AJAX
                re.compile(r'\$\s*\.(?:ajax|get|post)\s*\('),
                # XMLHttpRequest
                re.compile(r'\bnew\s+XMLHttpRequest\s*\('),
                # HTTP client instantiations
                re.compile(r'\bnew\s+(?:HttpClient|RestClient|ApiClient)\s*\('),
            ]
        }
        
        return patterns
    
    def detect(self, content: str, file_path: str) -> List[Finding]:
        """Detect issues in file content.
        
        Args:
            content: The file content to analyze
            file_path: Path to the file being analyzed (relative to project root)
            
        Returns:
            List of Finding objects for detected issues
        """
        if content is None:
            return []
        
        findings = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            # Check each pattern category
            for category, pattern_list in self.patterns.items():
                for pattern in pattern_list:
                    match = self.match_pattern(line, pattern)
                    if match:
                        finding = self._create_finding(
                            file_path=file_path,
                            line_number=line_num,
                            line_content=line,
                            match=match,
                            category=category,
                            pattern=pattern
                        )
                        findings.append(finding)
        
        return findings
    
    def detect_in_files(self, file_scanner: FileScanner, file_paths: List[str]) -> List[Finding]:
        """Detect issues across multiple files with error handling.
        
        Args:
            file_scanner: FileScanner instance to use for reading files
            file_paths: List of file paths to analyze (relative to scanner root)
            
        Returns:
            List of Finding objects for all detected issues
        """
        all_findings = []
        
        for file_path in file_paths:
            content = file_scanner.read_file(file_path)
            if content is not None:
                findings = self.detect(content, file_path)
                all_findings.extend(findings)
        
        return all_findings
    
    def match_pattern(self, line: str, pattern: Pattern) -> Optional[re.Match]:
        """Check if line matches a specific pattern.
        
        Args:
            line: The line of code to check
            pattern: Compiled regex pattern to match against
            
        Returns:
            Match object if pattern matches, None otherwise
        """
        return pattern.search(line)
    
    def _create_finding(
        self,
        file_path: str,
        line_number: int,
        line_content: str,
        match: re.Match,
        category: str,
        pattern: Pattern
    ) -> Finding:
        """Create a Finding object from a pattern match.
        
        Args:
            file_path: Path to the file
            line_number: Line number where issue was found
            line_content: The full line content
            match: The regex match object
            category: Issue category (hardcoded_path, secret, config, api_call)
            pattern: The pattern that matched
            
        Returns:
            Finding object with all required fields
        """
        # Map category to IssueType
        issue_type_map = {
            'hardcoded_path': IssueType.HARDCODED_PATH,
            'secret': IssueType.SECRET,
            'config': IssueType.CONFIG_VARIABLE,
            'api_call': IssueType.API_CALL
        }
        
        issue_type = issue_type_map.get(category, IssueType.CONFIG_VARIABLE)
        severity = self._calculate_severity(issue_type)
        recommendation = self._get_recommendation(issue_type)
        
        return Finding(
            file_path=file_path,
            line_number=line_number,
            column=match.start(),
            issue_type=issue_type,
            severity=severity,
            code_snippet=line_content.strip(),
            matched_pattern=match.group(0),
            recommendation=recommendation
        )
    
    def _calculate_severity(self, issue_type: IssueType) -> Severity:
        """Calculate severity level based on issue type.
        
        Args:
            issue_type: The type of issue detected
            
        Returns:
            Severity level (CRITICAL, HIGH, MEDIUM, LOW)
        """
        severity_map = {
            IssueType.SECRET: Severity.CRITICAL,
            IssueType.HARDCODED_PATH: Severity.MEDIUM,
            IssueType.CONFIG_VARIABLE: Severity.MEDIUM,
            IssueType.API_CALL: Severity.LOW
        }
        return severity_map.get(issue_type, Severity.LOW)
    
    def _get_recommendation(self, issue_type: IssueType) -> str:
        """Get remediation recommendation based on issue type.
        
        Args:
            issue_type: The type of issue detected
            
        Returns:
            Recommendation string for fixing the issue
        """
        recommendations = {
            IssueType.SECRET: "Move secret to environment variable or secure vault",
            IssueType.HARDCODED_PATH: "Use relative paths or environment variables for file paths",
            IssueType.CONFIG_VARIABLE: "Externalize configuration to environment variables or config files",
            IssueType.API_CALL: "Document external dependency and consider configuration"
        }
        return recommendations.get(issue_type, "Review and externalize if necessary")
