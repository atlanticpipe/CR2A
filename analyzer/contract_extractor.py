"""
Contract Section Extractor
Uses regex patterns to identify and extract relevant sections from contracts.
This reduces the amount of text sent to the AI API.
"""

import re
from typing import Dict, List, Tuple, Optional


# Legacy section patterns (kept for backward compatibility)
SECTION_PATTERNS = {
    'payment_terms': [
        r'payment\s+terms?',
        r'compensation',
        r'price',
        r'contract\s+(?:price|value|amount)',
        r'payment\s+schedule',
        r'invoicing',
        r'retainage',
        r'progress\s+payments?'
    ],
    'scope_of_work': [
        r'scope\s+of\s+work',
        r'work\s+to\s+be\s+performed',
        r'services',
        r'deliverables',
        r'project\s+description'
    ],
    'term_duration': [
        r'term\s+(?:of\s+)?(?:contract|agreement)',
        r'contract\s+period',
        r'duration',
        r'commencement',
        r'effective\s+date',
        r'expiration'
    ],
    'termination': [
        r'termination',
        r'cancellation',
        r'early\s+termination',
        r'termination\s+for\s+convenience',
        r'termination\s+for\s+cause'
    ],
    'indemnification': [
        r'indemnif(?:y|ication)',
        r'hold\s+harmless',
        r'defend',
        r'liability'
    ],
    'insurance': [
        r'insurance',
        r'coverage',
        r'additional\s+insured',
        r'waiver\s+of\s+subrogation'
    ],
    'warranties': [
        r'warrant(?:y|ies)',
        r'guarantee',
        r'defects?\s+liability'
    ],
    'dispute_resolution': [
        r'dispute\s+resolution',
        r'arbitration',
        r'mediation',
        r'litigation',
        r'governing\s+law'
    ],
    'change_orders': [
        r'change\s+orders?',
        r'modifications?',
        r'amendments?',
        r'scope\s+changes?'
    ],
    'delays': [
        r'delays?',
        r'force\s+majeure',
        r'excusable\s+delays?',
        r'time\s+extensions?'
    ],
    'parties': [
        r'parties',
        r'contractor',
        r'owner',
        r'client',
        r'vendor',
        r'between.*and'
    ]
}


# =============================================================================
# COMPREHENSIVE SECTION PATTERNS
# Extended pattern registry covering all 61+ clause categories from output_schemas_v1.json
# Keys match the exact schema category names for direct mapping
# =============================================================================

