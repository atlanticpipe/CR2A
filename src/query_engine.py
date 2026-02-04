"""
Query Engine for Contract Analysis Chat Interface.

This module provides the QueryEngine class that manages the query workflow,
integrating with OpenAI API for response generation and handling context
formatting and relevance extraction.

Supports optional verification mode for answer validation.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from src.openai_fallback_client import OpenAIClient
from src.analysis_models import AnalysisResult
from src.exhaustiveness_models import VerifiedQueryResponse
from openai import RateLimitError, APIConnectionError, AuthenticationError, APIError

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Query engine that manages query-response workflow.
    
    Integrates with OpenAI API to process user queries against analyzed
    contract data, handling context formatting and relevance extraction.
    
    Memory optimizations:
    - Limits context data to most relevant information
    - Truncates large data structures to fit within token limits
    - Passes empty conversation history to reduce memory usage
    """
    
    # Maximum number of items to include in context
    MAX_CLAUSES = 10
    MAX_RISKS = 10
    MAX_COMPLIANCE = 5
    MAX_REDLINING = 5
    
    def __init__(self, openai_client: OpenAIClient):
        """
        Initialize QueryEngine with an OpenAIClient instance.
        
        Args:
            openai_client: Initialized OpenAIClient for response generation
        """
        self.openai_client = openai_client
        self._verification_layer = None
        self._exhaustiveness_gate = None
        logger.info("QueryEngine initialized with memory optimization limits")
    
    def process_query(
        self,
        query: str,
        analysis_result: Dict[str, Any],
        verify: bool = False,
        contract_text: Optional[str] = None
    ) -> Union[str, VerifiedQueryResponse]:
        """
        Process query and return response.
        
        This is the main entry point for query processing. It formats the
        analysis result as context, extracts relevant information, and
        generates a natural language response using the OpenAI API.
        
        When verify=True, the response is verified against the contract text
        to detect hallucinations and provide source references.
        
        Args:
            query: User's question
            analysis_result: Full analysis result dictionary (from AnalysisResult.to_dict())
            verify: If True, verify the response against contract text
            contract_text: Contract text for verification (required if verify=True)
            
        Returns:
            Formatted response text (standard mode), or
            VerifiedQueryResponse (verification mode)
            
        Raises:
            ValueError: If analysis_result is invalid or verify=True without contract_text
            APIError: If OpenAI API returns an error
            APIConnectionError: If network connection fails
            RateLimitError: If rate limit is exceeded
            AuthenticationError: If API key is invalid
        """
        if not query or not query.strip():
            if verify:
                return VerifiedQueryResponse(
                    query=query,
                    response="Please provide a question about the contract.",
                    is_verified=False,
                    verification_status="not_found",
                    verified_portions=[],
                    unverified_portions=[],
                    source_references=[],
                    confidence_score=0.0
                )
            return "Please provide a question about the contract."
        
        if not analysis_result:
            if verify:
                return VerifiedQueryResponse(
                    query=query,
                    response="No contract analysis data available. Please analyze a contract first.",
                    is_verified=False,
                    verification_status="not_found",
                    verified_portions=[],
                    unverified_portions=[],
                    source_references=[],
                    confidence_score=0.0
                )
            return "No contract analysis data available. Please analyze a contract first."
        
        if verify and not contract_text:
            raise ValueError("contract_text is required when verify=True")
        
        try:
            logger.info(f"Processing query: {query} (verify={verify})")
            clauses = analysis_result.get('clauses', [])
            logger.info(f"Analysis result has {len(clauses)} clauses")
            if clauses:
                logger.debug(f"First clause keys: {list(clauses[0].keys()) if clauses else 'N/A'}")
            
            # Format context for the LLM
            formatted_context = self.format_context(analysis_result, query)
            logger.info(f"Formatted context has {len(formatted_context.get('clauses', []))} clauses")
            
            # Generate response using OpenAI API
            # Note: We pass empty conversation history to reduce memory usage
            response = self.openai_client.process_query(
                query=query,
                context=formatted_context,
                conversation_history=[]  # Empty context to reduce memory usage
            )
            
            logger.info("Query processed successfully")
            
            # If verification is requested, verify the response
            if verify:
                return self._verify_response(query, response, contract_text, analysis_result)
            
            return response
            
        except (RateLimitError, APIConnectionError, AuthenticationError, APIError) as e:
            logger.error(f"OpenAI API error processing query: {e}")
            # Return user-friendly error messages
            error_msg = self._get_error_message(e)
            
            if verify:
                return VerifiedQueryResponse(
                    query=query,
                    response=error_msg,
                    is_verified=False,
                    verification_status="error",
                    verified_portions=[],
                    unverified_portions=[],
                    source_references=[],
                    confidence_score=0.0
                )
            return error_msg
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_msg = f"I encountered an error processing your question: {str(e)}"
            
            if verify:
                return VerifiedQueryResponse(
                    query=query,
                    response=error_msg,
                    is_verified=False,
                    verification_status="error",
                    verified_portions=[],
                    unverified_portions=[],
                    source_references=[],
                    confidence_score=0.0
                )
            return error_msg
    
    def _get_error_message(self, error: Exception) -> str:
        """Get user-friendly error message for API errors."""
        if isinstance(error, RateLimitError):
            return "The AI service is busy. Please try again in a moment."
        elif isinstance(error, APIConnectionError):
            return "Unable to connect to the AI service. Please check your internet connection."
        elif isinstance(error, AuthenticationError):
            return "API key is invalid. Please update your API key in Settings."
        else:
            return "An error occurred while processing your question. Please try again."
    
    def _verify_response(
        self,
        query: str,
        response: str,
        contract_text: str,
        analysis_result: Dict[str, Any]
    ) -> VerifiedQueryResponse:
        """
        Verify a query response against the contract text.
        
        Args:
            query: User's question
            response: Generated response to verify
            contract_text: Original contract text
            analysis_result: Analysis result for context
            
        Returns:
            VerifiedQueryResponse with verification status and sources
        """
        # Lazy initialization of verification components
        if self._exhaustiveness_gate is None:
            from src.exhaustiveness_gate import ExhaustivenessGate
            # Create a minimal gate just for query verification
            self._exhaustiveness_gate = ExhaustivenessGate(
                analysis_engine=None,  # Not needed for query verification
                openai_client=self.openai_client,
                num_passes=2
            )
        
        return self._exhaustiveness_gate.verify_query_response(
            query=query,
            response=response,
            contract_text=contract_text
        )

    def format_context(self, analysis_result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format analysis result as context for LLM.
        
        Supports both legacy and comprehensive schema formats.
        Selects relevant portions of analysis based on query to fit within
        the model's context window (~2000 tokens). Uses keyword matching to
        extract the most relevant clauses, risks, and compliance issues.
        
        Args:
            analysis_result: Full analysis result dictionary (legacy or comprehensive format)
            query: User's question (used for relevance extraction)
            
        Returns:
            Filtered analysis result dictionary with relevant data
        """
        try:
            logger.debug("Formatting context for query")
            
            # Detect schema format
            from src.result_parser import ComprehensiveResultParser
            schema_format = ComprehensiveResultParser.detect_schema_format(analysis_result)
            
            logger.debug("Detected schema format: %s", schema_format)
            
            # Extract data based on format
            if schema_format == "comprehensive":
                return self._format_context_comprehensive(analysis_result, query)
            else:
                return self._format_context_legacy(analysis_result, query)
            
        except Exception as e:
            logger.error(f"Error formatting context: {e}")
            # Return minimal context on error
            metadata_key = 'metadata' if 'metadata' in analysis_result else 'contract_metadata'
            return {
                metadata_key: analysis_result.get(metadata_key, {}),
                'clauses': [],
                'risks': [],
                'compliance_issues': [],
                'redlining_suggestions': []
            }
    
    def _format_context_legacy(self, analysis_result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format legacy analysis result as context for LLM.
        
        Args:
            analysis_result: Legacy format analysis result dictionary
            query: User's question
            
        Returns:
            Filtered analysis result dictionary with relevant data
        """
        # Extract keywords from query for relevance matching
        query_lower = query.lower()
        
        # Get all clauses
        all_clauses = analysis_result.get('clauses', [])
        
        # Extract relevant clauses based on query
        relevant_clauses = self.extract_relevant_clauses(query, all_clauses)
        
        # Get risks associated with relevant clauses
        relevant_clause_ids = {clause['id'] for clause in relevant_clauses}
        all_risks = analysis_result.get('risks', [])
        relevant_risks = [
            risk for risk in all_risks 
            if risk.get('clause_id') in relevant_clause_ids
        ]
        
        # Check if query mentions compliance/regulation keywords
        compliance_keywords = ['compliance', 'regulation', 'gdpr', 'ccpa', 'sox', 'legal', 'law']
        mentions_compliance = any(keyword in query_lower for keyword in compliance_keywords)
        
        # Include compliance issues if query mentions compliance or if no specific clauses found
        all_compliance = analysis_result.get('compliance_issues', [])
        if mentions_compliance or not relevant_clauses:
            relevant_compliance = all_compliance[:5]  # Limit to 5 for context size
        else:
            relevant_compliance = []
        
        # Check if query mentions redlining/changes/suggestions
        redlining_keywords = ['change', 'modify', 'suggest', 'improve', 'redline', 'edit', 'revise']
        mentions_redlining = any(keyword in query_lower for keyword in redlining_keywords)
        
        # Include redlining suggestions if query mentions them or for relevant clauses
        all_redlining = analysis_result.get('redlining_suggestions', [])
        if mentions_redlining:
            relevant_redlining = all_redlining[:5]  # Limit to 5
        else:
            relevant_redlining = [
                suggestion for suggestion in all_redlining
                if suggestion.get('clause_id') in relevant_clause_ids
            ]
        
        # Build formatted context with relevant data (limited for memory optimization)
        formatted_context = {
            'contract_metadata': analysis_result.get('contract_metadata', {}),
            'clauses': relevant_clauses[:self.MAX_CLAUSES],  # Limit to MAX_CLAUSES
            'risks': relevant_risks[:self.MAX_RISKS],  # Limit to MAX_RISKS
            'compliance_issues': relevant_compliance[:self.MAX_COMPLIANCE],  # Limit to MAX_COMPLIANCE
            'redlining_suggestions': relevant_redlining[:self.MAX_REDLINING]  # Limit to MAX_REDLINING
        }
        
        # CRITICAL: Always ensure we have clauses if they exist in the analysis
        # This ensures the chat can answer questions about the contract
        if not formatted_context['clauses'] and all_clauses:
            logger.debug("No relevant clauses found by keyword matching, including all clauses")
            formatted_context['clauses'] = all_clauses[:self.MAX_CLAUSES]
        
        # If no relevant data found, include a summary of all data (still limited)
        if not relevant_clauses and not relevant_risks and not relevant_compliance:
            logger.debug("No specific relevant data found, including summary")
            formatted_context = {
                'contract_metadata': analysis_result.get('contract_metadata', {}),
                'clauses': all_clauses[:self.MAX_CLAUSES],  # Include more clauses
                'risks': all_risks[:self.MAX_RISKS],  # Include more risks
                'compliance_issues': all_compliance[:self.MAX_COMPLIANCE],
                'redlining_suggestions': all_redlining[:self.MAX_REDLINING]
            }
        
        logger.debug(f"Context formatted: {len(formatted_context['clauses'])} clauses, "
                    f"{len(formatted_context['risks'])} risks, "
                    f"{len(formatted_context['compliance_issues'])} compliance issues")
        
        return formatted_context
    
    def _format_context_comprehensive(self, analysis_result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format comprehensive analysis result as context for LLM.
        
        Args:
            analysis_result: Comprehensive format analysis result dictionary
            query: User's question
            
        Returns:
            Filtered analysis result dictionary with relevant data
        """
        query_lower = query.lower()
        
        # Extract all clause blocks from all sections
        all_clause_blocks = []
        section_names = [
            'administrative_and_commercial_terms',
            'technical_and_performance_terms',
            'legal_risk_and_enforcement',
            'regulatory_and_compliance_terms',
            'data_technology_and_deliverables'
        ]
        
        for section_name in section_names:
            section_data = analysis_result.get(section_name, {})
            if isinstance(section_data, dict):
                for clause_name, clause_block in section_data.items():
                    if clause_block and isinstance(clause_block, dict):
                        # Add section and clause name for context
                        clause_block_copy = clause_block.copy()
                        clause_block_copy['_section'] = section_name
                        clause_block_copy['_clause_name'] = clause_name
                        all_clause_blocks.append(clause_block_copy)
        
        # Add supplemental operational risks
        supplemental = analysis_result.get('supplemental_operational_risks', [])
        for idx, block in enumerate(supplemental):
            if block and isinstance(block, dict):
                block_copy = block.copy()
                block_copy['_section'] = 'supplemental_operational_risks'
                block_copy['_clause_name'] = f'risk_{idx + 1}'
                all_clause_blocks.append(block_copy)
        
        # Filter clause blocks based on query relevance
        relevant_blocks = self._extract_relevant_clause_blocks(query, all_clause_blocks)
        
        # If no relevant blocks found, include all blocks (limited)
        if not relevant_blocks:
            logger.debug("No relevant clause blocks found, including all blocks")
            relevant_blocks = all_clause_blocks[:self.MAX_CLAUSES]
        else:
            relevant_blocks = relevant_blocks[:self.MAX_CLAUSES]
        
        # Build formatted context
        formatted_context = {
            'metadata': analysis_result.get('metadata', {}),
            'contract_overview': analysis_result.get('contract_overview', {}),
            'clause_blocks': relevant_blocks,
            'schema_version': analysis_result.get('schema_version', 'unknown')
        }
        
        logger.debug(f"Context formatted: {len(relevant_blocks)} clause blocks from comprehensive schema")
        
        return formatted_context
    
    def _extract_relevant_clause_blocks(
        self, 
        query: str, 
        clause_blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract clause blocks relevant to query using keyword matching.
        
        Args:
            query: User's question
            clause_blocks: List of clause block dictionaries
            
        Returns:
            List of relevant clause blocks, sorted by relevance
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_blocks = []
        
        for block in clause_blocks:
            score = 0
            
            # Check clause language
            clause_language = block.get('Clause Language', block.get('clause_language', '')).lower()
            clause_summary = block.get('Clause Summary', block.get('clause_summary', '')).lower()
            
            # Count matching words
            for word in query_words:
                if len(word) > 3:  # Only count words longer than 3 chars
                    if word in clause_language:
                        score += 2
                    if word in clause_summary:
                        score += 1
            
            # Check risk triggers
            risk_triggers = block.get('Risk Triggers Identified', block.get('risk_triggers_identified', []))
            for trigger in risk_triggers:
                if isinstance(trigger, str) and any(word in trigger.lower() for word in query_words if len(word) > 3):
                    score += 3
            
            # Check clause name
            clause_name = block.get('_clause_name', '').lower()
            for word in query_words:
                if len(word) > 3 and word in clause_name:
                    score += 1
            
            if score > 0:
                scored_blocks.append((score, block))
        
        # Sort by score (highest first)
        scored_blocks.sort(key=lambda x: x[0], reverse=True)
        
        return [block for score, block in scored_blocks]
    
    def extract_relevant_clauses(self, query: str, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract clauses relevant to query using keyword matching.
        
        Uses simple keyword matching to identify clauses that are most likely
        relevant to the user's question. Matches against clause type, text,
        and risk level.
        
        Args:
            query: User's question
            clauses: List of clause dictionaries
            
        Returns:
            List of relevant clause dictionaries, sorted by relevance
        """
        if not clauses:
            return []
        
        try:
            logger.debug(f"Extracting relevant clauses from {len(clauses)} total clauses")
            
            # Extract keywords from query (remove common stop words)
            stop_words = {
                'what', 'when', 'where', 'who', 'how', 'why', 'is', 'are', 'the', 
                'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'about', 'can', 'you', 'tell', 'me', 'show', 'find', 'get', 'any',
                'this', 'that', 'these', 'those', 'there', 'here', 'does', 'do'
            }
            
            query_lower = query.lower()
            query_words = query_lower.split()
            keywords = [
                word.strip('?.,!') 
                for word in query_words 
                if word.lower() not in stop_words and len(word) > 2
            ]
            
            if not keywords:
                # If no keywords, return first few clauses
                return clauses[:5]
            
            logger.debug(f"Query keywords: {keywords}")
            
            # Score each clause based on keyword matches
            scored_clauses = []
            for clause in clauses:
                score = 0
                clause_text = clause.get('text', '').lower()
                clause_type = clause.get('type', '').lower()
                clause_risk = clause.get('risk_level', '').lower()
                
                # Check each keyword
                for keyword in keywords:
                    # Higher weight for matches in clause type
                    if keyword in clause_type:
                        score += 3
                    
                    # Medium weight for matches in clause text
                    if keyword in clause_text:
                        score += 2
                    
                    # Check for risk-related keywords
                    if keyword in ['risk', 'danger', 'problem', 'issue'] and clause_risk in ['high', 'critical']:
                        score += 2
                    
                    # Check for specific clause type keywords
                    type_keywords = {
                        'payment': ['payment', 'pay', 'money', 'fee', 'cost', 'price'],
                        'liability': ['liability', 'liable', 'responsible', 'fault'],
                        'termination': ['termination', 'terminate', 'end', 'cancel', 'exit'],
                        'warranty': ['warranty', 'guarantee', 'assurance'],
                        'indemnity': ['indemnity', 'indemnification', 'protect', 'defend'],
                        'confidentiality': ['confidential', 'secret', 'private', 'nda'],
                        'intellectual_property': ['ip', 'intellectual', 'property', 'patent', 'copyright', 'trademark']
                    }
                    
                    for clause_category, category_keywords in type_keywords.items():
                        if keyword in category_keywords and clause_category in clause_type:
                            score += 4
                
                if score > 0:
                    scored_clauses.append((score, clause))
            
            # Sort by score (descending) and return top matches
            scored_clauses.sort(key=lambda x: x[0], reverse=True)
            relevant_clauses = [clause for score, clause in scored_clauses if score > 0]
            
            logger.debug(f"Found {len(relevant_clauses)} relevant clauses")
            
            # If no relevant clauses found by keyword matching, return first clauses as fallback
            if not relevant_clauses:
                logger.debug("No keyword matches, returning first 10 clauses as fallback")
                return clauses[:10]
            
            # Return top 10 most relevant clauses
            return relevant_clauses[:10]
            
        except Exception as e:
            logger.error(f"Error extracting relevant clauses: {e}")
            # Return first few clauses on error
            return clauses[:5]
