"""
Query Engine for Contract Analysis Chat Interface.

This module provides the QueryEngine class that manages the query workflow,
integrating with the local AI model for response generation and handling context
formatting and relevance extraction.

Supports optional verification mode for answer validation.
"""

import logging
from typing import Dict, List, Any, Optional
from analysis_models import AnalysisResult

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Query engine that manages query-response workflow.

    Integrates with local AI model to process user queries against analyzed
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

    def __init__(self, ai_client, chat_history_manager=None, retriever=None):
        """
        Initialize QueryEngine with an AI client instance.

        Args:
            ai_client: Initialized AI client with process_query() method
            chat_history_manager: Optional ChatHistoryManager for saving chat history
            retriever: Optional DocumentRetriever for searching raw contract sections
        """
        self.ai_client = ai_client
        self.chat_history_manager = chat_history_manager
        self.retriever = retriever
        self.indexed_contract = None  # Set when a contract is loaded
        logger.info("QueryEngine initialized with memory optimization limits")
    
    def process_query(
        self,
        query: str,
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        Process query and return response.

        Uses tri-layer retrieval to search the full contract text if available,
        falling back to analysis results only if no retriever is configured.

        Args:
            query: User's question
            analysis_result: Full analysis result dictionary (from AnalysisResult.to_dict())

        Returns:
            Formatted response text
        """
        if not query or not query.strip():
            return "Please provide a question about the contract."

        if not analysis_result:
            return "No contract analysis data available. Please analyze a contract first."

        try:
            logger.info(f"Processing query: {query}")

            # Try retriever-based search first (searches full contract text)
            retrieved_sections = ""
            if self.retriever and self.indexed_contract:
                results = self.retriever.retrieve_for_query(query, top_k=5)
                if results:
                    retrieved_sections = self.retriever.format_sections_for_ai(results, max_chars=4000)
                    logger.info(f"Retrieved {len(results)} sections for query")

            # Also get analysis context (existing clause summaries)
            formatted_context = self.format_context(analysis_result, query)
            logger.info(f"Formatted context has {len(formatted_context.get('clauses', []))} clauses")

            # If we have retrieved sections, inject them into the context
            if retrieved_sections:
                formatted_context['_retrieved_sections'] = retrieved_sections

            # Generate response using AI model
            response = self.ai_client.process_query(
                query=query,
                context=formatted_context,
                conversation_history=[]
            )

            logger.info("Query processed successfully")

            # Save to chat history if available
            self._save_chat_history(query, response, analysis_result)

            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error processing your question: {str(e)}"

    def _save_chat_history(self, question: str, answer: str, analysis_result: Dict[str, Any]) -> None:
        """
        Save chat entry to history with user attribution.

        Args:
            question: User's question
            answer: AI's answer (can be string or VerifiedQueryResponse)
            analysis_result: Analysis result dictionary
        """
        if not self.chat_history_manager:
            return

        try:
            answer_text = answer
            if hasattr(answer, 'response'):
                answer_text = answer.response

            # Get contract metadata
            metadata = analysis_result.get('metadata', {})
            contract_file = metadata.get('filename', 'unknown')
            contract_version = metadata.get('version', 1)

            # Get model info
            model_metadata = {
                'model': getattr(self.ai_client, 'model', 'unknown')
            }

            # Create and save chat entry
            from chat_history_manager import ChatHistoryManager
            chat_entry = ChatHistoryManager.create_chat_entry(
                question=question,
                answer=answer_text,
                contract_file=contract_file,
                contract_version=contract_version,
                metadata=model_metadata
            )

            self.chat_history_manager.append_chat(chat_entry)
            logger.info(f"Chat entry saved: {chat_entry.get('chat_id')}")

        except Exception as e:
            # Don't fail the query if chat history fails
            logger.warning(f"Failed to save chat history: {e}")

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
            from result_parser import ComprehensiveResultParser
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
            
            # Check clause location
            clause_location = (block.get('Clause Location') or block.get('clause_location')
                             or block.get('Clause Language') or block.get('clause_language', '')).lower()
            clause_summary = (block.get('Clause Summary') or block.get('clause_summary', '')).lower()

            # Count matching words
            for word in query_words:
                if len(word) > 3:  # Only count words longer than 3 chars
                    if word in clause_location:
                        score += 2
                    if word in clause_summary:
                        score += 2
            
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
                        'confidentiality': ['confidential', 'secret', 'private', 'nda']
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