COMPREHENSIVE_SECTION_PATTERNS: Dict[str, List[str]] = {
    # =========================================================================
    # Section II: Administrative & Commercial Terms (16 categories)
    # =========================================================================
    
    'Contract Term, Renewal & Extensions': [
        r'contract\s+term',
        r'renewal',
        r'extension(?:s)?',
        r'duration\s+of\s+(?:contract|agreement)',
        r'term\s+of\s+(?:contract|agreement)',
        r'contract\s+period',
        r'effective\s+date',
        r'expiration\s+date',
        r'option\s+(?:to\s+)?(?:renew|extend)',
    ],
    
    'Bonding, Surety, & Insurance Obligations': [
        r'bond(?:ing)?',
        r'surety',
        r'performance\s+bond',
        r'payment\s+bond',
        r'bid\s+bond',
        r'insurance\s+(?:requirements?|obligations?)',
        r'certificate\s+of\s+insurance',
        r'bonding\s+(?:requirements?|capacity)',
    ],
    
    'Retainage, Progress Payments & Final Payment Terms': [
        r'retainage',
        r'retention',
        r'progress\s+payment(?:s)?',
        r'final\s+payment',
        r'payment\s+(?:terms?|schedule)',
        r'invoice',
        r'billing',
        r'pay\s+application',
        r'payment\s+(?:upon|after)\s+completion',
    ],
    
    'Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies': [
        r'pay[\s-]when[\s-]paid',
        r'pay[\s-]if[\s-]paid',
        r'payment\s+contingent',
        r'owner\s+payment\s+contingenc(?:y|ies)',
        r'payment\s+(?:conditioned|dependent)\s+(?:on|upon)',
        r'receipt\s+of\s+payment\s+from',
    ],
    
    'Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)': [
        r'price\s+escalation',
        r'cost\s+escalation',
        r'inflation\s+adjustment',
        r'labor\s+(?:cost\s+)?adjustment',
        r'material(?:s)?\s+(?:cost\s+)?adjustment',
        r'price\s+adjustment',
        r'economic\s+adjustment',
        r'cost[\s-]of[\s-]living',
        r'CPI\s+adjustment',
    ],
    
    'Fuel Price Adjustment / Fuel Cost Caps': [
        r'fuel\s+(?:price\s+)?adjustment',
        r'fuel\s+cost\s+cap',
        r'fuel\s+surcharge',
        r'fuel\s+escalation',
        r'petroleum\s+(?:price\s+)?adjustment',
        r'diesel\s+(?:price\s+)?adjustment',
    ],
    
    'Change Orders, Scope Adjustments & Modifications': [
        r'change\s+order(?:s)?',
        r'scope\s+(?:adjustment|change|modification)',
        r'contract\s+modification',
        r'amendment(?:s)?',
        r'variation(?:s)?',
        r'extra\s+work',
        r'additional\s+work',
        r'field\s+(?:change|order)',
        r'constructive\s+change',
    ],
    
    'Termination for Convenience (Owner/Agency Right to Terminate Without Cause)': [
        r'termination\s+for\s+convenience',
        r'terminate\s+(?:for\s+)?convenience',
        r'terminate\s+without\s+cause',
        r'termination\s+without\s+cause',
        r'owner(?:\'s)?\s+right\s+to\s+terminate',
        r'agency(?:\'s)?\s+right\s+to\s+terminate',
        r'unilateral\s+termination',
    ],
    
    'Termination for Cause / Default by Contractor': [
        r'termination\s+for\s+(?:cause|default)',
        r'terminate\s+for\s+(?:cause|default)',
        r'contractor\s+default',
        r'default\s+(?:by\s+)?contractor',
        r'material\s+breach',
        r'failure\s+to\s+perform',
        r'cure\s+period',
        r'notice\s+of\s+default',
    ],
    
    'Bid Protest Procedures & Claims of Improper Award': [
        r'bid\s+protest',
        r'protest\s+procedure(?:s)?',
        r'improper\s+award',
        r'award\s+protest',
        r'challenge\s+(?:to\s+)?(?:the\s+)?award',
        r'procurement\s+protest',
    ],
    
    'Bid Tabulation, Competition & Award Process Requirements': [
        r'bid\s+tabulation',
        r'competitive\s+bidding',
        r'award\s+process',
        r'bid\s+evaluation',
        r'lowest\s+(?:responsive\s+)?(?:responsible\s+)?bidder',
        r'best\s+value',
        r'bid\s+opening',
        r'sealed\s+bid(?:s)?',
    ],
    
    'Contractor Qualification, Licensing & Certification Requirements': [
        r'contractor\s+qualification(?:s)?',
        r'licensing\s+requirement(?:s)?',
        r'certification\s+requirement(?:s)?',
        r'prequalification',
        r'qualified\s+contractor',
        r'license(?:d)?\s+contractor',
        r'certified\s+contractor',
        r'contractor\s+registration',
    ],
    
    'Release Orders, Task Orders & Work Authorization Protocols': [
        r'release\s+order(?:s)?',
        r'task\s+order(?:s)?',
        r'work\s+(?:order|authorization)',
        r'delivery\s+order(?:s)?',
        r'notice\s+to\s+proceed',
        r'authorization\s+(?:to\s+)?(?:proceed|work)',
        r'work\s+directive',
    ],
    
    'Assignment & Novation Restrictions (Transfer of Contract Rights)': [
        r'assignment',
        r'novation',
        r'transfer\s+of\s+(?:contract|rights)',
        r'assign(?:ment)?\s+(?:of\s+)?(?:contract|rights)',
        r'sublet',
        r'delegation\s+of\s+(?:duties|obligations)',
        r'change\s+of\s+(?:ownership|control)',
    ],
    
    'Audit Rights, Recordkeeping & Document Retention Obligations': [
        r'audit\s+(?:rights?|provisions?)',
        r'recordkeeping',
        r'record\s+keeping',
        r'document\s+retention',
        r'records?\s+retention',
        r'inspection\s+of\s+records',
        r'access\s+to\s+(?:books|records)',
        r'maintain\s+records',
        r'retention\s+period',
    ],
    
    'Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)': [
        r'notice\s+requirement(?:s)?',
        r'claim\s+(?:timeframe|deadline|period)',
        r'notice\s+to\s+cure',
        r'delay\s+notice',
        r'termination\s+notice',
        r'written\s+notice',
        r'notice\s+period',
        r'notice\s+provision(?:s)?',
        r'timely\s+notice',
        r'notice\s+of\s+claim',
    ],
    
    # =========================================================================
    # Section III: Technical & Performance Terms (17 categories)
    # =========================================================================
    
    'Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)': [
        r'scope\s+of\s+work',
        r'work\s+(?:inclusions?|exclusions?)',
        r'defined\s+deliverables?',
        r'statement\s+of\s+work',
        r'SOW',
        r'work\s+to\s+be\s+performed',
        r'services\s+(?:to\s+be\s+)?(?:provided|rendered)',
        r'project\s+(?:scope|description)',
        r'contract\s+(?:scope|work)',
    ],
    
    'Performance Schedule, Time for Completion & Critical Path Obligations': [
        r'performance\s+schedule',
        r'time\s+for\s+completion',
        r'critical\s+path',
        r'project\s+schedule',
        r'construction\s+schedule',
        r'schedule\s+of\s+(?:work|performance)',
        r'completion\s+(?:date|time|deadline)',
        r'time\s+(?:is\s+)?of\s+(?:the\s+)?essence',
        r'milestone(?:s)?',
    ],
    
    'Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)': [
        r'delay(?:s)?',
        r'force\s+majeure',
        r'act(?:s)?\s+of\s+god',
        r'weather\s+(?:delay|condition)',
        r'owner[\s-]caused\s+delay',
        r'unforeseen\s+(?:event|condition|circumstance)',
        r'excusable\s+delay',
        r'compensable\s+delay',
        r'concurrent\s+delay',
        r'time\s+extension',
    ],
    
    'Suspension of Work, Work Stoppages & Agency Directives': [
        r'suspension\s+of\s+work',
        r'work\s+stoppage',
        r'stop\s+work\s+order',
        r'agency\s+directive',
        r'suspend(?:ed)?\s+(?:work|operations)',
        r'temporary\s+(?:suspension|stoppage)',
        r'directed\s+(?:suspension|stoppage)',
    ],
    
    'Submittals, Documentation & Approval Requirements': [
        r'submittal(?:s)?',
        r'shop\s+drawing(?:s)?',
        r'approval\s+(?:requirement|process)',
        r'documentation\s+requirement(?:s)?',
        r'submission\s+(?:requirement|deadline)',
        r'review\s+and\s+approval',
        r'product\s+data',
        r'sample(?:s)?',
        r'as[\s-]built(?:s)?',
    ],
    
    'Emergency & Contingency Work Obligations': [
        r'emergency\s+(?:work|response|services)',
        r'contingency\s+(?:work|plan)',
        r'urgent\s+(?:work|repairs)',
        r'emergency\s+(?:repairs?|situations?)',
        r'unforeseen\s+(?:work|conditions)',
        r'emergency\s+(?:response|procedures)',
    ],
    
    'Permits, Licensing & Regulatory Approvals for Work': [
        r'permit(?:s)?',
        r'licensing',
        r'regulatory\s+approval(?:s)?',
        r'building\s+permit',
        r'construction\s+permit',
        r'environmental\s+permit',
        r'permit\s+(?:requirement|application)',
        r'governmental\s+approval',
        r'agency\s+approval',
    ],
    
    'Warranty, Guarantee & Defects Liability Periods': [
        r'warrant(?:y|ies)',
        r'guarantee(?:s)?',
        r'defects?\s+liability',
        r'warranty\s+period',
        r'guarantee\s+period',
        r'correction\s+(?:of\s+)?(?:work|defects)',
        r'latent\s+defect(?:s)?',
        r'workmanship\s+(?:warranty|guarantee)',
        r'material(?:s)?\s+(?:warranty|guarantee)',
    ],
    
    'Use of APS Tools, Equipment, Materials or Supplies': [
        r'APS\s+(?:tools?|equipment|materials?|supplies)',
        r'owner[\s-](?:furnished|provided|supplied)',
        r'government[\s-](?:furnished|provided|supplied)',
        r'agency[\s-](?:furnished|provided|supplied)',
        r'furnished\s+(?:equipment|materials?|supplies)',
        r'provided\s+(?:equipment|materials?|supplies)',
    ],
    
    'Owner-Supplied Support, Utilities & Site Access Provisions': [
        r'owner[\s-]supplied',
        r'site\s+access',
        r'utilities?\s+(?:provision|access)',
        r'owner[\s-]provided\s+(?:support|utilities)',
        r'access\s+to\s+(?:site|premises|property)',
        r'right\s+of\s+(?:entry|access)',
        r'temporary\s+(?:utilities|facilities)',
    ],
    
    'Field Ticket, Daily Work Log & Documentation Requirements': [
        r'field\s+ticket(?:s)?',
        r'daily\s+(?:work\s+)?log(?:s)?',
        r'daily\s+report(?:s)?',
        r'work\s+(?:log|diary)',
        r'job\s+(?:log|diary)',
        r'documentation\s+(?:of\s+)?(?:work|progress)',
        r'time\s+(?:and\s+)?material(?:s)?\s+(?:ticket|record)',
        r'T&M\s+(?:ticket|record)',
    ],
    
    'Mobilization & Demobilization Provisions': [
        r'mobilization',
        r'demobilization',
        r'mob(?:ilization)?\s+(?:and|&)\s+demob(?:ilization)?',
        r'site\s+(?:setup|establishment)',
        r'project\s+(?:startup|closeout)',
        r'equipment\s+(?:mobilization|demobilization)',
    ],
    
    'Utility Coordination, Locate Risk & Conflict Avoidance': [
        r'utility\s+coordination',
        r'utility\s+locate',
        r'conflict\s+avoidance',
        r'underground\s+(?:utilities?|facilities)',
        r'utility\s+(?:conflict|relocation)',
        r'one[\s-]call',
        r'811',
        r'utility\s+(?:damage|strike)',
        r'locate\s+(?:risk|responsibility)',
    ],
    
    'Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards': [
        r'delivery\s+deadline(?:s)?',
        r'milestone\s+(?:date|deadline)',
        r'substantial\s+completion',
        r'final\s+completion',
        r'completion\s+(?:standard|criteria)',
        r'beneficial\s+(?:use|occupancy)',
        r'ready\s+for\s+(?:use|occupancy)',
        r'certificate\s+of\s+(?:substantial\s+)?completion',
    ],
    
    'Punch List, Closeout Procedures & Acceptance of Work': [
        r'punch\s+list',
        r'closeout\s+(?:procedure|requirement)',
        r'acceptance\s+of\s+work',
        r'final\s+(?:inspection|acceptance)',
        r'project\s+closeout',
        r'deficiency\s+list',
        r'completion\s+(?:list|items)',
        r'final\s+(?:walkthrough|walk[\s-]through)',
    ],
    
    'Worksite Coordination, Access Restrictions & Sequencing Obligations': [
        r'worksite\s+coordination',
        r'access\s+restriction(?:s)?',
        r'sequencing\s+(?:obligation|requirement)',
        r'work\s+(?:area|zone)\s+(?:restriction|limitation)',
        r'coordination\s+(?:with|of)\s+(?:other\s+)?contractor(?:s)?',
        r'phasing',
        r'staging',
        r'work\s+sequence',
    ],
    
    'Deliverables, Digital Submissions & Documentation Standards': [
        r'deliverable(?:s)?',
        r'digital\s+submission(?:s)?',
        r'documentation\s+standard(?:s)?',
        r'electronic\s+(?:submission|deliverable)',
        r'file\s+format(?:s)?',
        r'submission\s+(?:format|standard)',
        r'BIM',
        r'CAD',
        r'digital\s+(?:file|document)',
    ],
    
    # =========================================================================
    # Section IV: Legal Risk & Enforcement (13 categories)
    # =========================================================================
    
    'Indemnification, Defense & Hold Harmless Provisions': [
        r'indemnif(?:y|ication)',
        r'hold\s+harmless',
        r'defend\s+(?:and\s+)?(?:indemnify|hold)',
        r'defense\s+(?:and\s+)?indemnification',
        r'save\s+harmless',
        r'indemnity\s+(?:provision|clause|obligation)',
    ],
    
    'Duty to Defend vs. Indemnify Scope Clarifications': [
        r'duty\s+to\s+defend',
        r'defense\s+(?:obligation|duty)',
        r'indemnify\s+(?:vs\.?|versus)\s+defend',
        r'scope\s+of\s+(?:defense|indemnification)',
        r'defense\s+(?:cost|expense)',
        r'tender\s+(?:of\s+)?defense',
    ],
    
    'Limitations of Liability, Damage Caps & Waivers of Consequential Damages': [
        r'limitation(?:s)?\s+of\s+liability',
        r'damage\s+cap(?:s)?',
        r'liability\s+(?:cap|limit)',
        r'waiver\s+of\s+consequential\s+damage(?:s)?',
        r'consequential\s+damage(?:s)?',
        r'special\s+damage(?:s)?',
        r'incidental\s+damage(?:s)?',
        r'punitive\s+damage(?:s)?',
        r'liquidated\s+damage(?:s)?',
    ],
    
    'Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses': [
        r'insurance\s+coverage',
        r'additional\s+insured',
        r'waiver\s+of\s+subrogation',
        r'certificate\s+of\s+insurance',
        r'insurance\s+(?:requirement|provision)',
        r'general\s+liability\s+insurance',
        r'professional\s+liability',
        r'workers?\s+compensation\s+insurance',
        r'auto(?:mobile)?\s+(?:liability\s+)?insurance',
    ],
    
    'Dispute Resolution (Mediation, Arbitration, Litigation)': [
        r'dispute\s+resolution',
        r'mediation',
        r'arbitration',
        r'litigation',
        r'governing\s+law',
        r'choice\s+of\s+(?:law|forum)',
        r'venue',
        r'jurisdiction',
        r'alternative\s+dispute\s+resolution',
        r'ADR',
    ],
    
    'Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)': [
        r'flow[\s-]down',
        r'pass[\s-]through',
        r'prime[\s-]to[\s-]sub(?:contract)?',
        r'subcontract\s+(?:requirement|provision)',
        r'incorporate(?:d)?\s+(?:by\s+)?reference',
        r'binding\s+(?:on|upon)\s+subcontractor',
    ],
    
    'Subcontracting Restrictions, Approval & Substitution Requirements': [
        r'subcontract(?:ing)?\s+(?:restriction|approval|requirement)',
        r'subcontractor\s+(?:approval|substitution)',
        r'consent\s+to\s+subcontract',
        r'approved\s+subcontractor',
        r'subcontractor\s+list',
        r'substitution\s+(?:of\s+)?subcontractor',
        r'key\s+(?:personnel|subcontractor)',
    ],
    
    'Background Screening, Security Clearance & Worker Eligibility Requirements': [
        r'background\s+(?:check|screening)',
        r'security\s+clearance',
        r'worker\s+eligibility',
        r'criminal\s+(?:background|history)',
        r'drug\s+(?:test|screening)',
        r'employment\s+(?:verification|eligibility)',
        r'badging',
        r'access\s+(?:badge|credential)',
    ],
    
    'Safety Standards, OSHA Compliance & Site-Specific Safety Obligations': [
        r'safety\s+(?:standard|requirement|plan)',
        r'OSHA\s+(?:compliance|requirement)',
        r'site[\s-]specific\s+safety',
        r'safety\s+(?:program|plan)',
        r'accident\s+prevention',
        r'safety\s+(?:training|orientation)',
        r'PPE',
        r'personal\s+protective\s+equipment',
        r'job\s+hazard\s+analysis',
    ],
    
    'Site Conditions, Differing Site Conditions & Changed Circumstances Clauses': [
        r'site\s+condition(?:s)?',
        r'differing\s+site\s+condition(?:s)?',
        r'changed\s+(?:condition|circumstance)',
        r'unforeseen\s+(?:site\s+)?condition(?:s)?',
        r'subsurface\s+condition(?:s)?',
        r'concealed\s+condition(?:s)?',
        r'latent\s+(?:site\s+)?condition(?:s)?',
        r'Type\s+(?:I|II|1|2)\s+(?:differing\s+)?(?:site\s+)?condition',
    ],
    
    'Environmental Hazards, Waste Disposal & Hazardous Materials Provisions': [
        r'environmental\s+(?:hazard|requirement)',
        r'waste\s+disposal',
        r'hazardous\s+(?:material|waste|substance)',
        r'asbestos',
        r'lead[\s-]based\s+paint',
        r'contaminated\s+(?:soil|material)',
        r'environmental\s+(?:compliance|remediation)',
        r'HAZMAT',
        r'toxic\s+(?:material|substance)',
    ],
    
    'Conflicting Documents / Order of Precedence Clauses': [
        r'conflicting\s+document(?:s)?',
        r'order\s+of\s+precedence',
        r'precedence\s+(?:of\s+)?document(?:s)?',
        r'conflict(?:ing)?\s+(?:provision|term)',
        r'inconsistenc(?:y|ies)',
        r'hierarchy\s+of\s+document(?:s)?',
        r'controlling\s+document',
    ],
    
    "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)": [
        r'setoff',
        r'set[\s-]off',
        r'withholding\s+(?:right|payment)',
        r'right\s+to\s+(?:deduct|withhold)',
        r'deduction(?:s)?',
        r'offset',
        r'back[\s-]charge',
        r'backcharge',
        r'owner(?:\'s)?\s+(?:right\s+to\s+)?(?:deduct|withhold)',
    ],
    
    # =========================================================================
    # Section V: Regulatory & Compliance Terms (8 categories)
    # =========================================================================
    
    'Certified Payroll, Recordkeeping & Reporting Obligations': [
        r'certified\s+payroll',
        r'payroll\s+(?:record|report)',
        r'wage\s+(?:record|report)',
        r'labor\s+(?:compliance|reporting)',
        r'weekly\s+payroll',
        r'payroll\s+certification',
        r'labor\s+(?:record|documentation)',
    ],
    
    'Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance': [
        r'prevailing\s+wage',
        r'Davis[\s-]Bacon',
        r'federal\s+wage',
        r'state\s+wage',
        r'wage\s+(?:determination|rate)',
        r'minimum\s+wage',
        r'wage\s+compliance',
        r'labor\s+standard(?:s)?',
        r'Service\s+Contract\s+Act',
    ],
    
    'EEO, Non-Discrimination, MWBE/DBE Participation Requirements': [
        r'EEO',
        r'equal\s+(?:employment\s+)?opportunity',
        r'non[\s-]discrimination',
        r'MWBE',
        r'DBE',
        r'MBE',
        r'WBE',
        r'minority\s+(?:business|participation)',
        r'disadvantaged\s+business',
        r'small\s+business',
        r'diversity\s+(?:requirement|goal)',
        r'affirmative\s+action',
    ],
    
    'Anti-Lobbying / Cone of Silence Provisions': [
        r'anti[\s-]lobbying',
        r'cone\s+of\s+silence',
        r'lobbying\s+(?:restriction|prohibition)',
        r'no[\s-]contact',
        r'communication\s+(?:restriction|prohibition)',
        r'procurement\s+integrity',
        r'blackout\s+period',
    ],
    
    'Apprenticeship, Training & Workforce Development Requirements': [
        r'apprenticeship',
        r'apprentice\s+(?:requirement|ratio)',
        r'training\s+(?:requirement|program)',
        r'workforce\s+development',
        r'on[\s-]the[\s-]job\s+training',
        r'OJT',
        r'journeyman[\s-]to[\s-]apprentice',
        r'skilled\s+labor',
    ],
    
    'Immigration / E-Verify Compliance Obligations': [
        r'immigration',
        r'E[\s-]Verify',
        r'I[\s-]9',
        r'work\s+authorization',
        r'employment\s+eligibility\s+verification',
        r'legal\s+(?:work\s+)?status',
        r'immigration\s+(?:compliance|status)',
    ],
    
    'Worker Classification & Independent Contractor Restrictions': [
        r'worker\s+classification',
        r'independent\s+contractor',
        r'employee\s+(?:vs\.?|versus)\s+(?:independent\s+)?contractor',
        r'misclassification',
        r'1099',
        r'W[\s-]2',
        r'employment\s+(?:status|classification)',
    ],
    
    'Drug-Free Workplace Programs & Substance Testing Requirements': [
        r'drug[\s-]free\s+workplace',
        r'substance\s+(?:test|abuse)',
        r'drug\s+(?:test|screening)',
        r'alcohol\s+(?:test|policy)',
        r'controlled\s+substance',
        r'drug\s+(?:policy|program)',
        r'random\s+(?:drug\s+)?testing',
    ],
    
    # =========================================================================
    # Section VI: Data, Technology & Deliverables (7 categories)
    # =========================================================================
    
    'Data Ownership, Access & Rights to Digital Deliverables': [
        r'data\s+ownership',
        r'data\s+(?:access|rights)',
        r'digital\s+deliverable(?:s)?',
        r'ownership\s+of\s+(?:data|information)',
        r'rights\s+(?:to|in)\s+(?:data|deliverables)',
        r'data\s+(?:license|licensing)',
        r'proprietary\s+(?:data|information)',
    ],
    
    'AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)': [
        r'AI\s+(?:use|restriction)',
        r'artificial\s+intelligence',
        r'automation\s+(?:restriction|requirement)',
        r'digital\s+tool(?:s)?',
        r'proprietary\s+(?:system|software|tool)',
        r'technology\s+(?:use|restriction)',
        r'machine\s+learning',
        r'automated\s+(?:system|process)',
    ],
    
    'Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements': [
        r'digital\s+surveillance',
        r'GIS[\s-]tagged',
        r'monitoring\s+(?:requirement|system)',
        r'GPS\s+(?:tracking|monitoring)',
        r'geolocation',
        r'location\s+(?:tracking|data)',
        r'surveillance\s+(?:system|requirement)',
        r'telematics',
    ],
    
    'GIS, Digital Workflow Integration & Electronic Submittals': [
        r'GIS',
        r'geographic\s+information\s+system',
        r'digital\s+workflow',
        r'electronic\s+submittal(?:s)?',
        r'e[\s-]submittal(?:s)?',
        r'digital\s+(?:integration|platform)',
        r'workflow\s+(?:integration|system)',
        r'project\s+management\s+(?:system|software)',
    ],
    
    'Confidentiality, Data Security & Records Retention Obligations': [
        r'confidentiality',
        r'confidential\s+(?:information|data)',
        r'data\s+security',
        r'records?\s+retention',
        r'non[\s-]disclosure',
        r'NDA',
        r'proprietary\s+information',
        r'trade\s+secret(?:s)?',
        r'sensitive\s+(?:information|data)',
    ],
    
    'Intellectual Property, Licensing & Ownership of Work Product': [
        r'intellectual\s+property',
        r'IP\s+(?:rights|ownership)',
        r'licensing',
        r'ownership\s+of\s+work\s+product',
        r'copyright',
        r'patent',
        r'trademark',
        r'work\s+(?:product|for\s+hire)',
        r'license\s+(?:grant|rights)',
        r'proprietary\s+rights',
    ],
    
    'Cybersecurity Standards, Breach Notification & IT System Use Policies': [
        r'cybersecurity',
        r'cyber\s+security',
        r'breach\s+notification',
        r'IT\s+(?:system|security|policy)',
        r'information\s+security',
        r'data\s+breach',
        r'security\s+(?:incident|breach)',
        r'network\s+security',
        r'system\s+(?:access|security)',
        r'NIST',
        r'SOC\s+2',
    ],
}


