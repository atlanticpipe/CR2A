# Contract Analysis Skills

## When to Use Contract Analysis

Use `analyze_contract_category` when the user asks about specific contract clauses or topics:
- "What does the indemnification clause say?" -> analyze_contract_category(category="indemnification")
- "Check the termination provisions" -> analyze_contract_category(category="termination_for_convenience") then analyze_contract_category(category="termination_for_cause")
- "Are there price escalation clauses?" -> analyze_contract_category(category="price_escalation")

Use `run_full_contract_analysis` when the user wants a comprehensive review:
- "Analyze this contract"
- "Run a full review"
- "What are the risks in this contract?"

## Category Key Reference

### I. Administrative & Commercial Terms
contract_term_renewal_extensions, bonding_surety_insurance, retainage_progress_payments, pay_when_paid_if_paid, price_escalation, fuel_price_adjustment, change_orders, termination_for_convenience, termination_for_cause, bid_protest, bid_tabulation, contractor_qualification, release_orders, assignment_novation, audit_rights, notice_requirements

### II. Technical & Performance Terms
scope_of_work, performance_schedule, delays, suspension_of_work, submittals, emergency_work, permits_licensing, warranty, use_of_aps_tools, owner_supplied_support, field_ticket, mobilization_demobilization, utility_coordination, delivery_deadlines, punch_list, worksite_coordination, deliverables

### III. Legal Risk & Enforcement
indemnification, duty_to_defend, limitation_of_liability, insurance_coverage, dispute_resolution, flow_down_clauses, subcontracting, safety_osha, site_conditions, environmental, order_of_precedence, setoff_withholding

### IV. Regulatory & Compliance Terms
certified_payroll, prevailing_wage, eeo, mwbe_dbe, apprenticeship, e_verify, worker_classification, drug_free_workplace

### V. Data, Technology & Deliverables
data_ownership, ai_technology_use, cybersecurity, digital_deliverables, document_retention, confidentiality

## Interpreting Results

Each category result contains:
- **Clause Summary**: What the contract says about this topic
- **Clause Location**: Section/article reference in the document
- **Redline Recommendations**: Suggested changes or negotiation points
- **Harmful Language**: Clauses that pose unusual risk to the contractor

When presenting results, lead with the risk level and key concern, then provide the detail.
