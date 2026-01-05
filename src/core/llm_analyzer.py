"""
LLM-Powered Contract Analysis Engine
Handles contract analysis using GPT-4 with streaming progress updates.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from typing import AsyncGenerator, Optional
from enum import Enum

from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)


class AnalysisStage(str, Enum):
    """Progress stages during analysis."""
    INITIALIZATION = "initialization"
    TEXT_EXTRACTION = "text_extraction"
    CLAUSE_EXTRACTION = "clause_extraction"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECK = "compliance_check"
    SUMMARY_GENERATION = "summary_generation"
    REPORT_GENERATION = "report_generation"
    COMPLETE = "complete"


@dataclass
class ProgressUpdate:
    """Represents a progress update during analysis."""
    stage: AnalysisStage
    percentage: int
    message: str
    detail: Optional[str] = None


@dataclass
class ClauseFinding:
    """Represents a clause finding from analysis."""
    clause_type: str
    text: str
    risk_level: str  # HIGH, MEDIUM, LOW
    concern: str
    recommendation: str


@dataclass
class AnalysisResult:
    """Complete analysis result."""
    analysis_id: str
    contract_id: str
    risk_level: str  # HIGH, MEDIUM, LOW
    overall_score: float  # 0-100
    executive_summary: str
    findings: list[ClauseFinding]
    recommendations: list[str]
    compliance_issues: list[str]
    metadata: dict


class LLMAnalyzer:
    """Main analyzer using LLM for contract analysis."""

    def __init__(self, api_key: str, model: str = "gpt-5.2"):
        """
        Initialize the LLM analyzer.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-5.2)
        """
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            self.client = OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI clients: {e}")
            raise ValueError(f"Failed to initialize OpenAI clients: {e}") from e
        
        self.model = model

    def analyze(
        self,
        contract_text: str,
        contract_id: str,
        analysis_id: str,
    ) -> AnalysisResult:
        """
        Analyze a contract synchronously.

        Args:
            contract_text: Full contract text
            contract_id: Contract identifier
            analysis_id: Analysis session ID

        Returns:
            AnalysisResult with findings and recommendations
        """
        logger.info(f"Starting analysis for {contract_id}")

        # Step 1: Extract clauses
        clauses = self._extract_clauses(contract_text)
        logger.info(f"Extracted {len(clauses)} clauses")

        # Step 2: Assess risks
        findings = self._assess_risks(clauses)
        logger.info(f"Assessed {len(findings)} findings")

        # Step 3: Check compliance
        compliance_issues = self._check_compliance(findings, contract_text)
        logger.info(f"Found {len(compliance_issues)} compliance issues")

        # Step 4: Generate summary
        executive_summary = self._generate_summary(findings, compliance_issues)

        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(findings, compliance_issues)

        # Calculate overall risk
        risk_level, overall_score = self._calculate_risk_score(findings)

        result = AnalysisResult(
            analysis_id=analysis_id,
            contract_id=contract_id,
            risk_level=risk_level,
            overall_score=overall_score,
            executive_summary=executive_summary,
            findings=findings,
            recommendations=recommendations,
            compliance_issues=compliance_issues,
            metadata={
                "model": self.model,
                "clause_count": len(clauses),
                "finding_count": len(findings),
            },
        )

        logger.info(f"Analysis complete for {contract_id}")
        return result

    async def analyze_streaming(
        self,
        contract_text: str,
        contract_id: str,
        analysis_id: str,
    ) -> AsyncGenerator[ProgressUpdate | AnalysisResult, None]:
        """
        Analyze a contract with streaming progress updates.

        Yields:
            ProgressUpdate objects during analysis, then AnalysisResult
        """
        try:
            # Stage 1: Initialization
            yield ProgressUpdate(
                stage=AnalysisStage.INITIALIZATION,
                percentage=5,
                message="Initializing analysis engine",
            )

            # Stage 2: Clause Extraction
            yield ProgressUpdate(
                stage=AnalysisStage.TEXT_EXTRACTION,
                percentage=10,
                message="Extracting text from contract",
            )

            # Stage 3: Extract clauses with streaming
            yield ProgressUpdate(
                stage=AnalysisStage.CLAUSE_EXTRACTION,
                percentage=25,
                message="Identifying and classifying clauses",
            )
            clauses = await self._extract_clauses_async(contract_text)

            # Stage 4: Risk Assessment
            yield ProgressUpdate(
                stage=AnalysisStage.RISK_ASSESSMENT,
                percentage=45,
                message=f"Assessing risks for {len(clauses)} clauses",
            )
            findings = await self._assess_risks_async(clauses)

            # Stage 5: Compliance Check
            yield ProgressUpdate(
                stage=AnalysisStage.COMPLIANCE_CHECK,
                percentage=65,
                message="Checking compliance against policy standards",
            )
            compliance_issues = await self._check_compliance_async(findings, contract_text)

            # Stage 6: Summary Generation
            yield ProgressUpdate(
                stage=AnalysisStage.SUMMARY_GENERATION,
                percentage=80,
                message="Generating executive summary",
            )
            executive_summary = await self._generate_summary_async(
                findings, compliance_issues
            )

            # Stage 7: Recommendations
            yield ProgressUpdate(
                stage=AnalysisStage.SUMMARY_GENERATION,
                percentage=90,
                message="Generating recommendations",
            )
            recommendations = await self._generate_recommendations_async(
                findings, compliance_issues
            )

            # Calculate risk
            risk_level, overall_score = self._calculate_risk_score(findings)

            # Stage 8: Report Generation & Complete
            yield ProgressUpdate(
                stage=AnalysisStage.REPORT_GENERATION,
                percentage=95,
                message="Finalizing report",
            )

            result = AnalysisResult(
                analysis_id=analysis_id,
                contract_id=contract_id,
                risk_level=risk_level,
                overall_score=overall_score,
                executive_summary=executive_summary,
                findings=findings,
                recommendations=recommendations,
                compliance_issues=compliance_issues,
                metadata={
                    "model": self.model,
                    "clause_count": len(clauses),
                    "finding_count": len(findings),
                },
            )

            yield ProgressUpdate(
                stage=AnalysisStage.COMPLETE,
                percentage=100,
                message="Analysis complete",
            )

            yield result

        except Exception as e:
            logger.error(f"Error during streaming analysis: {e}")
            raise

    def _extract_clauses(self, contract_text: str) -> list[str]:
        """Extract clauses from contract text using LLM."""
        prompt = f"""Analyze this contract and extract all distinct clauses and sections. 