# =============================================================================
# Mapping from schema category names to Python-friendly keys (snake_case)
# =============================================================================

SCHEMA_CATEGORY_TO_KEY: Dict[str, str] = {
    # Administrative & Commercial Terms
    'Contract Term, Renewal & Extensions': 'contract_term_renewal_extensions',
    'Bonding, Surety, & Insurance Obligations': 'bonding_surety_insurance',
    'Retainage, Progress Payments & Final Payment Terms': 'retainage_progress_payments',
    'Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies': 'pay_when_paid',
    'Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)': 'price_escalation',
    'Fuel Price Adjustment / Fuel Cost Caps': 'fuel_price_adjustment',
    'Change Orders, Scope Adjustments & Modifications': 'change_orders',
    'Termination for Convenience (Owner/Agency Right to Terminate Without Cause)': 'termination_for_convenience',
    'Termination for Cause / Default by Contractor': 'termination_for_cause',
    'Bid Protest Procedures & Claims of Improper Award': 'bid_protest_procedures',
    'Bid Tabulation, Competition & Award Process Requirements': 'bid_tabulation',
    'Contractor Qualification, Licensing & Certification Requirements': 'contractor_qualification',
    'Release Orders, Task Orders & Work Authorization Protocols': 'release_orders',
    'Assignment & Novation Restrictions (Transfer of Contract Rights)': 'assignment_novation',
    'Audit Rights, Recordkeeping & Document Retention Obligations': 'audit_rights',
    'Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)': 'notice_requirements',
    # Technical & Performance Terms
    'Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)': 'scope_of_work',
    'Performance Schedule, Time for Completion & Critical Path Obligations': 'performance_schedule',
    'Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)': 'delays',
    'Suspension of Work, Work Stoppages & Agency Directives': 'suspension_of_work',
    'Submittals, Documentation & Approval Requirements': 'submittals',
    'Emergency & Contingency Work Obligations': 'emergency_work',
    'Permits, Licensing & Regulatory Approvals for Work': 'permits',
    'Warranty, Guarantee & Defects Liability Periods': 'warranty',
    'Use of APS Tools, Equipment, Materials or Supplies': 'aps_tools',
    'Owner-Supplied Support, Utilities & Site Access Provisions': 'owner_supplied_support',
    'Field Ticket, Daily Work Log & Documentation Requirements': 'field_ticket',
    'Mobilization & Demobilization Provisions': 'mobilization',
    'Utility Coordination, Locate Risk & Conflict Avoidance': 'utility_coordination',
    'Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards': 'delivery_deadlines',
    'Punch List, Closeout Procedures & Acceptance of Work': 'punch_list',
    'Worksite Coordination, Access Restrictions & Sequencing Obligations': 'worksite_coordination',
    'Deliverables, Digital Submissions & Documentation Standards': 'deliverables',
    # Legal Risk & Enforcement
    'Indemnification, Defense & Hold Harmless Provisions': 'indemnification',
    'Duty to Defend vs. Indemnify Scope Clarifications': 'duty_to_defend',
    'Limitations of Liability, Damage Caps & Waivers of Consequential Damages': 'limitations_of_liability',
    'Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses': 'insurance_coverage',
    'Dispute Resolution (Mediation, Arbitration, Litigation)': 'dispute_resolution',
    'Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)': 'flow_down_clauses',
    'Subcontracting Restrictions, Approval & Substitution Requirements': 'subcontracting_restrictions',
    'Background Screening, Security Clearance & Worker Eligibility Requirements': 'background_screening',
    'Safety Standards, OSHA Compliance & Site-Specific Safety Obligations': 'safety_standards',
    'Site Conditions, Differing Site Conditions & Changed Circumstances Clauses': 'site_conditions',
    'Environmental Hazards, Waste Disposal & Hazardous Materials Provisions': 'environmental_hazards',
    'Conflicting Documents / Order of Precedence Clauses': 'conflicting_documents',
    "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)": 'setoff_withholding',
    # Regulatory & Compliance Terms
    'Certified Payroll, Recordkeeping & Reporting Obligations': 'certified_payroll',
    'Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance': 'prevailing_wage',
    'EEO, Non-Discrimination, MWBE/DBE Participation Requirements': 'eeo_non_discrimination',
    'Anti-Lobbying / Cone of Silence Provisions': 'anti_lobbying',
    'Apprenticeship, Training & Workforce Development Requirements': 'apprenticeship',
    'Immigration / E-Verify Compliance Obligations': 'immigration_everify',
    'Worker Classification & Independent Contractor Restrictions': 'worker_classification',
    'Drug-Free Workplace Programs & Substance Testing Requirements': 'drug_free_workplace',
    # Data, Technology & Deliverables
    'Data Ownership, Access & Rights to Digital Deliverables': 'data_ownership',
    'AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)': 'ai_technology_use',
    'Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements': 'digital_surveillance',
    'GIS, Digital Workflow Integration & Electronic Submittals': 'gis_digital_workflow',
    'Confidentiality, Data Security & Records Retention Obligations': 'confidentiality',
    'Intellectual Property, Licensing & Ownership of Work Product': 'intellectual_property',
    'Cybersecurity Standards, Breach Notification & IT System Use Policies': 'cybersecurity',
}

