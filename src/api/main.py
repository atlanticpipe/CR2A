"""
CR2A REST API - Contract Risk & Compliance Analyzer
Provides endpoints for contract submission, analysis, and progress tracking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

from src.core.config import AppConfig, get_secret_env_or_aws
from src.core.llm_analyzer import LLMAnalyzer, AnalysisStage, ProgressUpdate, AnalysisResult
from src.services.document_processor import DocumentProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
UPLOAD_FOLDER = "/tmp/cr2a_uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# Global state (in production, use Redis or database)
analysis_store = {}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def initialize_analyzer() -> LLMAnalyzer:
    """Initialize the LLM analyzer with API credentials."""
    config = AppConfig.from_env()

    api_key = get_secret_env_or_aws("OPENAI_API_KEY", "OPENAI_API_KEY_ARN")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment or AWS Secrets Manager")

    analyzer = LLMAnalyzer(api_key=api_key, model=config.openai_model)
    return analyzer


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route("/analyze", methods=["POST"])
def submit_analysis():
    """
    Submit a contract for analysis.

    Form data:
        - file: PDF/DOCX/TXT file
        - contract_id: Unique contract identifier (optional)

    Returns:
        JSON with analysis_id, status, and submission timestamp
    """
    logger.info("Received analysis submission")

    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"})

    if not allowed_file(file.filename):
        return jsonify(
            {"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}
        ), 400

    # Generate IDs
    analysis_id = str(uuid.uuid4())
    contract_id = request.form.get("contract_id", f"CONTRACT-{analysis_id[:8]}")

    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], f"{analysis_id}_{filename}")
    file.save(filepath)

    # Store analysis metadata
    analysis_store[analysis_id] = {
        "status": "queued",
        "contract_id": contract_id,
        "filepath": filepath,
        "submitted_at": datetime.utcnow().isoformat(),
        "progress": {
            "stage": AnalysisStage.INITIALIZATION.value,
            "percentage": 0,
            "message": "Queued for analysis",
        },
    }

    logger.info(f"Analysis {analysis_id} queued for contract {contract_id}")

    return (
        jsonify(
            {
                "analysis_id": analysis_id,
                "contract_id": contract_id,
                "status": "queued",
                "submitted_at": analysis_store[analysis_id]["submitted_at"],
            }
        ),
        202,
    )


@app.route("/analyze/<analysis_id>/stream", methods=["GET"])
def stream_analysis(analysis_id: str):
    """
    Stream analysis progress and results.

    Returns: Server-sent events stream with progress updates and final result
    """
    if analysis_id not in analysis_store:
        return jsonify({"error": f"Analysis {analysis_id} not found"}), 404

    def event_stream():
        """Generate server-sent events for analysis progress."""
        try:
            # Get analysis metadata
            metadata = analysis_store[analysis_id]
            filepath = metadata["filepath"]
            contract_id = metadata["contract_id"]

            # Extract text from file
            processor = DocumentProcessor()
            contract_text = processor.extract_text(filepath)
            metadata["status"] = "processing"

            # Initialize analyzer
            analyzer = initialize_analyzer()

            # Run streaming analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def run_analysis():
                async for update in analyzer.analyze_streaming(
                    contract_text=contract_text,
                    contract_id=contract_id,
                    analysis_id=analysis_id,
                ):
                    if isinstance(update, ProgressUpdate):
                        # Yield progress update
                        metadata["progress"] = {
                            "stage": update.stage.value,
                            "percentage": update.percentage,
                            "message": update.message,
                            "detail": update.detail,
                        }

                        yield f"data: {json.dumps({'type': 'progress', 'data': metadata['progress']})}\n\n"

                    elif isinstance(update, AnalysisResult):
                        # Yield final result
                        metadata["status"] = "complete"
                        metadata["result"] = {
                            "analysis_id": update.analysis_id,
                            "contract_id": update.contract_id,
                            "risk_level": update.risk_level,
                            "overall_score": update.overall_score,
                            "executive_summary": update.executive_summary,
                            "findings": [
                                {
                                    "clause_type": f.clause_type,
                                    "risk_level": f.risk_level,
                                    "concern": f.concern,
                                    "recommendation": f.recommendation,
                                }
                                for f in update.findings
                            ],
                            "recommendations": update.recommendations,
                            "compliance_issues": update.compliance_issues,
                            "metadata": update.metadata,
                        }
                        metadata["completed_at"] = datetime.utcnow().isoformat()

                        yield f"data: {json.dumps({'type': 'result', 'data': metadata['result']})}\n\n"
                        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

            loop.run_until_complete(run_analysis())

        except Exception as e:
            logger.error(f"Error during streaming analysis: {e}")
            analysis_store[analysis_id]["status"] = "error"
            analysis_store[analysis_id]["error"] = str(e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


@app.route("/status/<analysis_id>", methods=["GET"])
def get_status(analysis_id: str):
    """
    Get current status and progress of an analysis.

    Returns:
        JSON with status, progress, and metadata
    """
    if analysis_id not in analysis_store:
        return jsonify({"error": f"Analysis {analysis_id} not found"}), 404

    metadata = analysis_store[analysis_id]
    return jsonify(
        {
            "analysis_id": analysis_id,
            "contract_id": metadata["contract_id"],
            "status": metadata["status"],
            "progress": metadata.get("progress"),
            "submitted_at": metadata["submitted_at"],
            "completed_at": metadata.get("completed_at"),
            "error": metadata.get("error"),
        }
    ), 200


@app.route("/results/<analysis_id>", methods=["GET"])
def get_results(analysis_id: str):
    """
    Get analysis results.

    Returns:
        JSON with complete analysis results
    """
    if analysis_id not in analysis_store:
        return jsonify({"error": f"Analysis {analysis_id} not found"}), 404

    metadata = analysis_store[analysis_id]

    if metadata["status"] != "complete":
        return (
            jsonify(
                {"error": f"Analysis status is {metadata['status']}, not complete"}
            ),
            202,
        )

    return jsonify(metadata.get("result")), 200


@app.route("/download/<analysis_id>", methods=["GET"])
def download_report(analysis_id: str):
    """
    Download analysis report as PDF.

    Returns:
        PDF file
    """
    if analysis_id not in analysis_store:
        return jsonify({"error": f"Analysis {analysis_id} not found"}), 404

    metadata = analysis_store[analysis_id]

    if metadata["status"] != "complete":
        return (
            jsonify({"error": f"Analysis not complete"}),
            202,
        )

    result = metadata.get("result")
    if not result:
        return jsonify({"error": "No results available"}), 404

    # TODO: Implement PDF export using pdf_export service
    # For now, return JSON
    return jsonify(result), 200


@app.route("/analyses", methods=["GET"])
def list_analyses():
    """
    List all analyses (with pagination).

    Returns:
        JSON array of analysis metadata
    """
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    analyses = list(analysis_store.items())[offset : offset + limit]

    return jsonify(
        {
            "total": len(analysis_store),
            "limit": limit,
            "offset": offset,
            "analyses": [
                {
                    "analysis_id": aid,
                    "contract_id": metadata["contract_id"],
                    "status": metadata["status"],
                    "submitted_at": metadata["submitted_at"],
                }
                for aid, metadata in analyses
            ],
        }
    ), 200


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({"error": "File too large. Maximum size is 500 MB"}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    # For local development only
    app.run(debug=True, port=5000)