For each clause, provide:
1. The clause type (e.g., Indemnification, Liability, Warranty, Payment Terms, etc.)
2. The complete clause text

Return as JSON array with objects containing 'type' and 'text' fields.

Contract:
{contract_text[:10000]}

JSON Response:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            result = json.loads(response.choices[0].message.content)
            return [clause.get("text", "") for clause in result if clause.get("text")]
        except json.JSONDecodeError:
            logger.warning("Failed to parse clauses JSON, returning raw response")
            return [response.choices[0].message.content] if response else []
        except Exception as e:
            logger.error(f"Failed to extract clauses: {e}")
            return []

    async def _extract_clauses_async(self, contract_text: str) -> list[str]:
        """Extract clauses asynchronously."""
        prompt = f"""Analyze this contract and extract all distinct clauses and sections. 
For each clause, provide:
1. The clause type (e.g., Indemnification, Liability, Warranty, Payment Terms, etc.)
2. The complete clause text

Return as JSON array with objects containing 'type' and 'text' fields.

Contract:
{contract_text[:10000]}

JSON Response:"""

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        try:
            result = json.loads(response.choices[0].message.content)
            return [clause.get("text", "") for clause in result if clause.get("text")]
        except json.JSONDecodeError:
            logger.warning("Failed to parse clauses JSON, returning raw response")
            return [response.choices[0].message.content]

    def _assess_risks(self, clauses: list[str]) -> list[ClauseFinding]:
        """Assess risks in clauses using LLM."""
        findings = []

        for clause in clauses[:20]:  # Limit to first 20 for API calls
            prompt = f"""Analyze this contract clause for risks and compliance issues:

{clause}

Provide assessment in JSON format with:
- clause_type: string
- risk_level: 'HIGH', 'MEDIUM', or 'LOW'
- concern: string describing the risk
- recommendation: string with mitigation advice

JSON Response:"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            try:
                data = json.loads(response.choices[0].message.content)
                finding = ClauseFinding(
                    clause_type=data.get("clause_type", "Unknown"),
                    text=clause,
                    risk_level=data.get("risk_level", "MEDIUM"),
                    concern=data.get("concern", ""),
                    recommendation=data.get("recommendation", ""),
                )
                findings.append(finding)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse clause assessment")

        return findings

    async def _assess_risks_async(self, clauses: list[str]) -> list[ClauseFinding]:
        """Assess risks asynchronously."""
        findings = []

        for clause in clauses[:20]:  # Limit to first 20
            prompt = f"""Analyze this contract clause for risks and compliance issues:

{clause}

Provide assessment in JSON format with:
- clause_type: string
- risk_level: 'HIGH', 'MEDIUM', or 'LOW'
- concern: string describing the risk
- recommendation: string with mitigation advice