# Reverse mapping: Python key to schema category name
KEY_TO_SCHEMA_CATEGORY: Dict[str, str] = {v: k for k, v in SCHEMA_CATEGORY_TO_KEY.items()}


# =============================================================================
# Section groupings for organized extraction
# =============================================================================

SECTION_GROUPINGS: Dict[str, List[str]] = {
    'administrative_and_commercial_terms': [
        'Contract Term, Renewal & Extensions',
        'Bonding, Surety, & Insurance Obligations',
        'Retainage, Progress Payments & Final Payment Terms',
        'Pay-When-Paid, Pay-If-Paid, or Owner Payment Contingencies',
        'Price Escalation Clauses (Labor, Materials, Fuel, Inflation Adjustments)',
        'Fuel Price Adjustment / Fuel Cost Caps',
        'Change Orders, Scope Adjustments & Modifications',
        'Termination for Convenience (Owner/Agency Right to Terminate Without Cause)',
        'Termination for Cause / Default by Contractor',
        'Bid Protest Procedures & Claims of Improper Award',
        'Bid Tabulation, Competition & Award Process Requirements',
        'Contractor Qualification, Licensing & Certification Requirements',
        'Release Orders, Task Orders & Work Authorization Protocols',
        'Assignment & Novation Restrictions (Transfer of Contract Rights)',
        'Audit Rights, Recordkeeping & Document Retention Obligations',
        'Notice Requirements & Claim Timeframes (Notice to Cure, Delay Notices, Termination Notices, etc.)',
    ],
    'technical_and_performance_terms': [
        'Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)',
        'Performance Schedule, Time for Completion & Critical Path Obligations',
        'Delays of Any Kind (Force Majeure, Acts of God, Weather, Owner-Caused, Unforeseen Events)',
        'Suspension of Work, Work Stoppages & Agency Directives',
        'Submittals, Documentation & Approval Requirements',
        'Emergency & Contingency Work Obligations',
        'Permits, Licensing & Regulatory Approvals for Work',
        'Warranty, Guarantee & Defects Liability Periods',
        'Use of APS Tools, Equipment, Materials or Supplies',
        'Owner-Supplied Support, Utilities & Site Access Provisions',
        'Field Ticket, Daily Work Log & Documentation Requirements',
        'Mobilization & Demobilization Provisions',
        'Utility Coordination, Locate Risk & Conflict Avoidance',
        'Delivery Deadlines, Milestone Dates, Substantial & Final Completion Standards',
        'Punch List, Closeout Procedures & Acceptance of Work',
        'Worksite Coordination, Access Restrictions & Sequencing Obligations',
        'Deliverables, Digital Submissions & Documentation Standards',
    ],
    'legal_risk_and_enforcement': [
        'Indemnification, Defense & Hold Harmless Provisions',
        'Duty to Defend vs. Indemnify Scope Clarifications',
        'Limitations of Liability, Damage Caps & Waivers of Consequential Damages',
        'Insurance Coverage, Additional Insured & Waiver of Subrogation Clauses',
        'Dispute Resolution (Mediation, Arbitration, Litigation)',
        'Flow-Down Clauses (Prime-to-Subcontract Risk Pass-Through)',
        'Subcontracting Restrictions, Approval & Substitution Requirements',
        'Background Screening, Security Clearance & Worker Eligibility Requirements',
        'Safety Standards, OSHA Compliance & Site-Specific Safety Obligations',
        'Site Conditions, Differing Site Conditions & Changed Circumstances Clauses',
        'Environmental Hazards, Waste Disposal & Hazardous Materials Provisions',
        'Conflicting Documents / Order of Precedence Clauses',
        "Setoff & Withholding Rights (Owner's Right to Deduct or Withhold Payment)",
    ],
    'regulatory_and_compliance_terms': [
        'Certified Payroll, Recordkeeping & Reporting Obligations',
        'Prevailing Wage, Davis-Bacon & Federal/State Wage Compliance',
        'EEO, Non-Discrimination, MWBE/DBE Participation Requirements',
        'Anti-Lobbying / Cone of Silence Provisions',
        'Apprenticeship, Training & Workforce Development Requirements',
        'Immigration / E-Verify Compliance Obligations',
        'Worker Classification & Independent Contractor Restrictions',
        'Drug-Free Workplace Programs & Substance Testing Requirements',
    ],
    'data_technology_and_deliverables': [
        'Data Ownership, Access & Rights to Digital Deliverables',
        'AI / Technology Use Restrictions (Automation, Digital Tools, Proprietary Systems)',
        'Digital Surveillance, GIS-Tagged Deliverables & Monitoring Requirements',
        'GIS, Digital Workflow Integration & Electronic Submittals',
        'Confidentiality, Data Security & Records Retention Obligations',
        'Intellectual Property, Licensing & Ownership of Work Product',
        'Cybersecurity Standards, Breach Notification & IT System Use Policies',
    ],
}



