"""
Result Parser Module

Handles parsing and validation of OpenAI API responses into AnalysisResult objects.
Provides robust handling of partial or malformed responses.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.analysis_models import (
    AnalysisResult,
    ContractMetadata,
    Clause,
    Risk,
    ComplianceIssue,
    RedliningSuggestion
)


logger = logging.getLogger(__name__)


class ResultParser:
    """
    Parses OpenAI API JSON responses into AnalysisResult objects.
    
    This class handles:
    - Parsing structured JSON responses
    - Validating required fields
    - Handling partial or malformed responses
    - Providing default values for missing fields
    """
    
    def __init__(self):
        """Initialize the result parser."""
        logger.debug("ResultParser initialized")
    
    def parse_api_response(
        self,
        api_response: Dict[str, Any],
        filename: str,
        file_size_bytes: int,
        page_count: Optional[int] = None
    ) -> AnalysisResult:
        """
        Parse OpenAI API JSON response into AnalysisResult.
        
        Args:
            api_response: JSON response from OpenAI API
            filename: Name of the analyzed contract file
            file_size_bytes: Size of the file in bytes
            page_count: Number of pages (optional)
        
        Returns:
            AnalysisResult object
        
        Raises:
            ValueError: If response is invalid or missing critical fields
        """
        logger.info("Parsing API response for file: %s", filename)
        
        try:
            # Create metadata
            metadata = self._parse_metadata(
                api_response,
                filename,
                file_size_bytes,
                page_count
            )
            
            # Parse clauses
            clauses = self._parse_clauses(api_response)
            logger.debug("Parsed %d clauses", len(clauses))
            
            # Parse risks
            risks = self._parse_risks(api_response)
            logger.debug("Parsed %d risks", len(risks))
            
            # Parse compliance issues
            compliance_issues = self._parse_compliance_issues(api_response)
            logger.debug("Parsed %d compliance issues", len(compliance_issues))
            
            # Parse redlining suggestions
            redlining_suggestions = self._parse_redlining_suggestions(api_response)
            logger.debug("Parsed %d redlining suggestions", len(redlining_suggestions))
            
            # Create analysis result
            result = AnalysisResult(
                metadata=metadata,
                clauses=clauses,
                risks=risks,
                compliance_issues=compliance_issues,
                redlining_suggestions=redlining_suggestions
            )
            
            # Validate the result
            if not result.validate_result():
                logger.warning("Analysis result validation failed, but continuing with partial result")
            
            logger.info("Successfully parsed analysis result")
            return result
            
        except Exception as e:
            logger.error("Failed to parse API response: %s", e, exc_info=True)
            raise ValueError(f"Failed to parse analysis result: {str(e)}") from e
    
    def _parse_metadata(
        self,
        api_response: Dict[str, Any],
        filename: str,
        file_size_bytes: int,
        page_count: Optional[int]
    ) -> ContractMetadata:
        """
        Parse contract metadata from API response.
        
        Args:
            api_response: API response dictionary
            filename: Contract filename
            file_size_bytes: File size in bytes
            page_count: Number of pages (optional)
        
        Returns:
            ContractMetadata object
        """
        # Try to get page count from API response if not provided
        if page_count is None:
            metadata_dict = api_response.get('contract_metadata', {})
            page_count = metadata_dict.get('page_count', 0)
        
        # Ensure page_count is at least 1 if we have a file
        if page_count == 0 and file_size_bytes > 0:
            page_count = 1
        
        return ContractMetadata(
            filename=filename,
            analyzed_at=datetime.now(),
            page_count=page_count,
            file_size_bytes=file_size_bytes
        )
    
    def _parse_clauses(self, api_response: Dict[str, Any]) -> List[Clause]:
        """
        Parse clauses from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of Clause objects
        """
        clauses = []
        clauses_data = api_response.get('clauses', [])
        
        if not isinstance(clauses_data, list):
            logger.warning("Clauses field is not a list, skipping")
            return clauses
        
        for idx, clause_data in enumerate(clauses_data):
            try:
                clause = self._parse_single_clause(clause_data, idx)
                if clause:
                    clauses.append(clause)
            except Exception as e:
                logger.warning("Failed to parse clause %d: %s", idx, e)
                continue
        
        return clauses
    
    def _parse_single_clause(
        self,
        clause_data: Dict[str, Any],
        index: int
    ) -> Optional[Clause]:
        """
        Parse a single clause from data.
        
        Args:
            clause_data: Clause data dictionary
            index: Index of the clause (for generating default ID)
        
        Returns:
            Clause object or None if parsing fails
        """
        if not isinstance(clause_data, dict):
            return None
        
        # Extract fields with defaults
        clause_id = clause_data.get('id', f'clause_{index + 1}')
        clause_type = clause_data.get('type', 'unknown')
        text = clause_data.get('text', '')
        page = clause_data.get('page', 0)
        risk_level = clause_data.get('risk_level', 'low')
        
        # Validate risk level
        if risk_level not in ['low', 'medium', 'high']:
            logger.warning("Invalid risk level '%s' for clause %s, defaulting to 'low'", 
                         risk_level, clause_id)
            risk_level = 'low'
        
        # Skip clauses with no text
        if not text:
            logger.warning("Skipping clause %s with empty text", clause_id)
            return None
        
        return Clause(
            id=clause_id,
            type=clause_type,
            text=text,
            page=page,
            risk_level=risk_level
        )
    
    def _parse_risks(self, api_response: Dict[str, Any]) -> List[Risk]:
        """
        Parse risks from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of Risk objects
        """
        risks = []
        risks_data = api_response.get('risks', [])
        
        if not isinstance(risks_data, list):
            logger.warning("Risks field is not a list, skipping")
            return risks
        
        for idx, risk_data in enumerate(risks_data):
            try:
                risk = self._parse_single_risk(risk_data, idx)
                if risk:
                    risks.append(risk)
            except Exception as e:
                logger.warning("Failed to parse risk %d: %s", idx, e)
                continue
        
        return risks
    
    def _parse_single_risk(
        self,
        risk_data: Dict[str, Any],
        index: int
    ) -> Optional[Risk]:
        """
        Parse a single risk from data.
        
        Args:
            risk_data: Risk data dictionary
            index: Index of the risk (for generating default ID)
        
        Returns:
            Risk object or None if parsing fails
        """
        if not isinstance(risk_data, dict):
            return None
        
        # Extract fields with defaults
        risk_id = risk_data.get('id', f'risk_{index + 1}')
        clause_id = risk_data.get('clause_id', '')
        severity = risk_data.get('severity', 'low')
        description = risk_data.get('description', '')
        recommendation = risk_data.get('recommendation', '')
        
        # Validate severity
        if severity not in ['low', 'medium', 'high', 'critical']:
            logger.warning("Invalid severity '%s' for risk %s, defaulting to 'low'", 
                         severity, risk_id)
            severity = 'low'
        
        # Skip risks with no description
        if not description:
            logger.warning("Skipping risk %s with empty description", risk_id)
            return None
        
        return Risk(
            id=risk_id,
            clause_id=clause_id,
            severity=severity,
            description=description,
            recommendation=recommendation
        )
    
    def _parse_compliance_issues(self, api_response: Dict[str, Any]) -> List[ComplianceIssue]:
        """
        Parse compliance issues from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of ComplianceIssue objects
        """
        compliance_issues = []
        issues_data = api_response.get('compliance_issues', [])
        
        if not isinstance(issues_data, list):
            logger.warning("Compliance issues field is not a list, skipping")
            return compliance_issues
        
        for idx, issue_data in enumerate(issues_data):
            try:
                issue = self._parse_single_compliance_issue(issue_data, idx)
                if issue:
                    compliance_issues.append(issue)
            except Exception as e:
                logger.warning("Failed to parse compliance issue %d: %s", idx, e)
                continue
        
        return compliance_issues
    
    def _parse_single_compliance_issue(
        self,
        issue_data: Dict[str, Any],
        index: int
    ) -> Optional[ComplianceIssue]:
        """
        Parse a single compliance issue from data.
        
        Args:
            issue_data: Compliance issue data dictionary
            index: Index of the issue (for generating default ID)
        
        Returns:
            ComplianceIssue object or None if parsing fails
        """
        if not isinstance(issue_data, dict):
            return None
        
        # Extract fields with defaults
        issue_id = issue_data.get('id', f'compliance_{index + 1}')
        regulation = issue_data.get('regulation', 'Unknown')
        issue = issue_data.get('issue', '')
        severity = issue_data.get('severity', 'low')
        
        # Validate severity
        if severity not in ['low', 'medium', 'high']:
            logger.warning("Invalid severity '%s' for compliance issue %s, defaulting to 'low'", 
                         severity, issue_id)
            severity = 'low'
        
        # Skip issues with no description
        if not issue:
            logger.warning("Skipping compliance issue %s with empty description", issue_id)
            return None
        
        return ComplianceIssue(
            id=issue_id,
            regulation=regulation,
            issue=issue,
            severity=severity
        )
    
    def _parse_redlining_suggestions(self, api_response: Dict[str, Any]) -> List[RedliningSuggestion]:
        """
        Parse redlining suggestions from API response.
        
        Args:
            api_response: API response dictionary
        
        Returns:
            List of RedliningSuggestion objects
        """
        suggestions = []
        suggestions_data = api_response.get('redlining_suggestions', [])
        
        if not isinstance(suggestions_data, list):
            logger.warning("Redlining suggestions field is not a list, skipping")
            return suggestions
        
        for idx, suggestion_data in enumerate(suggestions_data):
            try:
                suggestion = self._parse_single_redlining_suggestion(suggestion_data, idx)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.warning("Failed to parse redlining suggestion %d: %s", idx, e)
                continue
        
        return suggestions
    
    def _parse_single_redlining_suggestion(
        self,
        suggestion_data: Dict[str, Any],
        index: int
    ) -> Optional[RedliningSuggestion]:
        """
        Parse a single redlining suggestion from data.
        
        Args:
            suggestion_data: Redlining suggestion data dictionary
            index: Index of the suggestion
        
        Returns:
            RedliningSuggestion object or None if parsing fails
        """
        if not isinstance(suggestion_data, dict):
            return None
        
        # Extract fields
        clause_id = suggestion_data.get('clause_id', '')
        original_text = suggestion_data.get('original_text', '')
        suggested_text = suggestion_data.get('suggested_text', '')
        rationale = suggestion_data.get('rationale', '')
        
        # Skip suggestions with missing required fields
        if not clause_id or not original_text or not suggested_text:
            logger.warning("Skipping redlining suggestion %d with missing required fields", index)
            return None
        
        return RedliningSuggestion(
            clause_id=clause_id,
            original_text=original_text,
            suggested_text=suggested_text,
            rationale=rationale
        )