JSON Response:"""

            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            try:
                data = json.loads(response.choices[0].message.content)
                finding = ClauseFinding(
                    clause_type=data.get("clause_type", "Unknown"),
                    text=clause,
                    risk_level=data.get("risk_level", "MEDIUM"),
                    concern=data.get("concern", ""),
                    recommendation=data.get("recommendation", ""),
                )
                findings.append(finding)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse clause assessment")

        return findings

    def _check_compliance(
        self, findings: list[ClauseFinding], contract_text: str
    ) -> list[str]:
        """Check compliance against policy standards."""
        prompt = f"""Based on these findings, identify compliance issues:

Findings Summary:
{json.dumps([asdict(f) for f in findings[:10]], indent=2)}

Contract excerpt:
{contract_text[:5000]}

Return as JSON array of compliance issue strings.

JSON Response:"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return []

    async def _check_compliance_async(
        self, findings: list[ClauseFinding], contract_text: str
    ) -> list[str]:
        """Check compliance asynchronously."""
        prompt = f"""Based on these findings, identify compliance issues:

Findings Summary:
{json.dumps([asdict(f) for f in findings[:10]], indent=2)}

Contract excerpt:
{contract_text[:5000]}

Return as JSON array of compliance issue strings.

JSON Response:"""

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return []

    def _generate_summary(
        self, findings: list[ClauseFinding], compliance_issues: list[str]
    ) -> str:
        """Generate executive summary."""
        prompt = f"""Generate a concise executive summary for contract analysis:

Key Findings ({len(findings)} total):
{json.dumps([asdict(f) for f in findings[:5]], indent=2)}

Compliance Issues ({len(compliance_issues)} total):
{json.dumps(compliance_issues[:5], indent=2)}

Provide 2-3 paragraph summary highlighting key risks and recommendations."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        return response.choices[0].message.content

    async def _generate_summary_async(
        self, findings: list[ClauseFinding], compliance_issues: list[str]
    ) -> str:
        """Generate executive summary asynchronously."""
        prompt = f"""Generate a concise executive summary for contract analysis:

Key Findings ({len(findings)} total):
{json.dumps([asdict(f) for f in findings[:5]], indent=2)}

Compliance Issues ({len(compliance_issues)} total):
{json.dumps(compliance_issues[:5], indent=2)}

Provide 2-3 paragraph summary highlighting key risks and recommendations."""

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        return response.choices[0].message.content

    def _generate_recommendations(
        self, findings: list[ClauseFinding], compliance_issues: list[str]
    ) -> list[str]:
        """Generate actionable recommendations."""
        if not findings and not compliance_issues:
            return ["Review contract with legal counsel"]

        prompt = f"""Based on these findings, generate 5-7 specific, actionable recommendations:

Findings:
{json.dumps([asdict(f) for f in findings[:5]], indent=2)}

Compliance Issues:
{json.dumps(compliance_issues[:5], indent=2)}

Return as JSON array of recommendation strings."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return ["Review contract with legal counsel"]

    async def _generate_recommendations_async(
        self, findings: list[ClauseFinding], compliance_issues: list[str]
    ) -> list[str]:
        """Generate recommendations asynchronously."""
        if not findings and not compliance_issues:
            return ["Review contract with legal counsel"]

        prompt = f"""Based on these findings, generate 5-7 specific, actionable recommendations:

Findings:
{json.dumps([asdict(f) for f in findings[:5]], indent=2)}

Compliance Issues:
{json.dumps(compliance_issues[:5], indent=2)}

Return as JSON array of recommendation strings."""

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return ["Review contract with legal counsel"]

    @staticmethod
    def _calculate_risk_score(findings: list[ClauseFinding]) -> tuple[str, float]:
        """Calculate overall risk level and score."""
        if not findings:
            return "LOW", 0.0

        risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for finding in findings:
            risk_counts[finding.risk_level] += 1

        total = len(findings)
        high_percent = (risk_counts["HIGH"] / total) * 100 if total > 0 else 0
        medium_percent = (risk_counts["MEDIUM"] / total) * 100 if total > 0 else 0

        # Determine overall risk level
        if high_percent > 20:
            risk_level = "HIGH"
            score = 75 + (high_percent * 0.25)
        elif high_percent > 0 or medium_percent > 40:
            risk_level = "MEDIUM"
            score = 40 + (high_percent * 0.5) + (medium_percent * 0.25)
        else:
            risk_level = "LOW"
            score = medium_percent * 0.3

        score = min(100.0, max(0.0, score))  # Clamp to 0-100
        return risk_level, score