def extract_section_context(text: str, start_pos: int, context_chars: int = 2000) -> str:
    """
    Extract text around a found pattern with context.
    
    Args:
        text: Full contract text
        start_pos: Position where pattern was found
        context_chars: Number of characters to include before and after
    
    Returns:
        Text snippet with context
    """
    start = max(0, start_pos - context_chars)
    end = min(len(text), start_pos + context_chars)
    return text[start:end]


def find_section_by_patterns(text: str, patterns: List[str]) -> List[Tuple[int, str]]:
    """
    Find all occurrences of patterns in text.
    
    Args:
        text: Contract text to search
        patterns: List of regex patterns
    
    Returns:
        List of (position, matched_text) tuples
    """
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            matches.append((match.start(), match.group()))
    return matches


def extract_relevant_sections(contract_text: str, max_chars: int = 100000) -> Dict[str, str]:
    """
    Extract relevant sections from contract using pattern matching.
    
    Args:
        contract_text: Full contract text
        max_chars: Maximum characters to extract (to stay within token limits)
    
    Returns:
        Dictionary mapping section names to extracted text
    """
    sections = {}
    total_chars = 0
    
    # Track which parts of the contract we've already extracted
    extracted_ranges = []
    
    for section_name, patterns in SECTION_PATTERNS.items():
        matches = find_section_by_patterns(contract_text, patterns)
        
        if matches:
            # Get context around each match
            section_texts = []
            for pos, matched_text in matches:
                # Check if we've already extracted this area
                already_extracted = False
                for start, end in extracted_ranges:
                    if start <= pos <= end:
                        already_extracted = True
                        break
                
                if not already_extracted:
                    context = extract_section_context(contract_text, pos, context_chars=1500)
                    section_texts.append(context)
                    
                    # Mark this range as extracted
                    context_start = max(0, pos - 1500)
                    context_end = min(len(contract_text), pos + 1500)
                    extracted_ranges.append((context_start, context_end))
                    
                    total_chars += len(context)
                    
                    # Stop if we've extracted enough
                    if total_chars >= max_chars:
                        break
            
            if section_texts:
                sections[section_name] = '\n\n---\n\n'.join(section_texts)
        
        if total_chars >= max_chars:
            break
    
    return sections



