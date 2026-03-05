"""
Unit tests for Analysis Result data models.

Tests the data models for contract analysis results including
serialization, deserialization, and validation.
"""

import pytest
from datetime import datetime
from src.analysis_models import (
    ContractMetadata,
    Clause,
    Risk,
    ComplianceIssue,
    RedliningSuggestion,
    AnalysisResult,
    RedlineRecommendation,
    ClauseBlock,
    ContractOverview,
    VALID_REDLINE_ACTIONS,
    VALID_RISK_LEVELS,
    VALID_BID_MODELS
)


class TestRedlineRecommendation:
    """Tests for RedlineRecommendation model."""
    
    def test_create_with_insert_action(self):
        """Test creating RedlineRecommendation with insert action."""
        rec = RedlineRecommendation(
            action="insert",
            text="Add liability cap of $1M",
            reference="Section 5.2"
        )
        
        assert rec.action == "insert"
        assert rec.text == "Add liability cap of $1M"
        assert rec.reference == "Section 5.2"
    
    def test_create_with_replace_action(self):
        """Test creating RedlineRecommendation with replace action."""
        rec = RedlineRecommendation(
            action="replace",
            text="Replace unlimited liability with capped liability"
        )
        
        assert rec.action == "replace"
        assert rec.text == "Replace unlimited liability with capped liability"
        assert rec.reference is None
    
    def test_create_with_delete_action(self):
        """Test creating RedlineRecommendation with delete action."""
        rec = RedlineRecommendation(
            action="delete",
            text="Remove non-compete clause"
        )
        
        assert rec.action == "delete"
        assert rec.text == "Remove non-compete clause"
    
    def test_invalid_action_raises_error(self):
        """Test that invalid action raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            RedlineRecommendation(
                action="modify",
                text="Some text"
            )
        
        assert "Invalid action 'modify'" in str(exc_info.value)
        assert "insert" in str(exc_info.value)
        assert "replace" in str(exc_info.value)
        assert "delete" in str(exc_info.value)
    
    def test_to_dict_with_reference(self):
        """Test converting to dictionary with reference."""
        rec = RedlineRecommendation(
            action="insert",
            text="Add clause",
            reference="Policy 3.1"
        )
        
        result = rec.to_dict()
        
        assert result['action'] == "insert"
        assert result['text'] == "Add clause"
        assert result['reference'] == "Policy 3.1"
    
    def test_to_dict_without_reference(self):
        """Test converting to dictionary without reference (omits None)."""
        rec = RedlineRecommendation(
            action="delete",
            text="Remove clause"
        )
        
        result = rec.to_dict()
        
        assert result['action'] == "delete"
        assert result['text'] == "Remove clause"
        assert 'reference' not in result
    
    def test_from_dict_with_reference(self):
        """Test creating from dictionary with reference."""
        data = {
            'action': 'replace',
            'text': 'New text',
            'reference': 'Section 2.1'
        }
        
        rec = RedlineRecommendation.from_dict(data)
        
        assert rec.action == "replace"
        assert rec.text == "New text"
        assert rec.reference == "Section 2.1"
    
    def test_from_dict_without_reference(self):
        """Test creating from dictionary without reference."""
        data = {
            'action': 'insert',
            'text': 'New clause text'
        }
        
        rec = RedlineRecommendation.from_dict(data)
        
        assert rec.action == "insert"
        assert rec.text == "New clause text"
        assert rec.reference is None
    
    def test_from_dict_invalid_action(self):
        """Test that from_dict raises error for invalid action."""
        data = {
            'action': 'update',
            'text': 'Some text'
        }
        
        with pytest.raises(ValueError) as exc_info:
            RedlineRecommendation.from_dict(data)
        
        assert "Invalid action 'update'" in str(exc_info.value)
    
    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = RedlineRecommendation(
            action="replace",
            text="Replace with new terms",
            reference="Legal review"
        )
        
        serialized = original.to_dict()
        restored = RedlineRecommendation.from_dict(serialized)
        
        assert restored.action == original.action
        assert restored.text == original.text
        assert restored.reference == original.reference
    
    def test_valid_actions_constant(self):
        """Test that VALID_REDLINE_ACTIONS contains expected values."""
        assert "insert" in VALID_REDLINE_ACTIONS
        assert "replace" in VALID_REDLINE_ACTIONS
        assert "delete" in VALID_REDLINE_ACTIONS
        assert len(VALID_REDLINE_ACTIONS) == 3


class TestClauseBlock:
    """Tests for ClauseBlock model."""
    
    def test_create_clause_block(self):
        """Test creating ClauseBlock instance with all fields."""
        rec = RedlineRecommendation(action="insert", text="Add liability cap")
        
        block = ClauseBlock(
            clause_language="The contractor shall be liable for all damages.",
            clause_summary="Unlimited liability clause",
            risk_triggers_identified=["unlimited liability", "all damages"],
            flow_down_obligations=["Pass to subcontractors"],
            redline_recommendations=[rec],
            harmful_language_policy_conflicts=["Conflicts with company policy on liability caps"]
        )
        
        assert block.clause_language == "The contractor shall be liable for all damages."
        assert block.clause_summary == "Unlimited liability clause"
        assert block.risk_triggers_identified == ["unlimited liability", "all damages"]
        assert block.flow_down_obligations == ["Pass to subcontractors"]
        assert len(block.redline_recommendations) == 1
        assert block.redline_recommendations[0].action == "insert"
        assert block.harmful_language_policy_conflicts == ["Conflicts with company policy on liability caps"]
    
    def test_create_clause_block_with_empty_lists(self):
        """Test creating ClauseBlock with empty lists."""
        block = ClauseBlock(
            clause_language="Simple clause text",
            clause_summary="A simple clause",
            risk_triggers_identified=[],
            flow_down_obligations=[],
            redline_recommendations=[],
            harmful_language_policy_conflicts=[]
        )
        
        assert block.clause_language == "Simple clause text"
        assert block.risk_triggers_identified == []
        assert block.flow_down_obligations == []
        assert block.redline_recommendations == []
        assert block.harmful_language_policy_conflicts == []
    
    def test_to_dict_maps_to_schema_format(self):
        """Test that to_dict maps Python field names to schema format."""
        rec = RedlineRecommendation(action="replace", text="New text", reference="Section 3")
        
        block = ClauseBlock(
            clause_language="Original clause text",
            clause_summary="Summary of clause",
            risk_triggers_identified=["risk1", "risk2"],
            flow_down_obligations=["obligation1"],
            redline_recommendations=[rec],
            harmful_language_policy_conflicts=["conflict1"]
        )
        
        result = block.to_dict()
        
        # Verify schema format keys
        assert result['Clause Language'] == "Original clause text"
        assert result['Clause Summary'] == "Summary of clause"
        assert result['Risk Triggers Identified'] == ["risk1", "risk2"]
        assert result['Flow-Down Obligations'] == ["obligation1"]
        assert result['Harmful Language / Policy Conflicts'] == ["conflict1"]
        
        # Verify nested RedlineRecommendation is serialized
        assert len(result['Redline Recommendations']) == 1
        assert result['Redline Recommendations'][0]['action'] == "replace"
        assert result['Redline Recommendations'][0]['text'] == "New text"
        assert result['Redline Recommendations'][0]['reference'] == "Section 3"
    
    def test_to_dict_with_multiple_redline_recommendations(self):
        """Test to_dict with multiple redline recommendations."""
        recs = [
            RedlineRecommendation(action="insert", text="Add clause"),
            RedlineRecommendation(action="delete", text="Remove clause"),
            RedlineRecommendation(action="replace", text="Replace text", reference="Policy")
        ]
        
        block = ClauseBlock(
            clause_language="Clause text",
            clause_summary="Summary",
            risk_triggers_identified=[],
            flow_down_obligations=[],
            redline_recommendations=recs,
            harmful_language_policy_conflicts=[]
        )
        
        result = block.to_dict()
        
        assert len(result['Redline Recommendations']) == 3
        assert result['Redline Recommendations'][0]['action'] == "insert"
        assert result['Redline Recommendations'][1]['action'] == "delete"
        assert result['Redline Recommendations'][2]['action'] == "replace"
    
    def test_from_dict_with_schema_format_keys(self):
        """Test from_dict with schema format keys (spaces in names)."""
        data = {
            'Clause Language': 'The clause text',
            'Clause Summary': 'A summary',
            'Risk Triggers Identified': ['trigger1', 'trigger2'],
            'Flow-Down Obligations': ['obligation1'],
            'Redline Recommendations': [
                {'action': 'insert', 'text': 'Add text'}
            ],
            'Harmful Language / Policy Conflicts': ['conflict1']
        }
        
        block = ClauseBlock.from_dict(data)
        
        assert block.clause_language == 'The clause text'
        assert block.clause_summary == 'A summary'
        assert block.risk_triggers_identified == ['trigger1', 'trigger2']
        assert block.flow_down_obligations == ['obligation1']
        assert len(block.redline_recommendations) == 1
        assert block.redline_recommendations[0].action == 'insert'
        assert block.harmful_language_policy_conflicts == ['conflict1']
    
    def test_from_dict_with_python_format_keys(self):
        """Test from_dict with Python format keys (underscores)."""
        data = {
            'clause_language': 'The clause text',
            'clause_summary': 'A summary',
            'risk_triggers_identified': ['trigger1'],
            'flow_down_obligations': ['obligation1'],
            'redline_recommendations': [
                {'action': 'delete', 'text': 'Remove text'}
            ],
            'harmful_language_policy_conflicts': []
        }
        
        block = ClauseBlock.from_dict(data)
        
        assert block.clause_language == 'The clause text'
        assert block.clause_summary == 'A summary'
        assert block.risk_triggers_identified == ['trigger1']
        assert block.flow_down_obligations == ['obligation1']
        assert len(block.redline_recommendations) == 1
        assert block.redline_recommendations[0].action == 'delete'
    
    def test_from_dict_with_empty_data(self):
        """Test from_dict with minimal/empty data uses defaults."""
        data = {}
        
        block = ClauseBlock.from_dict(data)
        
        assert block.clause_language == ''
        assert block.clause_summary == ''
        assert block.risk_triggers_identified == []
        assert block.flow_down_obligations == []
        assert block.redline_recommendations == []
        assert block.harmful_language_policy_conflicts == []
    
    def test_from_dict_handles_redline_recommendation_objects(self):
        """Test from_dict handles already-parsed RedlineRecommendation objects."""
        rec = RedlineRecommendation(action="insert", text="Add text")
        data = {
            'clause_language': 'Text',
            'clause_summary': 'Summary',
            'risk_triggers_identified': [],
            'flow_down_obligations': [],
            'redline_recommendations': [rec],  # Already a RedlineRecommendation object
            'harmful_language_policy_conflicts': []
        }
        
        block = ClauseBlock.from_dict(data)
        
        assert len(block.redline_recommendations) == 1
        assert block.redline_recommendations[0] is rec
    
    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = ClauseBlock(
            clause_language="Original clause language text",
            clause_summary="This is a summary of the clause",
            risk_triggers_identified=["risk1", "risk2", "risk3"],
            flow_down_obligations=["obligation1", "obligation2"],
            redline_recommendations=[
                RedlineRecommendation(action="insert", text="Insert this"),
                RedlineRecommendation(action="replace", text="Replace with this", reference="Ref1")
            ],
            harmful_language_policy_conflicts=["conflict1"]
        )
        
        serialized = original.to_dict()
        restored = ClauseBlock.from_dict(serialized)
        
        assert restored.clause_language == original.clause_language
        assert restored.clause_summary == original.clause_summary
        assert restored.risk_triggers_identified == original.risk_triggers_identified
        assert restored.flow_down_obligations == original.flow_down_obligations
        assert restored.harmful_language_policy_conflicts == original.harmful_language_policy_conflicts
        
        # Check nested redline recommendations
        assert len(restored.redline_recommendations) == len(original.redline_recommendations)
        for orig_rec, rest_rec in zip(original.redline_recommendations, restored.redline_recommendations):
            assert rest_rec.action == orig_rec.action
            assert rest_rec.text == orig_rec.text
            assert rest_rec.reference == orig_rec.reference


class TestContractOverview:
    """Tests for ContractOverview model."""
    
    def test_create_contract_overview(self):
        """Test creating ContractOverview instance with all fields."""
        overview = ContractOverview(
            project_title="Highway Construction Project",
            solicitation_no="SOL-2024-001",
            owner="State Department of Transportation",
            contractor="ABC Construction Inc.",
            scope="Construction of 5-mile highway extension",
            general_risk_level="Medium",
            bid_model="Lump Sum",
            notes="Contract includes environmental compliance requirements"
        )
        
        assert overview.project_title == "Highway Construction Project"
        assert overview.solicitation_no == "SOL-2024-001"
        assert overview.owner == "State Department of Transportation"
        assert overview.contractor == "ABC Construction Inc."
        assert overview.scope == "Construction of 5-mile highway extension"
        assert overview.general_risk_level == "Medium"
        assert overview.bid_model == "Lump Sum"
        assert overview.notes == "Contract includes environmental compliance requirements"
    
    def test_valid_risk_levels(self):
        """Test that all valid risk levels are accepted."""
        for risk_level in ["Low", "Medium", "High", "Critical"]:
            overview = ContractOverview(
                project_title="Test Project",
                solicitation_no="TEST-001",
                owner="Owner",
                contractor="Contractor",
                scope="Test scope",
                general_risk_level=risk_level,
                bid_model="Lump Sum",
                notes=""
            )
            assert overview.general_risk_level == risk_level
    
    def test_valid_bid_models(self):
        """Test that all valid bid models are accepted."""
        valid_models = ["Lump Sum", "Unit Price", "Cost Plus", "Time & Materials", 
                        "GMP", "Design-Build", "Other"]
        for bid_model in valid_models:
            overview = ContractOverview(
                project_title="Test Project",
                solicitation_no="TEST-001",
                owner="Owner",
                contractor="Contractor",
                scope="Test scope",
                general_risk_level="Low",
                bid_model=bid_model,
                notes=""
            )
            assert overview.bid_model == bid_model
    
    def test_invalid_risk_level_raises_error(self):
        """Test that invalid risk level raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ContractOverview(
                project_title="Test Project",
                solicitation_no="TEST-001",
                owner="Owner",
                contractor="Contractor",
                scope="Test scope",
                general_risk_level="Invalid",
                bid_model="Lump Sum",
                notes=""
            )
        
        assert "Invalid general_risk_level 'Invalid'" in str(exc_info.value)
        assert "Low" in str(exc_info.value)
        assert "Medium" in str(exc_info.value)
        assert "High" in str(exc_info.value)
        assert "Critical" in str(exc_info.value)
    
    def test_invalid_bid_model_raises_error(self):
        """Test that invalid bid model raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ContractOverview(
                project_title="Test Project",
                solicitation_no="TEST-001",
                owner="Owner",
                contractor="Contractor",
                scope="Test scope",
                general_risk_level="Low",
                bid_model="Invalid Model",
                notes=""
            )
        
        assert "Invalid bid_model 'Invalid Model'" in str(exc_info.value)
        assert "Lump Sum" in str(exc_info.value)
    
    def test_to_dict_maps_to_schema_format(self):
        """Test that to_dict maps Python field names to schema format."""
        overview = ContractOverview(
            project_title="Highway Project",
            solicitation_no="SOL-2024-001",
            owner="DOT",
            contractor="ABC Inc.",
            scope="Highway construction",
            general_risk_level="High",
            bid_model="Unit Price",
            notes="Important notes"
        )
        
        result = overview.to_dict()
        
        # Verify schema format keys
        assert result['Project Title'] == "Highway Project"
        assert result['Solicitation No.'] == "SOL-2024-001"
        assert result['Owner'] == "DOT"
        assert result['Contractor'] == "ABC Inc."
        assert result['Scope'] == "Highway construction"
        assert result['General Risk Level'] == "High"
        assert result['Bid Model'] == "Unit Price"
        assert result['Notes'] == "Important notes"
    
    def test_from_dict_with_schema_format_keys(self):
        """Test from_dict with schema format keys (spaces in names)."""
        data = {
            'Project Title': 'Bridge Construction',
            'Solicitation No.': 'SOL-2024-002',
            'Owner': 'City of Springfield',
            'Contractor': 'XYZ Builders',
            'Scope': 'Bridge construction over river',
            'General Risk Level': 'Critical',
            'Bid Model': 'Design-Build',
            'Notes': 'Expedited timeline'
        }
        
        overview = ContractOverview.from_dict(data)
        
        assert overview.project_title == 'Bridge Construction'
        assert overview.solicitation_no == 'SOL-2024-002'
        assert overview.owner == 'City of Springfield'
        assert overview.contractor == 'XYZ Builders'
        assert overview.scope == 'Bridge construction over river'
        assert overview.general_risk_level == 'Critical'
        assert overview.bid_model == 'Design-Build'
        assert overview.notes == 'Expedited timeline'
    
    def test_from_dict_with_python_format_keys(self):
        """Test from_dict with Python format keys (underscores)."""
        data = {
            'project_title': 'Office Building',
            'solicitation_no': 'SOL-2024-003',
            'owner': 'Private Corp',
            'contractor': 'Build Co',
            'scope': 'Office building construction',
            'general_risk_level': 'Low',
            'bid_model': 'GMP',
            'notes': 'Standard project'
        }
        
        overview = ContractOverview.from_dict(data)
        
        assert overview.project_title == 'Office Building'
        assert overview.solicitation_no == 'SOL-2024-003'
        assert overview.owner == 'Private Corp'
        assert overview.contractor == 'Build Co'
        assert overview.scope == 'Office building construction'
        assert overview.general_risk_level == 'Low'
        assert overview.bid_model == 'GMP'
        assert overview.notes == 'Standard project'
    
    def test_from_dict_with_empty_data_raises_error(self):
        """Test from_dict with empty data raises error due to invalid enum values."""
        data = {}
        
        # Empty strings are not valid enum values
        with pytest.raises(ValueError):
            ContractOverview.from_dict(data)
    
    def test_round_trip_serialization(self):
        """Test that to_dict and from_dict are inverse operations."""
        original = ContractOverview(
            project_title="Test Project Title",
            solicitation_no="TEST-SOL-001",
            owner="Test Owner Organization",
            contractor="Test Contractor LLC",
            scope="Complete scope description for testing",
            general_risk_level="Medium",
            bid_model="Cost Plus",
            notes="Additional notes for testing round-trip"
        )
        
        serialized = original.to_dict()
        restored = ContractOverview.from_dict(serialized)
        
        assert restored.project_title == original.project_title
        assert restored.solicitation_no == original.solicitation_no
        assert restored.owner == original.owner
        assert restored.contractor == original.contractor
        assert restored.scope == original.scope
        assert restored.general_risk_level == original.general_risk_level
        assert restored.bid_model == original.bid_model
        assert restored.notes == original.notes
    
    def test_valid_risk_levels_constant(self):
        """Test that VALID_RISK_LEVELS contains expected values."""
        assert "Low" in VALID_RISK_LEVELS
        assert "Medium" in VALID_RISK_LEVELS
        assert "High" in VALID_RISK_LEVELS
        assert "Critical" in VALID_RISK_LEVELS
        assert len(VALID_RISK_LEVELS) == 4
    
    def test_valid_bid_models_constant(self):
        """Test that VALID_BID_MODELS contains expected values."""
        assert "Lump Sum" in VALID_BID_MODELS
        assert "Unit Price" in VALID_BID_MODELS
        assert "Cost Plus" in VALID_BID_MODELS
        assert "Time & Materials" in VALID_BID_MODELS
        assert "GMP" in VALID_BID_MODELS
        assert "Design-Build" in VALID_BID_MODELS
        assert "Other" in VALID_BID_MODELS
        assert len(VALID_BID_MODELS) == 7


class TestContractMetadata:
    """Tests for ContractMetadata model."""
    
    def test_create_metadata(self):
        """Test creating ContractMetadata instance."""
        now = datetime.now()
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=now,
            page_count=10,
            file_size_bytes=1024
        )
        
        assert metadata.filename == "test.pdf"
        assert metadata.analyzed_at == now
        assert metadata.page_count == 10
        assert metadata.file_size_bytes == 1024
    
    def test_to_dict(self):
        """Test converting metadata to dictionary."""
        now = datetime.now()
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=now,
            page_count=10,
            file_size_bytes=1024
        )
        
        result = metadata.to_dict()
        
        assert result['filename'] == "test.pdf"
        assert result['analyzed_at'] == now.isoformat()
        assert result['page_count'] == 10
        assert result['file_size_bytes'] == 1024
    
    def test_from_dict(self):
        """Test creating metadata from dictionary."""
        now = datetime.now()
        data = {
            'filename': 'test.pdf',
            'analyzed_at': now.isoformat(),
            'page_count': 10,
            'file_size_bytes': 1024
        }
        
        metadata = ContractMetadata.from_dict(data)
        
        assert metadata.filename == "test.pdf"
        assert metadata.page_count == 10
        assert metadata.file_size_bytes == 1024


class TestClause:
    """Tests for Clause model."""
    
    def test_create_clause(self):
        """Test creating Clause instance."""
        clause = Clause(
            id="clause_1",
            type="payment_terms",
            text="Payment shall be made within 30 days",
            page=3,
            risk_level="low"
        )
        
        assert clause.id == "clause_1"
        assert clause.type == "payment_terms"
        assert clause.text == "Payment shall be made within 30 days"
        assert clause.page == 3
        assert clause.risk_level == "low"
    
    def test_to_dict(self):
        """Test converting clause to dictionary."""
        clause = Clause(
            id="clause_1",
            type="payment_terms",
            text="Payment shall be made within 30 days",
            page=3,
            risk_level="low"
        )
        
        result = clause.to_dict()
        
        assert result['id'] == "clause_1"
        assert result['type'] == "payment_terms"
        assert result['text'] == "Payment shall be made within 30 days"
        assert result['page'] == 3
        assert result['risk_level'] == "low"
    
    def test_from_dict(self):
        """Test creating clause from dictionary."""
        data = {
            'id': 'clause_1',
            'type': 'payment_terms',
            'text': 'Payment shall be made within 30 days',
            'page': 3,
            'risk_level': 'low'
        }
        
        clause = Clause.from_dict(data)
        
        assert clause.id == "clause_1"
        assert clause.type == "payment_terms"


class TestRisk:
    """Tests for Risk model."""
    
    def test_create_risk(self):
        """Test creating Risk instance."""
        risk = Risk(
            id="risk_1",
            clause_id="clause_1",
            severity="high",
            description="Unlimited liability",
            recommendation="Negotiate liability cap"
        )
        
        assert risk.id == "risk_1"
        assert risk.clause_id == "clause_1"
        assert risk.severity == "high"
        assert risk.description == "Unlimited liability"
        assert risk.recommendation == "Negotiate liability cap"


class TestComplianceIssue:
    """Tests for ComplianceIssue model."""
    
    def test_create_compliance_issue(self):
        """Test creating ComplianceIssue instance."""
        issue = ComplianceIssue(
            id="compliance_1",
            regulation="GDPR",
            issue="Missing data processing terms",
            severity="medium"
        )
        
        assert issue.id == "compliance_1"
        assert issue.regulation == "GDPR"
        assert issue.issue == "Missing data processing terms"
        assert issue.severity == "medium"


class TestRedliningSuggestion:
    """Tests for RedliningSuggestion model."""
    
    def test_create_redlining_suggestion(self):
        """Test creating RedliningSuggestion instance."""
        suggestion = RedliningSuggestion(
            clause_id="clause_1",
            original_text="Original text",
            suggested_text="Suggested text",
            rationale="Clarify terms"
        )
        
        assert suggestion.clause_id == "clause_1"
        assert suggestion.original_text == "Original text"
        assert suggestion.suggested_text == "Suggested text"
        assert suggestion.rationale == "Clarify terms"


class TestAnalysisResult:
    """Tests for AnalysisResult model."""
    
    def test_create_analysis_result(self):
        """Test creating AnalysisResult instance."""
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=1024
        )
        
        result = AnalysisResult(metadata=metadata)
        
        assert result.metadata == metadata
        assert result.clauses == []
        assert result.risks == []
        assert result.compliance_issues == []
        assert result.redlining_suggestions == []
    
    def test_to_dict(self):
        """Test converting analysis result to dictionary."""
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=1024
        )
        
        clause = Clause(
            id="clause_1",
            type="payment_terms",
            text="Payment terms",
            page=1,
            risk_level="low"
        )
        
        result = AnalysisResult(
            metadata=metadata,
            clauses=[clause]
        )
        
        result_dict = result.to_dict()
        
        assert 'contract_metadata' in result_dict
        assert 'clauses' in result_dict
        assert len(result_dict['clauses']) == 1
    
    def test_from_dict(self):
        """Test creating analysis result from dictionary."""
        now = datetime.now()
        data = {
            'contract_metadata': {
                'filename': 'test.pdf',
                'analyzed_at': now.isoformat(),
                'page_count': 10,
                'file_size_bytes': 1024
            },
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment terms',
                    'page': 1,
                    'risk_level': 'low'
                }
            ],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        result = AnalysisResult.from_dict(data)
        
        assert result.metadata.filename == "test.pdf"
        assert len(result.clauses) == 1
        assert result.clauses[0].id == "clause_1"
    
    def test_validate_result_valid(self):
        """Test validation of valid analysis result."""
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=1024
        )
        
        clause = Clause(
            id="clause_1",
            type="payment_terms",
            text="Payment terms",
            page=1,
            risk_level="low"
        )
        
        result = AnalysisResult(
            metadata=metadata,
            clauses=[clause]
        )
        
        assert result.validate_result() is True
    
    def test_validate_result_invalid_clause_risk_level(self):
        """Test validation fails for invalid clause risk level."""
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=1024
        )
        
        clause = Clause(
            id="clause_1",
            type="payment_terms",
            text="Payment terms",
            page=1,
            risk_level="invalid"
        )
        
        result = AnalysisResult(
            metadata=metadata,
            clauses=[clause]
        )
        
        assert result.validate_result() is False
    
    def test_validate_result_empty_lists(self):
        """Test validation passes with empty lists."""
        metadata = ContractMetadata(
            filename="test.pdf",
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=1024
        )
        
        result = AnalysisResult(metadata=metadata)
        
        assert result.validate_result() is True
