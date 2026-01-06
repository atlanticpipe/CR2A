"""
Comprehensive error logging system for CR2A testing framework.
Captures and analyzes CloudWatch logs across all components with error pattern detection.
"""

import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import boto3
from botocore.exceptions import ClientError

from .base import BaseTestFramework
from .models import TestConfiguration, TestResult, TestStatus


class ErrorCategory(Enum):
    """Categories for error classification."""
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ErrorPattern:
    """Pattern definition for error detection."""
    category: ErrorCategory
    pattern: str
    description: str
    severity: str
    suggested_fix: str


@dataclass
class LogEntry:
    """Structured log entry with metadata."""
    timestamp: datetime
    log_group: str
    log_stream: str
    message: str
    level: str
    component: str
    raw_event: Dict[str, Any]


@dataclass
class ErrorAnalysis:
    """Analysis result for detected errors."""
    category: ErrorCategory
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    affected_components: Set[str]
    sample_messages: List[str]
    pattern_matches: List[str]
    suggested_fixes: List[str]


class ErrorLoggingSystem(BaseTestFramework):
    """Comprehensive error logging and analysis system."""
    
    def __init__(self, config: TestConfiguration):
        super().__init__(config)
        self.cloudwatch_client = self.get_aws_client('logs')
        self.error_patterns = self._initialize_error_patterns()
        self.log_groups = []  # Initialize empty, will be populated on first use
    
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize error detection patterns."""
        return [
            # Dependency errors
            ErrorPattern(
                ErrorCategory.DEPENDENCY_ERROR,
                r"ModuleNotFoundError|ImportError|No module named",
                "Missing Python package or import error",
                "HIGH",
                "Update Lambda layer with missing dependencies"
            ),
            ErrorPattern(
                ErrorCategory.DEPENDENCY_ERROR,
                r"Unable to import module|cannot import name",
                "Module import failure",
                "HIGH",
                "Check package installation and Python path"
            ),
            
            # Configuration errors
            ErrorPattern(
                ErrorCategory.CONFIGURATION_ERROR,
                r"KeyError.*OPENAI_API_KEY|Missing.*API.*key",
                "Missing OpenAI API key configuration",
                "CRITICAL",
                "Set OPENAI_API_KEY environment variable or AWS secret"
            ),
            ErrorPattern(
                ErrorCategory.CONFIGURATION_ERROR,
                r"Environment variable.*not set|Missing required environment variable",
                "Missing environment variable",
                "HIGH",
                "Configure required environment variables"
            ),
            
            # Permission errors
            ErrorPattern(
                ErrorCategory.PERMISSION_ERROR,
                r"AccessDenied|Forbidden|UnauthorizedOperation",
                "AWS permission denied",
                "CRITICAL",
                "Update IAM policies with required permissions"
            ),
            ErrorPattern(
                ErrorCategory.PERMISSION_ERROR,
                r"User.*is not authorized to perform",
                "IAM authorization failure",
                "CRITICAL",
                "Grant required IAM permissions to execution role"
            ),
            
            # Network errors
            ErrorPattern(
                ErrorCategory.NETWORK_ERROR,
                r"ConnectionError|TimeoutError|ConnectTimeout",
                "Network connectivity issue",
                "MEDIUM",
                "Check network configuration and retry logic"
            ),
            ErrorPattern(
                ErrorCategory.NETWORK_ERROR,
                r"Unable to locate credentials|NoCredentialsError",
                "AWS credentials not found",
                "CRITICAL",
                "Configure AWS credentials or IAM role"
            ),
            
            # Timeout errors
            ErrorPattern(
                ErrorCategory.TIMEOUT_ERROR,
                r"Task timed out|Lambda timeout|ReadTimeoutError",
                "Operation timeout",
                "MEDIUM",
                "Increase timeout settings or optimize performance"
            ),
            
            # Validation errors
            ErrorPattern(
                ErrorCategory.VALIDATION_ERROR,
                r"ValidationException|Invalid.*format|Schema validation failed",
                "Data validation failure",
                "MEDIUM",
                "Check input data format and schema compliance"
            ),
            
            # DynamoDB specific errors
            ErrorPattern(
                ErrorCategory.CONFIGURATION_ERROR,
                r"ResourceNotFoundException.*Table",
                "DynamoDB table not found",
                "CRITICAL",
                "Create missing DynamoDB table or check table name"
            ),
            ErrorPattern(
                ErrorCategory.VALIDATION_ERROR,
                r"ValidationException.*reserved keyword",
                "DynamoDB reserved keyword conflict",
                "HIGH",
                "Use expression attribute names for reserved keywords"
            ),
            
            # Step Functions errors
            ErrorPattern(
                ErrorCategory.CONFIGURATION_ERROR,
                r"StateMachineDoesNotExist|InvalidArn",
                "Step Functions state machine not found",
                "CRITICAL",
                "Deploy state machine or check ARN configuration"
            ),
            
            # API Gateway errors
            ErrorPattern(
                ErrorCategory.CONFIGURATION_ERROR,
                r"NotFoundException.*API|RestApi.*not found",
                "API Gateway not found",
                "CRITICAL",
                "Deploy API Gateway or check API ID configuration"
            ),
            
            # OpenAI specific errors
            ErrorPattern(
                ErrorCategory.NETWORK_ERROR,
                r"OpenAI.*rate limit|RateLimitError",
                "OpenAI API rate limit exceeded",
                "MEDIUM",
                "Implement exponential backoff and retry logic"
            ),
            ErrorPattern(
                ErrorCategory.VALIDATION_ERROR,
                r"OpenAI.*invalid.*model|model.*not found",
                "Invalid OpenAI model specified",
                "HIGH",
                "Use supported OpenAI model name"
            ),
        ]
    
    def _get_cr2a_log_groups(self) -> List[str]:
        """Get all CR2A-related CloudWatch log groups."""
        log_groups = []
        
        try:
            paginator = self.cloudwatch_client.get_paginator('describe_log_groups')
            
            for page in paginator.paginate():
                for group in page['logGroups']:
                    group_name = group['logGroupName']
                    # Include CR2A-related log groups
                    if any(pattern in group_name.lower() for pattern in [
                        'cr2a', '/aws/lambda/cr2a', '/aws/apigateway/cr2a',
                        '/aws/stepfunctions/cr2a'
                    ]):
                        log_groups.append(group_name)
            
            self.logger.info(f"Found {len(log_groups)} CR2A log groups")
            return log_groups
            
        except ClientError as e:
            self.logger.error(f"Failed to list log groups: {e}")
            return []
    
    def capture_logs(self, 
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    log_groups: Optional[List[str]] = None) -> List[LogEntry]:
        """Capture logs from CloudWatch for analysis."""
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        
        # Get log groups if not provided and not already cached
        if log_groups is None:
            if not self.log_groups:
                self.log_groups = self._get_cr2a_log_groups()
            log_groups_to_query = self.log_groups
        else:
            log_groups_to_query = log_groups
        
        all_entries = []
        
        for log_group in log_groups_to_query:
            try:
                entries = self._fetch_log_entries(log_group, start_time, end_time)
                all_entries.extend(entries)
                self.logger.debug(f"Captured {len(entries)} entries from {log_group}")
                
            except ClientError as e:
                self.logger.warning(f"Failed to fetch logs from {log_group}: {e}")
                continue
        
        self.logger.info(f"Captured total of {len(all_entries)} log entries")
        return sorted(all_entries, key=lambda x: x.timestamp)
    
    def _fetch_log_entries(self, 
                          log_group: str, 
                          start_time: datetime, 
                          end_time: datetime) -> List[LogEntry]:
        """Fetch log entries from a specific log group."""
        entries = []
        
        try:
            # Convert to milliseconds for CloudWatch API
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            paginator = self.cloudwatch_client.get_paginator('filter_log_events')
            
            for page in paginator.paginate(
                logGroupName=log_group,
                startTime=start_ms,
                endTime=end_ms
            ):
                for event in page['events']:
                    entry = self._parse_log_event(event, log_group)
                    if entry:
                        entries.append(entry)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.logger.warning(f"Log group {log_group} not found")
            else:
                raise
        
        return entries
    
    def _parse_log_event(self, event: Dict[str, Any], log_group: str) -> Optional[LogEntry]:
        """Parse a CloudWatch log event into structured format."""
        try:
            timestamp = datetime.fromtimestamp(
                event['timestamp'] / 1000, 
                tz=timezone.utc
            )
            
            message = event['message'].strip()
            log_stream = event.get('logStreamName', 'unknown')
            
            # Extract log level and component from message
            level, component = self._extract_log_metadata(message, log_group)
            
            return LogEntry(
                timestamp=timestamp,
                log_group=log_group,
                log_stream=log_stream,
                message=message,
                level=level,
                component=component,
                raw_event=event
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse log event: {e}")
            return None
    
    def _extract_log_metadata(self, message: str, log_group: str) -> Tuple[str, str]:
        """Extract log level and component from log message."""
        # Extract log level
        level_patterns = {
            'ERROR': r'\b(ERROR|FATAL|CRITICAL)\b',
            'WARN': r'\b(WARN|WARNING)\b',
            'INFO': r'\bINFO\b',
            'DEBUG': r'\bDEBUG\b'
        }
        
        level = 'UNKNOWN'
        for level_name, pattern in level_patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                level = level_name
                break
        
        # Extract component from log group or message
        component = 'unknown'
        if '/aws/lambda/' in log_group:
            component = log_group.split('/')[-1]  # Lambda function name
        elif '/aws/apigateway/' in log_group:
            component = 'api-gateway'
        elif '/aws/stepfunctions/' in log_group:
            component = 'step-functions'
        
        return level, component
    
    def analyze_errors(self, log_entries: List[LogEntry]) -> Dict[ErrorCategory, ErrorAnalysis]:
        """Analyze log entries for error patterns and categorize them."""
        error_analyses = {}
        
        # Initialize analysis for each category
        for category in ErrorCategory:
            error_analyses[category] = ErrorAnalysis(
                category=category,
                count=0,
                first_occurrence=None,
                last_occurrence=None,
                affected_components=set(),
                sample_messages=[],
                pattern_matches=[],
                suggested_fixes=[]
            )
        
        # Analyze each log entry
        for entry in log_entries:
            # Only analyze error-level entries
            if entry.level not in ['ERROR', 'FATAL', 'CRITICAL']:
                continue
            
            # Check against all error patterns
            for pattern in self.error_patterns:
                if re.search(pattern.pattern, entry.message, re.IGNORECASE):
                    analysis = error_analyses[pattern.category]
                    
                    analysis.count += 1
                    analysis.affected_components.add(entry.component)
                    analysis.pattern_matches.append(pattern.pattern)
                    
                    if analysis.first_occurrence is None or entry.timestamp < analysis.first_occurrence:
                        analysis.first_occurrence = entry.timestamp
                    
                    if analysis.last_occurrence is None or entry.timestamp > analysis.last_occurrence:
                        analysis.last_occurrence = entry.timestamp
                    
                    # Keep sample messages (limit to 5 per category)
                    if len(analysis.sample_messages) < 5:
                        analysis.sample_messages.append(entry.message[:200])
                    
                    # Add suggested fix if not already present
                    if pattern.suggested_fix not in analysis.suggested_fixes:
                        analysis.suggested_fixes.append(pattern.suggested_fix)
                    
                    break  # Only match first pattern per entry
        
        # Filter out categories with no errors
        return {k: v for k, v in error_analyses.items() if v.count > 0}
    
    def generate_error_report(self, 
                            analyses: Dict[ErrorCategory, ErrorAnalysis],
                            output_format: str = 'json') -> str:
        """Generate comprehensive error analysis report."""
        if output_format == 'json':
            return self._generate_json_report(analyses)
        elif output_format == 'html':
            return self._generate_html_report(analyses)
        else:
            return self._generate_text_report(analyses)
    
    def _generate_json_report(self, analyses: Dict[ErrorCategory, ErrorAnalysis]) -> str:
        """Generate JSON format error report."""
        report_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_error_categories': len(analyses),
            'total_errors': sum(analysis.count for analysis in analyses.values()),
            'categories': {}
        }
        
        for category, analysis in analyses.items():
            report_data['categories'][category.value] = {
                'count': analysis.count,
                'first_occurrence': analysis.first_occurrence.isoformat() if analysis.first_occurrence else None,
                'last_occurrence': analysis.last_occurrence.isoformat() if analysis.last_occurrence else None,
                'affected_components': list(analysis.affected_components),
                'sample_messages': analysis.sample_messages,
                'suggested_fixes': analysis.suggested_fixes
            }
        
        return json.dumps(report_data, indent=2)
    
    def _generate_text_report(self, analyses: Dict[ErrorCategory, ErrorAnalysis]) -> str:
        """Generate human-readable text report."""
        lines = [
            "CR2A Error Analysis Report",
            "=" * 50,
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total Error Categories: {len(analyses)}",
            f"Total Errors: {sum(analysis.count for analysis in analyses.values())}",
            ""
        ]
        
        for category, analysis in sorted(analyses.items(), key=lambda x: x[1].count, reverse=True):
            lines.extend([
                f"{category.value}:",
                f"  Count: {analysis.count}",
                f"  Affected Components: {', '.join(analysis.affected_components)}",
                f"  First Occurrence: {analysis.first_occurrence.strftime('%Y-%m-%d %H:%M:%S') if analysis.first_occurrence else 'N/A'}",
                f"  Last Occurrence: {analysis.last_occurrence.strftime('%Y-%m-%d %H:%M:%S') if analysis.last_occurrence else 'N/A'}",
                "  Suggested Fixes:",
            ])
            
            for fix in analysis.suggested_fixes:
                lines.append(f"    - {fix}")
            
            if analysis.sample_messages:
                lines.append("  Sample Messages:")
                for msg in analysis.sample_messages[:3]:  # Show top 3
                    lines.append(f"    - {msg}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def test_error_logging_system(self) -> TestResult:
        """Test the error logging system functionality."""
        try:
            # Test log group discovery
            log_groups = self._get_cr2a_log_groups()
            if not log_groups:
                return TestResult(
                    test_name="error_logging_system",
                    status=TestStatus.FAIL,
                    message="No CR2A log groups found"
                )
            
            # Test log capture (last 10 minutes)
            start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            log_entries = self.capture_logs(start_time=start_time)
            
            # Test error analysis
            error_analyses = self.analyze_errors(log_entries)
            
            # Test report generation
            report = self.generate_error_report(error_analyses)
            
            return TestResult(
                test_name="error_logging_system",
                status=TestStatus.PASS,
                message=f"Error logging system functional. Found {len(log_groups)} log groups, "
                       f"captured {len(log_entries)} entries, identified {len(error_analyses)} error categories",
                details={
                    'log_groups_count': len(log_groups),
                    'log_entries_count': len(log_entries),
                    'error_categories_count': len(error_analyses),
                    'report_length': len(report)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name="error_logging_system",
                status=TestStatus.ERROR,
                message=f"Error logging system test failed: {str(e)}",
                details={'exception': str(e)}
            )