def extract_comprehensive_sections(
    contract_text: str, 
    max_chars: int = 100000
) -> Dict[str, Dict[str, str]]:
    """
    Extract sections using comprehensive patterns organized by schema sections.
    
    Args:
        contract_text: Full contract text
        max_chars: Maximum characters to extract
    
    Returns:
        Dictionary mapping schema section names to dictionaries of category->text
    """
    result: Dict[str, Dict[str, str]] = {}
    total_chars = 0
    extracted_ranges: List[Tuple[int, int]] = []
    
    for section_name, categories in SECTION_GROUPINGS.items():
        result[section_name] = {}
        
        for category in categories:
            if category not in COMPREHENSIVE_SECTION_PATTERNS:
                continue
                
            patterns = COMPREHENSIVE_SECTION_PATTERNS[category]
            matches = find_section_by_patterns(contract_text, patterns)
            
            if matches:
                section_texts = []
                for pos, matched_text in matches:
                    # Check if already extracted
                    already_extracted = any(
                        start <= pos <= end for start, end in extracted_ranges
                    )
                    
                    if not already_extracted:
                        context = extract_section_context(contract_text, pos, context_chars=1500)
                        section_texts.append(context)
                        
                        context_start = max(0, pos - 1500)
                        context_end = min(len(contract_text), pos + 1500)
                        extracted_ranges.append((context_start, context_end))
                        
                        total_chars += len(context)
                        
                        if total_chars >= max_chars:
                            break
                
                if section_texts:
                    result[section_name][category] = '\n\n---\n\n'.join(section_texts)
            
            if total_chars >= max_chars:
                break
        
        if total_chars >= max_chars:
            break
    
    return result


def get_patterns_for_category(category_name: str) -> Optional[List[str]]:
    """
    Get regex patterns for a specific clause category.
    
    Args:
        category_name: The schema category name (e.g., 'Contract Term, Renewal & Extensions')
    
    Returns:
        List of regex patterns or None if category not found
    """
    return COMPREHENSIVE_SECTION_PATTERNS.get(category_name)


def get_all_category_names() -> List[str]:
    """
    Get all clause category names from the comprehensive patterns.
    
    Returns:
        List of all category names
    """
    return list(COMPREHENSIVE_SECTION_PATTERNS.keys())


def get_categories_for_section(section_name: str) -> List[str]:
    """
    Get all category names for a specific schema section.
    
    Args:
        section_name: The schema section name (e.g., 'administrative_and_commercial_terms')
    
    Returns:
        List of category names in that section
    """
    return SECTION_GROUPINGS.get(section_name, [])



def extract_key_information(contract_text: str) -> Dict[str, any]:
    """
    Extract key information using regex patterns.
    
    Args:
        contract_text: Full contract text
    
    Returns:
        Dictionary with extracted information
    """
    info = {}
    
    # Extract dates
    date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
    dates = re.findall(date_pattern, contract_text, re.IGNORECASE)
    if dates:
        info['dates_found'] = dates[:5]  # First 5 dates
    
    # Extract dollar amounts
    money_pattern = r'\$[\d,]+(?:\.\d{2})?'
    amounts = re.findall(money_pattern, contract_text)
    if amounts:
        info['amounts_found'] = amounts[:10]  # First 10 amounts
    
    # Extract percentages
    percent_pattern = r'\b\d+(?:\.\d+)?%'
    percentages = re.findall(percent_pattern, contract_text)
    if percentages:
        info['percentages_found'] = percentages[:10]
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, contract_text)
    if emails:
        info['emails_found'] = emails
    
    # Extract phone numbers
    phone_pattern = r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, contract_text)
    if phones:
        info['phones_found'] = phones
    
    return info


def create_focused_contract(contract_text: str, max_chars: int = 100000) -> Tuple[str, Dict]:
    """
    Create a focused version of the contract with only relevant sections.
    
    Args:
        contract_text: Full contract text
        max_chars: Maximum characters for focused version
    
    Returns:
        Tuple of (focused_text, metadata)
    """
    # Extract relevant sections
    sections = extract_relevant_sections(contract_text, max_chars)
    
    # Extract key information
    key_info = extract_key_information(contract_text)
    
    # Build focused contract text
    focused_parts = []
    
    # Add a summary header
    focused_parts.append("=== EXTRACTED RELEVANT SECTIONS ===\n")
    
    # Add each section
    for section_name, section_text in sections.items():
        focused_parts.append(f"\n=== {section_name.upper().replace('_', ' ')} ===\n")
        focused_parts.append(section_text)
    
    focused_text = '\n'.join(focused_parts)
    
    # Create metadata
    metadata = {
        'original_length': len(contract_text),
        'focused_length': len(focused_text),
        'reduction_percent': round((1 - len(focused_text) / len(contract_text)) * 100, 1),
        'sections_extracted': list(sections.keys()),
        'key_info': key_info
    }
    
    return focused_text, metadata



def create_comprehensive_focused_contract(
    contract_text: str, 
    max_chars: int = 100000
) -> Tuple[str, Dict]:
    """
    Create a focused version of the contract organized by schema sections.
    
    Args:
        contract_text: Full contract text
        max_chars: Maximum characters for focused version
    
    Returns:
        Tuple of (focused_text, metadata)
    """
    # Extract sections using comprehensive patterns
    sections = extract_comprehensive_sections(contract_text, max_chars)
    
    # Extract key information
    key_info = extract_key_information(contract_text)
    
    # Build focused contract text
    focused_parts = []
    focused_parts.append("=== EXTRACTED RELEVANT SECTIONS (COMPREHENSIVE) ===\n")
    
    categories_found = []
    
    for section_name, categories in sections.items():
        if categories:
            focused_parts.append(f"\n=== {section_name.upper().replace('_', ' ')} ===\n")
            for category, text in categories.items():
                focused_parts.append(f"\n--- {category} ---\n")
                focused_parts.append(text)
                categories_found.append(category)
    
    focused_text = '\n'.join(focused_parts)
    
    # Create metadata
    metadata = {
        'original_length': len(contract_text),
        'focused_length': len(focused_text),
        'reduction_percent': round((1 - len(focused_text) / len(contract_text)) * 100, 1) if len(contract_text) > 0 else 0,
        'sections_extracted': list(sections.keys()),
        'categories_found': categories_found,
        'total_categories': len(categories_found),
        'key_info': key_info
    }
    
    return focused_text, metadata


def should_use_extraction(contract_text: str, token_limit: int = 100000) -> bool:
    """
    Determine if we should use extraction or send full contract.
    
    Args:
        contract_text: Full contract text
        token_limit: Token limit for decision
    
    Returns:
        True if extraction should be used
    """
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = len(contract_text) // 4
    return estimated_tokens > token_limit


# =============================================================================
# ComprehensiveContractExtractor Class
# =============================================================================

class ComprehensiveContractExtractor:
    """
    Extracts sections matching all schema clause categories.
    
    This class provides a structured interface for extracting contract text
    organized by the comprehensive 8-section schema defined in output_schemas_v1.json.
    """
    
    def __init__(self):
        """Initialize the extractor with comprehensive patterns."""
        self._patterns = COMPREHENSIVE_SECTION_PATTERNS
        self._section_groupings = SECTION_GROUPINGS
        self._category_to_key = SCHEMA_CATEGORY_TO_KEY
        self._key_to_category = KEY_TO_SCHEMA_CATEGORY
    
    def extract_for_schema_section(
        self, 
        contract_text: str, 
        section_name: str,
        max_chars_per_category: int = 3000
    ) -> Dict[str, str]:
        """
        Extract text for all clause categories in a specific schema section.
        
        Args:
            contract_text: Full contract text to search
            section_name: Schema section name (e.g., 'administrative_and_commercial_terms')
            max_chars_per_category: Maximum characters to extract per category
        
        Returns:
            Dictionary mapping category names to extracted text.
            Keys are the full schema category names (e.g., 'Contract Term, Renewal & Extensions')
        """
        if section_name not in self._section_groupings:
            return {}
        
        result: Dict[str, str] = {}
        categories = self._section_groupings[section_name]
        
        for category in categories:
            if category not in self._patterns:
                continue
            
            patterns = self._patterns[category]
            matches = find_section_by_patterns(contract_text, patterns)
            
            if matches:
                # Collect text around each match
                section_texts = []
                total_chars = 0
                
                for pos, matched_text in matches:
                    if total_chars >= max_chars_per_category:
                        break
                    
                    context = extract_section_context(
                        contract_text, 
                        pos, 
                        context_chars=min(1500, max_chars_per_category - total_chars)
                    )
                    section_texts.append(context)
                    total_chars += len(context)
                
                if section_texts:
                    result[category] = '\n\n---\n\n'.join(section_texts)
        
        return result
    
    def extract_all_sections(
        self, 
        contract_text: str,
        max_chars: int = 100000
    ) -> Dict[str, Dict[str, str]]:
        """
        Extract text for all schema sections and their categories.
        
        Args:
            contract_text: Full contract text
            max_chars: Maximum total characters to extract
        
        Returns:
            Nested dictionary: section_name -> category_name -> extracted_text
        """
        return extract_comprehensive_sections(contract_text, max_chars)
    
    def create_focused_contract(
        self, 
        contract_text: str, 
        max_chars: int = 100000
    ) -> Tuple[str, Dict]:
        """
        Create focused contract organized by schema sections.
        
        Args:
            contract_text: Full contract text
            max_chars: Maximum characters for focused version
        
        Returns:
            Tuple of (focused_text, metadata)
            - focused_text: Contract text organized by schema sections
            - metadata: Dictionary with extraction statistics including:
                - original_length: Original contract length
                - focused_length: Focused contract length
                - reduction_percent: Percentage reduction
                - sections_extracted: List of section names with content
                - categories_found: List of category names found
                - total_categories: Count of categories found
                - key_info: Extracted key information (dates, amounts, etc.)
        """
        return create_comprehensive_focused_contract(contract_text, max_chars)
    
    def get_category_patterns(self, category_name: str) -> Optional[List[str]]:
        """
        Get regex patterns for a specific clause category.
        
        Args:
            category_name: The schema category name
        
        Returns:
            List of regex patterns or None if category not found
        """
        return self._patterns.get(category_name)
    
    def get_all_categories(self) -> List[str]:
        """
        Get all clause category names.
        
        Returns:
            List of all 61 category names
        """
        return list(self._patterns.keys())
    
    def get_section_categories(self, section_name: str) -> List[str]:
        """
        Get category names for a specific schema section.
        
        Args:
            section_name: Schema section name
        
        Returns:
            List of category names in that section
        """
        return self._section_groupings.get(section_name, [])
    
    def get_section_names(self) -> List[str]:
        """
        Get all schema section names.
        
        Returns:
            List of section names
        """
        return list(self._section_groupings.keys())
    
    def category_to_python_key(self, category_name: str) -> Optional[str]:
        """
        Convert schema category name to Python-friendly key.
        
        Args:
            category_name: Full schema category name
        
        Returns:
            Python key (snake_case) or None if not found
        """
        return self._category_to_key.get(category_name)
    
    def python_key_to_category(self, python_key: str) -> Optional[str]:
        """
        Convert Python key to schema category name.
        
        Args:
            python_key: Python key (snake_case)
        
        Returns:
            Full schema category name or None if not found
        """
        return self._key_to_category.get(python_key)
    
    def extract_category_text(
        self, 
        contract_text: str, 
        category_name: str,
        max_chars: int = 3000
    ) -> Optional[str]:
        """
        Extract text for a single clause category.
        
        Args:
            contract_text: Full contract text
            category_name: Schema category name
            max_chars: Maximum characters to extract
        
        Returns:
            Extracted text or None if category not found
        """
        if category_name not in self._patterns:
            return None
        
        patterns = self._patterns[category_name]
        matches = find_section_by_patterns(contract_text, patterns)
        
        if not matches:
            return None
        
        section_texts = []
        total_chars = 0
        
        for pos, matched_text in matches:
            if total_chars >= max_chars:
                break
            
            context = extract_section_context(
                contract_text, 
                pos, 
                context_chars=min(1500, max_chars - total_chars)
            )
            section_texts.append(context)
            total_chars += len(context)
        
        return '\n\n---\n\n'.join(section_texts) if section_texts else None


# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_contract = """
    CONSTRUCTION CONTRACT
    
    This agreement is made on January 15, 2024 between ABC Construction (Contractor)
    and State DOT (Owner).
    
    PAYMENT TERMS
    The contract price is $5,000,000. Payment shall be made within 30 days of invoice.
    Retainage of 10% will be held until final completion.
    
    SCOPE OF WORK
    Contractor shall perform all work necessary to complete the highway construction
    project as described in the attached specifications.
    
    TERMINATION
    Either party may terminate this agreement with 30 days written notice.
    Owner may terminate for convenience with payment for work performed.
    
    INDEMNIFICATION
    Contractor shall indemnify and hold harmless Owner from all claims arising
    from Contractor's performance of the work.
    """
    
    focused, metadata = create_focused_contract(sample_contract)
    print("Original length:", metadata['original_length'])
    print("Focused length:", metadata['focused_length'])
    print("Reduction:", metadata['reduction_percent'], "%")
    print("\nSections found:", metadata['sections_extracted'])
    print("\nFocused contract:")
    print(focused)
