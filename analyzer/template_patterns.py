"""
Template-to-Regex Pattern Mapping

Maps each of the 60+ template categories to regex patterns that identify
relevant clauses in contract text.
"""

import bisect
import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Template Category Pattern Mappings
# Each category has multiple regex patterns to catch different phrasings

TEMPLATE_PATTERNS = {
    # ===================================================================
    # SECTION II: ADMINISTRATIVE & COMMERCIAL TERMS (16 categories)
    # ===================================================================

    "contract_term_renewal_extensions": [
        r'(?:contract|agreement)\s+(?:term|duration|period)',
        r'(?:term|duration)\s+of\s+(?:this|the)\s+(?:agreement|contract)',
        r'renewal.*?(?:period|option|term)',
        r'extension.*?(?:time|term|period)',
        r'(?:substantial|final)\s+completion.*?within.*?(?:days|months)',
        r'notice\s+to\s+proceed',
        r'(?:calendar|working|business)\s+days.*?completion',
    ],

    "bonding_surety_insurance": [
        r'bond(?:s|ing)?\s+(?:and|&)?\s*(?:insurance|surety)',
        r'performance\s+bond',
        r'payment\s+bond',
        r'bid\s+bond',
        r'surety.*?(?:company|bond)',
        r'insurance.*?(?:requirements?|coverage|certificate)',
        r'additional\s+insured',
        r'waiver\s+of\s+subrogation',
        r'guarantees?\s+(?:and|or)\s+bonds?',
        r'(?:compile|assemble).*?(?:guarantee|bond)',
    ],

    "retainage_progress_payments": [
        r'retainage',
        r'progress\s+payment',
        r'(?:monthly|periodic)\s+payment',
        r'(?:pay|invoice)\s+application',
        r'final\s+payment',
        r'payment.*?(?:schedule|terms|conditions)',
        r'invoice.*?(?:submission|approval)',
        r'(?:final|last)\s+Application\s+for\s+Payment',
        r'APPLICATION\s+FOR\s+(?:FINAL\s+)?PAYMENT',
    ],

    "pay_when_paid_if_paid": [
        r'pay[\-\s]when[\-\s]paid',
        r'pay[\-\s]if[\-\s]paid',
        r'condition\s+precedent.*?payment',
        r'payment.*?(?:contingent|subject\s+to).*?owner',
        r'receipt\s+of\s+payment.*?owner',
        r'payable\s+to\s+the\s+CONTRACTOR.*?provided',
    ],

    "price_escalation": [
        r'price.*?(?:escalation|adjustment|increase)',
        r'adjustment.*?(?:to|of)\s+(?:the\s+)?price',
        r'Producer.*?Price\s+Index|PPI',
        r'(?:labor|material).*?(?:cost|price).*?adjustment',
        r'inflation.*?adjustment',
        r'economic.*?(?:adjustment|price)',
        r'cost.*?index',
        r'(?:appropriate|equitable)\s+adjustment\s+of\s+the\s+contract',
        r'negotiated\s+price',
        r'fuel.*?(?:cost|price|surcharge|adjustment)',
        r'diesel.*?(?:cost|price)',
        r'petroleum.*?cost',
    ],

    "change_orders": [
        r'change\s+order',
        r'modification.*?(?:contract|scope|work)',
        r'scope.*?(?:change|adjustment|modification)',
        r'extra\s+work',
        r'additional\s+work',
        r'contract\s+amendment',
        r'(?:FINAL|final)\s+ADJUSTMENT\s+OF\s+ACCOUNTS',
        r'sole\s+discretion.*?(?:agree|reject)',
    ],

    "termination_for_convenience": [
        r'terminat(?:e|ion).*?(?:for\s+)?convenience',
        r'terminat(?:e|ion).*?(?:without\s+cause|at\s+will)',
        r'(?:owner|agency).*?(?:may|right).*?terminat',
        r'cancel.*?without\s+cause',
    ],

    "termination_for_cause": [
        r'terminat(?:e|ion).*?(?:for\s+)?(?:cause|default)',
        r'terminat(?:e|ion).*?breach',
        r'terminat(?:e|ion).*?(?:failure|violation)',
        r'default.*?(?:contractor|party)',
        r'cure\s+period',
        r'notice\s+of\s+default',
    ],

    "bid_protest": [
        r'bid\s+protest',
        r'protest.*?(?:award|solicitation)',
        r'challenge.*?award',
        r'dispute.*?(?:bid|award)',
        r'(?:No|no)\s+request.*?(?:change|claim).*?(?:Contract|contract)\s+(?:Price|Time)',
        r'shall\s+(?:not\s+be|be)\s+allowed.*?(?:written\s+notice|strict\s+accordance)',
    ],

    "bid_tabulation": [
        r'bid\s+tabulation',
        r'(?:competitive|competitive\s+sealed)\s+bid',
        r'award.*?(?:process|criteria)',
        r'evaluation.*?(?:criteria|factors)',
        r'lowest.*?(?:responsible|responsive).*?bid',
        r'(?:Bid|bid)\s+Schedule',
        r'bid\s+item',
        r'prices?\s+named\s+in\s+the\s+(?:Bid|bid)',
        r'lump\s+sum\s+price\s+named',
        r'(?:Payment|payment)\s+for\s+(?:all\s+)?bid\s+items',
        r'MEASUREMENT\s+AND\s+PAYMENT',
        r'full\s+compensation\s+for\s+(?:the\s+)?(?:complete|total)',
    ],

    "contractor_qualification": [
        r'(?:contractor|bidder)\s+(?:qualification|eligibility)',
        r'(?:contractor|bidder)\s+licens(?:e|ing)',
        r'prequalification',
        r'registered.*?(?:contractor|general\s+contractor)',
        r'(?:experience|qualification)\s+(?:requirements?|criteria)',
    ],

    "release_orders": [
        r'(?:release|task)\s+order',
        r'work\s+(?:order|authorization)\s+(?:form|process|procedure|protocol)',
        r'(?:initial|final|limited)\s+notice\s+to\s+proceed',
        r'indefinite\s+(?:delivery|quantity)',
    ],

    "assignment_novation": [
        r'assignment\s+of\s+(?:this\s+)?(?:contract|agreement|rights)',
        r'novation',
        r'transfer\s+of\s+(?:this\s+)?(?:contract|agreement|rights)',
        r'shall\s+not\s+assign\s+(?:this|the)',
        r'consent.*?(?:to\s+)?(?:assignment|transfer\s+of)',
    ],

    "audit_rights": [
        r'audit\s+(?:rights|access)',
        r'(?:books|records).*?(?:inspection|access|review)',
        r'recordkeeping',
        r'document.*?retention',
        r'right\s+to\s+(?:inspect|audit|examine)',
    ],

    "notice_requirements": [
        r'notice.*?(?:requirement|provision|shall)',
        r'notification.*?(?:period|deadline|timeframe)',
        r'written\s+notice',
        r'notice.*?(?:cure|delay|claim)',
        r'(?:within|not\s+later\s+than).*?\d+\s+days.*?notice',
    ],

    # ===================================================================
    # SECTION III: TECHNICAL & PERFORMANCE TERMS (17 categories)
    # ===================================================================

    "scope_of_work": [
        r'scope\s+of\s+work',
        r'work.*?(?:inclusions?|exclusions?)',
        r'deliverables?',
        r'services\s+to\s+be\s+(?:provided|performed)',
        r'contractor\s+shall.*?(?:provide|perform|furnish)',
    ],

    "performance_schedule": [
        r'(?:performance|project)\s+schedule',
        r'time\s+for\s+completion',
        r'milestone.*?date',
        r'critical\s+path',
        r'schedule\s+(?:requirements|obligations)',
        r'time\s+is\s+of\s+the\s+essence',
        r'(?:WORK|work)\s+(?:SCHEDULE|schedule)',
        r'(?:5|five)[\-\s]+day\s+(?:WORK|work)\s+week',
        r'(?:construction|project)\s+schedule.*?(?:submit|approv|CPM)',
    ],

    "delays": [
        r'delay(?:s|ed)?\s+(?:in|to|of|shall|caused|resulting|due|by|claim)',
        r'(?:excusable|compensable|inexcusable|owner[\-\s]caused)\s+delay',
        r'extension\s+of\s+time',
        r'time\s+extension',
        r'force\s+majeure',
    ],

    "suspension_of_work": [
        r'suspend.*?(?:work|operations)',
        r'suspension.*?(?:work|contract)',
        r'stop\s+work',
        r'work\s+stoppage',
        r'(?:right\s+to\s+)?delay\s+performance',
        r'(?:stopped|delayed)\s+(?:for\s+)?(?:more\s+than\s+)?\d+',
        r'stoppage\s+(?:or|and)\s+delay',
    ],

    "submittals": [
        r'submittal(?:s)?',
        r'shop\s+drawing',
        r'(?:material|product)\s+(?:data|sample)',
        r'approval.*?(?:submittal|drawing)',
        r'(?:contractor|subcontractor)\s+shall\s+submit',
        r'(?:furnish|provide)\s+to\s+the\s+ENGINEER\s+for\s+review',
        r'shop\s+drawing\s+submittals?\s+shall',
        r'SUBMISSION\s+REQUIREMENTS',
    ],

    "emergency_work": [
        r'emergency.*?(?:work|services|response)',
        r'contingency.*?(?:work|provision)',
        r'urgent.*?(?:work|repair)',
    ],

    "permits_licensing": [
        r'(?:building|construction|environmental|work|excavation)\s+permit',
        r'permit(?:s)?\s+(?:required|shall|must|needed|obtained|application)',
        r'licens(?:e|ing)\s+(?:required|shall|must|valid|current)',
        r'regulatory\s+approval',
        r'(?:shall|must|contractor)\s+(?:obtain|secure|procure).*?(?:permit|license|approval)',
    ],

    "warranty": [
        r'warrant(?:y|ies)',
        r'guarantee(?:s|d)?\s+(?:period|work|bond|for\s+)',
        r'(?:compile|assemble).*?guarantee',
        r'defect(?:s)?\s+liability',
        r'warranty\s+period',
        r'(?:one|two|three)\s+year.*?warranty',
        r'correction\s+of\s+(?:defective\s+)?work',
    ],

    "use_of_aps_tools": [
        r'(?:tools|equipment|plant|machinery)\s+(?:provided|furnished|supplied)\s+by\s+(?:owner|city|agency)',
        r'owner[\-\s](?:provided|furnished|supplied)\s+(?:tools|equipment|software)',
        r'(?:use|provision)\s+of\s+(?:owner|city).{0,20}(?:tools|equipment|software)',
        r'(?:specialized|proprietary)\s+(?:tools|software|system)',
    ],

    "owner_supplied_support": [
        r'owner[\-\s](?:furnished|supplied|provided)',
        r'(?:furnished|supplied|provided)\s+by\s+(?:owner|agency|department)',
        r'government[\-\s]furnished',
        r'GFE|GFM|GFP',
        r'owner\s+shall\s+(?:provide|furnish|supply)',
    ],

    "field_ticket": [
        r'field\s+ticket',
        r'daily\s+(?:work|job)\s+(?:log|report|ticket)',
        r'time\s+and\s+material',
        r'T\s*&\s*M\s+(?:work|ticket|basis)',
        r'extra\s+work\s+(?:order|authorization|ticket)',
    ],

    "mobilization_demobilization": [
        r'mobiliz(?:e|ation).*?(?:cost|fee|payment|schedule|site|demobiliz|lump\s+sum|allowance|shall)',
        r'demobiliz(?:e|ation)',
        r'site\s+establishment',
        r'(?:move|moving)\s+(?:in|on|to)\s+(?:site|project)',
        r'setup\s+(?:cost|fee|charge)',
        r'no\s+special\s+measurement\s+or\s+payment',
    ],

    "utility_coordination": [
        r'utility\s+(?:coordination|relocation|conflict|locate)',
        r'underground\s+(?:utility|utilities|facility|facilities)',
        r'(?:locate|mark|identify).*?(?:utility|utilities)',
        r'utility\s+(?:damage|strike|hit)',
        r'one[\-\s]call|811|dig\s+safe',
        r'(?:existence|location)\s+(?:and\s+location\s+)?of\s+utilit(?:y|ies)',
    ],

    "delivery_deadlines": [
        r'milestone\s+(?:date|deadline|schedule)',
        r'delivery\s+(?:date|deadline|schedule)',
        r'completion\s+(?:date|deadline|benchmark)',
        r'substantial\s+completion',
        r'final\s+completion',
        r'(?:interim|intermediate)\s+(?:milestone|deadline)',
    ],

    "punch_list": [
        r'punch\s+list',
        r'(?:final|pre[\-\s]final)\s+inspection',
        r'close[\-\s]out',
        r'acceptance\s+of\s+work',
        r'(?:substantial|final)\s+(?:completion|acceptance)',
        r'deficiency\s+list',
    ],

    "worksite_coordination": [
        r'(?:staging|laydown)\s+area',
        r'site\s+access',
        r'work\s+(?:area|zone|space)',
        r'(?:traffic|lane)\s+(?:control|management)',
        r'(?:work|construction)\s+(?:sequencing|coordination)',
        r'(?:adjacent|concurrent)\s+(?:work|operations|contractor)',
    ],

    "deliverables": [
        r'deliverable(?:s)?',
        r'as[\-\s]built',
        r'record\s+(?:drawing|document)',
        r'(?:project|construction)\s+(?:document|record|file)',
        r'(?:digital|electronic)\s+(?:submission|deliverable|file)',
        r'(?:O&M|operation\s+and\s+maintenance)\s+manual',
    ],

    "emergency_contingency": [
        r'emergency\s+(?:work|response|situation)',
        r'contingency\s+(?:work|plan|operation)',
        r'(?:urgent|immediate)\s+(?:work|action|response)',
    ],

    # ===================================================================
    # SECTION IV: LEGAL RISK & ENFORCEMENT (13 categories)
    # ===================================================================

    "indemnification": [
        r'indemnif(?:y|ication)',
        r'hold\s+harmless',
        r'defend.*?(?:against|from)',
        r'shall.*?(?:indemnify|hold\s+harmless)',
    ],

    "duty_to_defend": [
        r'duty\s+to\s+defend',
        r'defend.*?(?:claims|actions|suits)',
        r'legal\s+defense',
    ],

    "limitation_of_liability": [
        r'limitation.*?(?:liability|damages)',
        r'cap.*?(?:liability|damages)',
        r'(?:shall\s+)?not.*?(?:liable|responsible).*?(?:for|exceed)',
    ],

    "insurance_coverage": [
        r'insurance.*?(?:requirements?|coverage|limits?)',
        r'(?:general|commercial)\s+liability\s+insurance',
        r'workers.*?compensation',
        r'professional\s+liability',
        r'umbrella\s+(?:policy|coverage)',
        r'(?:Certificate|certificate)\s+of\s+Insurance',
        r'(?:Products?\s+and\s+Completed\s+Operations)',
    ],

    "dispute_resolution": [
        r'dispute\s+resolution',
        r'mediation',
        r'arbitration',
        r'(?:governing|choice\s+of)\s+law',
        r'venue',
        r'jurisdiction',
    ],

    "flow_down_clauses": [
        r'flow[\s\-]down',
        r'(?:pass|pass[\s\-]through).*?(?:subcontractor|sub)',
        r'subcontract.*?(?:shall\s+)?include',
        r'applicable.*?(?:terms|provisions).*?subcontract',
    ],

    "subcontracting": [
        r'subcontract(?:or|ing)?',
        r'sub[\-\s](?:contractor|tier)',
        r'(?:approval|consent).*?subcontract',
        r'(?:shall\s+)?not\s+subcontract.*?without',
    ],

    "safety_osha": [
        r'safety.*?(?:requirements?|standards?|program)',
        r'OSHA',
        r'occupational.*?(?:safety|health)',
        r'accident.*?(?:prevention|reporting)',
    ],

    "site_conditions": [
        r'site\s+condition',
        r'differing\s+site\s+condition',
        r'changed\s+condition',
        r'subsurface\s+condition',
        r'unforeseen\s+condition',
        r'(?:subsurface|geotechnical)\s+(?:investigation|exploration)',
        r'excavat(?:e|ing|ion).*?(?:complete|finish)',
        r'(?:field|site)\s+conditions?[\s\S]{0,80}?(?:modif|alter)',
        r'(?:free|unrestricted)\s+access\s+(?:to\s+)?(?:the\s+)?(?:work\s+)?site',
        r'access\s+to\s+(?:the\s+)?(?:work\s+)?site',
        r'other\s+(?:contractors?|parties)\s+(?:may\s+)?(?:perform|work)',
        r'[Cc]onditions?\s+that\s+occur\s+on\s+the\s+site',
        r'(?:borings|probings).*?(?:subsurface|soil\s+condition)',
    ],

    "environmental": [
        r'environmental.*?(?:compliance|requirement|hazard|protection)',
        r'hazardous\s+(?:material|substance|waste)',
        r'(?:waste|debris).*?(?:dispos|remov)',
        r'\bEPA\b',
        r'pollution.*?(?:control|prevent|limit|law)',
        r'(?:spill|contaminat).*?(?:prevent|clean|response)',
        r'(?:storage\s+area)\s+for\s+hazardous',
        r'(?:demolition|clearing).*?(?:material|debris).*?(?:dispos|remov|property)',
        r'(?:demolition|wrecking)\s+operations?.*?(?:water|sprinkl|dust|enclosure)',
        r'(?:dust|air)\s+(?:control|pollution).*?(?:operation|demolit)',
    ],

    "order_of_precedence": [
        r'order\s+of\s+precedence',
        r'conflict.*?(?:document|provision)',
        r'inconsisten(?:cy|t).*?document',
        r'precedence.*?(?:document|term)',
    ],

    "setoff_withholding": [
        r'set[\s\-]?off\s+(?:right|provision|against)',
        r'(?:withhold|deduct).{0,30}(?:from\s+)?(?:final\s+)?payment',
        r'(?:owner|city|agency).{0,20}(?:may|right\s+to)\s+(?:deduct|withhold)',
        r'(?:OWNER|owner)\s+will\s+deduct',
        r'(?:Deductions?)\s+for\s+(?:uncorrected|liquidated|reinspection)',
    ],

    # ===================================================================
    # SECTION V: REGULATORY & COMPLIANCE TERMS (8 categories)
    # ===================================================================

    "certified_payroll": [
        r'certified\s+payroll',
        r'payroll.*?(?:record|report|certification)',
        r'(?:wage|labor)\s+report',
    ],

    "prevailing_wage": [
        r'prevailing\s+wage',
        r'Davis[\s\-]Bacon',
        r'(?:federal|state)\s+wage.*?(?:requirement|determination)',
        r'minimum\s+wage',
    ],

    "eeo": [
        r'(?:equal|E\.?E\.?O\.?)\s+(?:employment\s+)?opportunit(?:y|ies)',
        r'non[\s\-]discriminat(?:ion|ory)',
        r'affirmative\s+action',
        r'anti[\s\-]?discriminat(?:ion|ory|e)',
        r'(?:shall|will)\s+not\s+discriminate',
    ],

    "mwbe_dbe": [
        r'(?:M|D|W)(?:B|W)E',
        r'(?:minority|woman|disadvantaged)[\s\-]owned\s+business',
        r'small\s+business.*?(?:participation|goal)',
    ],

    "apprenticeship": [
        r'apprentice(?:ship)?',
        r'training.*?(?:program|requirement)',
        r'workforce\s+development',
    ],

    "e_verify": [
        r'E[\s\-]Verify',
        r'(?:employment|work)\s+(?:eligibility\s+)?(?:verification|authorization).*?(?:immigration|I[\s\-]?9|citizenship|alien)',
        r'immigration.*?(?:compliance|requirement|verification|status)',
        r'unauthorized\s+alien',
        r'(?:I[\s\-]?9|form\s+I[\s\-]?9)',
    ],

    "worker_classification": [
        r'(?:employee|worker)\s+classification',
        r'independent\s+contractor.*?(?:status|designation|determination|shall|restrict)',
        r'(?:1099|W[\s\-]2).*?(?:employee|contractor|worker|classification|status)',
        r'misclassif(?:y|ication).*?(?:worker|employee)',
    ],

    "drug_free_workplace": [
        r'drug[\s\-]free\s+workplace',
        r'substance.*?(?:testing|abuse)',
        r'alcohol.*?(?:testing|policy)',
    ],

    # ===================================================================
    # SECTION VI: DATA, TECHNOLOGY & DELIVERABLES (7 categories)
    # ===================================================================

    "data_ownership": [
        r'data\s+ownership',
        r'(?:right|title|interest)\s+(?:in|to)\s+(?:data|digital\s+deliverable)',
        r'(?:ownership|rights?)\s+(?:of|to|in)\s+(?:data|digital|electronic)',
    ],


    "ai_technology_use": [
        r'artificial\s+intelligence',
        r'\bAI\b.*?(?:tool|system|model|use|restriction|prohibition|software)',
        r'A\.I\.',
        r'(?:machine\s+learning|automated\s+decision)',
        r'technology\s+(?:use\s+)?restriction.*?(?:contract|clause|provision|prohibit)',
    ],

    "cybersecurity": [
        r'cyber[\s\-]?security',
        r'information\s+security\s+(?:policy|plan|requirement|standard)',
        r'data\s+breach',
        r'breach\s+notification',
        r'(?:network|IT|computer|system)\s+security',
    ],

    "digital_deliverables": [
        r'(?:BIM|GIS)',
        r'digital.*?(?:deliverable|submission)',
        r'electronic.*?(?:file|format|submission)',
        r'CAD',
        r'(?:digital|aerial)\s+(?:images?|photograph)',
        r'(?:digital|electronic)\s+(?:progress\s+)?AS[\-\s]?BUILT',
        r'AS[\-\s]?BUILT\s+DRAWINGS?',
    ],

    "document_retention": [
        r'document.*?retention',
        r'(?:record|file).*?(?:retention|preservation)',
        r'retain.*?(?:document|record).*?(?:\d+\s+years?|period)',
    ],

    "confidentiality": [
        r'confidentiality\s+(?:agreement|provision|clause|obligation|requirement)',
        r'confidential\s+(?:information|document|data|material)',
        r'non[\s\-]disclosure',
        r'(?:NDA|N\.D\.A\.)',
        r'proprietary\s+information',
        r'trade\s+secret',
    ],
}


# =========================================================================
# Exclude Zone Detection — identify non-clause regions to skip
# =========================================================================

# TOC lines: dot leaders (anywhere in line) or "thru" page references
_TOC_DOT_LEADER_RE = re.compile(
    r'^.*?\.{5,}.*$',
    re.MULTILINE
)
_TOC_THRU_RE = re.compile(
    r'^\s*.*?\d+[\-\.]\d+\s+thru\s+\d+[\-\.]\d+',
    re.MULTILINE | re.IGNORECASE
)

# Drawing/specification index headers
_INDEX_HEADER_RE = re.compile(
    r'(?:DRAWING|SHEET|SPECIFICATION)\s+INDEX',
    re.IGNORECASE
)

# Project info / permit status blocks
_PROJECT_INFO_RE = re.compile(
    r'(?:^|\n)\s*(?:'
    r'PROJECT\s+(?:OWNER|MAP|LOCATION|SITE|NUMBER|NAME|INFO)'
    r'|PERMIT\s+(?:STATUS|NUMBER|NO\.?|INFO)'
    r'|SCALE:\s*\d'
    r')',
    re.IGNORECASE | re.MULTILINE
)

# Section header pattern (reused for end-of-zone detection)
_SECTION_HEADER_RE = re.compile(
    r'(?:^|\n)(?:'
    r'(?:SECTION|ARTICLE|PART)\s+[IVX0-9]'
    r'|[0-9]+\.[0-9]+\s+[A-Z]'
    r'|[A-Z][A-Z\s]{5,40}(?:\n|$)'
    r')',
    re.IGNORECASE | re.MULTILINE
)


def _merge_zones(zones: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Merge overlapping (start, end) ranges into non-overlapping sorted list."""
    if not zones:
        return []
    zones.sort()
    merged = [zones[0]]
    for start, end in zones[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _find_next_boundary(text: str, pos: int, max_chars: int) -> int:
    """Find next section header or double-newline after pos, up to max_chars."""
    search_end = min(len(text), pos + max_chars)
    # Try section header first
    m = _SECTION_HEADER_RE.search(text, pos + 100, search_end)
    if m:
        return m.start()
    # Fall back to double-newline
    dn = text.find('\n\n', pos + 50, search_end)
    if dn != -1:
        return dn
    return search_end


def detect_exclude_zones(contract_text: str) -> List[Tuple[int, int]]:
    """
    Identify non-clause regions in contract text that should be excluded
    from regex matching: TOC blocks, drawing indices, project info blocks.

    Returns sorted, non-overlapping list of (start, end) character position ranges.
    """
    zones = []
    text_len = len(contract_text)

    # --- TOC blocks: clusters of 3+ dot-leader or "thru" lines ---
    toc_positions = []
    for m in _TOC_DOT_LEADER_RE.finditer(contract_text):
        toc_positions.append((m.start(), m.end()))
    for m in _TOC_THRU_RE.finditer(contract_text):
        toc_positions.append((m.start(), m.end()))
    toc_positions.sort()

    # Cluster nearby TOC lines (within 500 chars of each other)
    if toc_positions:
        cluster_start = toc_positions[0][0]
        cluster_end = toc_positions[0][1]
        cluster_count = 1
        for start, end in toc_positions[1:]:
            if start - cluster_end < 500:
                cluster_end = end
                cluster_count += 1
            else:
                if cluster_count >= 3:
                    zones.append((cluster_start, cluster_end))
                cluster_start = start
                cluster_end = end
                cluster_count = 1
        if cluster_count >= 3:
            zones.append((cluster_start, cluster_end))

    # --- Drawing/specification index blocks ---
    for m in _INDEX_HEADER_RE.finditer(contract_text):
        end = _find_next_boundary(contract_text, m.start(), 5000)
        zones.append((m.start(), end))

    # --- Project info / permit status blocks ---
    for m in _PROJECT_INFO_RE.finditer(contract_text):
        # Use tight boundary: next double-newline or 500 chars max
        dn = contract_text.find('\n\n', m.end(), min(text_len, m.end() + 500))
        end = dn if dn != -1 else min(text_len, m.end() + 500)
        zones.append((m.start(), end))

    merged = _merge_zones(zones)
    total_chars = sum(e - s for s, e in merged)
    logger.info(
        f"Detected {len(merged)} exclude zones covering {total_chars} chars "
        f"({total_chars * 100 / max(len(contract_text), 1):.1f}% of text)"
    )
    return merged


def _position_in_exclude_zone(
    position: int,
    zones: List[Tuple[int, int]]
) -> bool:
    """Check if position falls within any exclude zone using binary search."""
    if not zones:
        return False
    starts = [z[0] for z in zones]
    idx = bisect.bisect_right(starts, position) - 1
    if idx >= 0 and zones[idx][0] <= position <= zones[idx][1]:
        return True
    return False


# =============================================================================
# SECTION-AWARE PARSING: Structural segmentation of construction contracts
# =============================================================================

@dataclass
class SectionBlock:
    """A structural section of the contract (CSI section, article, or sub-article)."""
    header_text: str
    header_normalized: str  # lowercase, stripped
    start_pos: int
    end_pos: int
    section_type: str  # 'csi_major', 'article', 'subarticle', 'flat'


# Three tiers of header detection, from most specific to least
MAJOR_SECTION_RE = re.compile(
    r'(?:^|\n)\s*(?:SECTION|DIVISION)\s+(\d{4,5})\b[^\n]*',
    re.IGNORECASE | re.MULTILINE
)

ARTICLE_RE = re.compile(
    r'(?:^|\n)\s*(?:'
    r'ARTICLE\s+[IVX0-9]+'                        # ARTICLE 7, ARTICLE IV
    r'|GENERAL\s+CONDITIONS'                       # GENERAL CONDITIONS header
    r'|SUPPLEMENTAL\s+(?:GENERAL\s+)?CONDITIONS'   # SUPPLEMENTAL CONDITIONS
    r'|SPECIAL\s+(?:CONDITIONS|PROVISIONS)'         # SPECIAL CONDITIONS
    r')',
    re.IGNORECASE | re.MULTILINE
)

# Roman numeral headers — NO IGNORECASE so [A-Z] only matches actual uppercase
# Requires 2+ Roman numeral chars (II, III, IV, etc.) to avoid matching
# common spec list items like "I. NO MUCK BLANKET..." or "V. APPLY COATING..."
ROMAN_NUMERAL_RE = re.compile(
    r'(?:^|\n)\s*[IVX]{2,4}\.\s+[A-Z][A-Z ]{2,}',
    re.MULTILINE
)

SUBARTICLE_RE = re.compile(
    r'(?:^|\n)\s*(\d{1,2}\.\d{1,3})\.?\s+[A-Z][A-Za-z]',
    re.MULTILINE
)


def parse_contract_sections(
    contract_text: str,
    exclude_zones: Optional[List[Tuple[int, int]]] = None
) -> List[SectionBlock]:
    """
    Parse a contract into structural sections for section-aware extraction.

    Uses three tiers of header detection:
    1. CSI MasterFormat sections (SECTION 01505, DIVISION 02)
    2. Articles (ARTICLE 7, III. TERM OF AGREEMENT)
    3. Sub-articles (1.1 GENERAL, 2.3 MATERIALS)

    Flat-contract fallback: If fewer than 3 sections detected, returns a single
    SectionBlock spanning the entire text with section_type='flat'.

    Returns:
        Ordered list of SectionBlock objects
    """
    if not contract_text:
        return [SectionBlock("", "", 0, 0, "flat")]

    text_len = len(contract_text)
    raw_headers = []  # list of (position, end_pos, header_text, section_type)

    # Tier 1: CSI major sections
    for m in MAJOR_SECTION_RE.finditer(contract_text):
        if exclude_zones and _position_in_exclude_zone(m.start(), exclude_zones):
            continue
        raw_headers.append((m.start(), m.end(), m.group(0).strip(), 'csi_major'))

    # Tier 2a: Named articles (ARTICLE X, GENERAL CONDITIONS, etc.)
    for m in ARTICLE_RE.finditer(contract_text):
        if exclude_zones and _position_in_exclude_zone(m.start(), exclude_zones):
            continue
        raw_headers.append((m.start(), m.end(), m.group(0).strip(), 'article'))

    # Tier 2b: Roman numeral headers (III. TERM OF AGREEMENT) — case-sensitive
    for m in ROMAN_NUMERAL_RE.finditer(contract_text):
        if exclude_zones and _position_in_exclude_zone(m.start(), exclude_zones):
            continue
        raw_headers.append((m.start(), m.end(), m.group(0).strip(), 'article'))

    # Tier 3: Sub-articles
    for m in SUBARTICLE_RE.finditer(contract_text):
        if exclude_zones and _position_in_exclude_zone(m.start(), exclude_zones):
            continue
        raw_headers.append((m.start(), m.end(), m.group(0).strip(), 'subarticle'))

    # Sort by position
    raw_headers.sort(key=lambda h: h[0])

    # Deduplicate overlaps (min 100-char gap between headers)
    deduped = []
    for hdr in raw_headers:
        if deduped and hdr[0] - deduped[-1][0] < 100:
            # Keep the more specific one (csi_major > article > subarticle)
            priority = {'csi_major': 3, 'article': 2, 'subarticle': 1}
            if priority.get(hdr[3], 0) > priority.get(deduped[-1][3], 0):
                deduped[-1] = hdr
            continue
        deduped.append(hdr)

    # Flat-contract fallback
    if len(deduped) < 3:
        logger.info(f"Flat contract detected ({len(deduped)} headers) — section scoring disabled")
        return [SectionBlock("", "", 0, text_len, "flat")]

    # Build SectionBlock list with end_pos = next header's start_pos
    sections = []

    # Capture preamble text before the first detected header
    first_header_pos = deduped[0][0]
    if first_header_pos > 200:
        sections.append(SectionBlock(
            header_text="CONTRACT PREAMBLE",
            header_normalized="contract preamble",
            start_pos=0,
            end_pos=first_header_pos,
            section_type="preamble"
        ))

    for i, (pos, end, text, stype) in enumerate(deduped):
        next_pos = deduped[i + 1][0] if i + 1 < len(deduped) else text_len
        sections.append(SectionBlock(
            header_text=text,
            header_normalized=text.lower().strip(),
            start_pos=pos,
            end_pos=next_pos,
            section_type=stype
        ))

    logger.info(f"Parsed {len(sections)} contract sections ({sum(1 for s in sections if s.section_type == 'csi_major')} CSI, "
                f"{sum(1 for s in sections if s.section_type == 'article')} articles, "
                f"{sum(1 for s in sections if s.section_type == 'subarticle')} sub-articles)")
    return sections


# Category-to-section hint mapping: keywords expected in section headers
# Keys MUST match TEMPLATE_PATTERNS keys exactly
CATEGORY_SECTION_HINTS = {
    # Administrative & Commercial
    "contract_term_renewal_extensions": ["agreement", "contract term", "duration", "term of contract", "renewal", "extension"],
    "notice_requirements": ["notice to proceed", "written notice", "notice requirement", "notices"],
    "assignment_novation": ["assignment", "novation", "transfer of contract", "shall not assign"],
    "dispute_resolution": ["dispute resolution", "arbitration", "mediation", "claims process", "disputes"],
    "limitation_of_liability": ["limitation of liability", "liability cap", "consequential damages", "damage cap", "not liable"],
    "confidentiality": ["confidential", "proprietary", "non-disclosure", "trade secret"],

    "audit_rights": ["audit rights", "inspection of records", "books and records", "audit", "records"],
    "subcontracting": ["subcontract", "01400", "subcontractor approval", "subcontractor"],
    "order_of_precedence": ["order of precedence", "conflicting documents", "document hierarchy", "precedence"],
    "document_retention": ["record retention", "document retention", "retention period", "maintain records"],

    # Financial
    "retainage_progress_payments": ["payment", "retainage", "retention", "progress payment", "final payment"],
    "mobilization_demobilization": ["mobilization", "01505", "01500", "demobilization"],
    "price_escalation": ["escalation", "price adjustment", "adjustments to price", "fuel price", "fuel adjustment", "diesel", "ppi", "producer price index", "cost index"],
    "setoff_withholding": ["setoff", "withhold", "offset", "deduct", "retain amounts"],
    "pay_when_paid_if_paid": ["pay when paid", "pay if paid", "payment condition", "receipt of payment"],
    "change_orders": ["change order", "changes in the work", "modification of contract", "extra work", "additional work"],

    # Insurance & Risk
    "insurance_coverage": ["insurance requirements", "insurance coverage", "certificates of insurance", "additional insured", "policy limits", "commercial general liability"],
    "bonding_surety_insurance": ["bond", "00610", "00600", "surety", "performance bond", "payment bond"],
    "indemnification": ["indemnif", "hold harmless", "defend and indemnify", "indemnity"],
    "duty_to_defend": ["duty to defend", "defense obligation", "defend and indemnify", "defense cost"],
    "warranty": ["warranty", "guarantee", "correction of work", "defects", "workmanship"],

    # Scope & Execution
    "scope_of_work": ["summary of work", "01010", "01110", "scope of work", "01100", "scope"],
    "deliverables": ["deliverable", "submittals", "01300", "as-built"],
    "delivery_deadlines": ["delivery deadline", "substantial completion", "final completion", "completion date", "time for completion"],
    "submittals": ["submittals", "01300", "01340", "shop drawing", "product data"],
    "site_conditions": ["site condition", "subsurface", "differing site", "changed conditions",
                        "site access", "access to work site", "cooperation", "work area", "other contractors"],
    "environmental": ["environmental", "01560", "hazardous", "waste disposal", "contamination"],
    "safety_osha": ["safety", "01560", "01530", "osha", "health and safety", "ppe", "safety program"],
    "permits_licensing": ["permit", "license", "01060", "regulatory approval"],
    "performance_schedule": ["schedule", "01310", "01320", "progress schedule", "cpm", "time is of the essence"],
    "worksite_coordination": ["coordination", "01040", "interface", "other contractors"],
    "utility_coordination": ["utility", "utility coordination", "locate", "utility conflict"],
    "punch_list": ["punch list", "01700", "substantial completion", "final inspection"],

    # Termination
    "termination_for_cause": ["termination", "default", "cause", "material breach", "cure period"],
    "termination_for_convenience": ["termination for convenience", "terminate without cause", "owner may terminate", "for any reason"],
    "suspension_of_work": ["suspension of work", "suspend work", "stop work order",
                          "work stoppage", "delay performance", "right to delay",
                          "stopped or delayed"],
    "delays": ["delay", "excusable", "time extension", "force majeure", "acts of god"],

    # Compliance & Regulatory
    "prevailing_wage": ["prevailing wage", "davis-bacon", "wage rate", "wage determination"],
    "certified_payroll": ["payroll", "certified payroll", "prevailing wage"],
    "mwbe_dbe": ["minority", "mbe", "dbe", "disadvantaged business", "mwbe"],
    "e_verify": ["e-verify", "immigration", "i-9", "employment eligibility"],
    "drug_free_workplace": ["drug", "substance", "drug-free", "drug screening"],
    "eeo": ["equal opportunity", "eeo", "nondiscrimination", "discrimination",
            "anti-discrimination", "discriminate"],
    "worker_classification": ["worker classification", "independent contractor", "employee vs contractor"],
    "apprenticeship": ["apprentice", "training program", "workforce development"],

    # Special / Supplemental
    "owner_supplied_support": ["owner furnished", "owner provided", "01600"],
    "emergency_work": ["emergency", "urgent", "emergency work"],
    "emergency_contingency": ["emergency", "contingency", "emergency response"],
    "flow_down_clauses": ["flow down", "flow-down", "subcontract requirements"],
    "field_ticket": ["field ticket", "time and material", "force account"],
    "release_orders": ["release order", "task order", "work authorization"],
    "contractor_qualification": ["qualification", "experience", "00200", "prequalification"],
    "bid_protest": ["bid protest", "00100", "procurement"],
    "bid_tabulation": ["bid tabulation", "00100", "bid opening", "bid evaluation"],

    # Technology & Data
    "ai_technology_use": ["artificial intelligence", "ai technology", "automation"],
    "cybersecurity": ["cybersecurity", "data security", "breach notification"],
    "data_ownership": ["data ownership", "intellectual property", "work product"],
    "digital_deliverables": ["digital", "bim", "cad", "01300"],
    "use_of_aps_tools": ["software", "tools", "system"],
}

# Brief descriptions telling the AI what to look for in each category.
# Used by per-item AI analysis to build focused search prompts.
CATEGORY_SEARCH_DESCRIPTIONS = {
    # Section II: Administrative & Commercial Terms
    "contract_term_renewal_extensions": "Contract duration, term length, renewal options, extension provisions, days for substantial and final completion",
    "bonding_surety_insurance": "Performance bonds, payment bonds, surety requirements, bond amounts and conditions",
    "retainage_progress_payments": "Retainage percentage, progress payment schedules, final payment conditions, payment applications",
    "pay_when_paid_if_paid": "Payment contingent on owner paying general contractor, pay-when-paid or pay-if-paid conditions, subcontractor payment timing",
    "price_escalation": "Price escalation clauses for labor, materials, fuel, or inflation adjustments, cost adjustment formulas, fuel surcharge provisions",
    "change_orders": "Change order procedures, scope modifications, pricing of changes, written authorization requirements",
    "termination_for_convenience": "Owner or agency right to terminate without cause, compensation upon convenience termination",
    "termination_for_cause": "Termination for default by contractor, cure periods, grounds for cause termination",
    "bid_protest": "Bid protest procedures, claims of improper award, protest timelines and remedies",
    "bid_tabulation": "Bid tabulation requirements, competition standards, award process procedures",
    "contractor_qualification": "Contractor qualification, licensing, certification, experience requirements, prequalification",
    "release_orders": "Release orders, task orders, work authorization protocols, indefinite quantity provisions",
    "assignment_novation": "Assignment restrictions, novation requirements, transfer of contract rights",
    "audit_rights": "Audit rights, recordkeeping obligations, document retention, inspection of books and records",
    "notice_requirements": "Notice requirements, claim timeframes, notice to cure, delay notices, written notice provisions",
    # Section III: Technical & Performance Terms
    "scope_of_work": "Scope of work, work inclusions, exclusions, defined deliverables, summary of work",
    "performance_schedule": "Performance schedule, time for completion, critical path obligations, CPM schedule, milestone dates",
    "delays": "Delays, force majeure, acts of God, weather delays, owner-caused delays, excusable delays, time extensions",
    "suspension_of_work": "Suspension of work, work stoppages, agency stop-work directives, resumption procedures, right to delay performance, project stopped or delayed for extended period",
    "submittals": "Submittals, shop drawings, product data, samples, approval requirements, submittal schedule",
    "emergency_work": "Emergency work obligations, urgent repairs, emergency response procedures",
    "permits_licensing": "Permits, licensing, regulatory approvals required for the work, permit fees",
    "warranty": "Warranty periods, guarantees, defects liability, correction of work, warranty obligations",
    "use_of_aps_tools": "Use of specific tools, equipment, materials, or supplies; owner-specified systems",
    "owner_supplied_support": "Owner-furnished materials, owner-provided utilities, site access provisions",
    "field_ticket": "Field tickets, daily work logs, time and materials documentation, force account work",
    "mobilization_demobilization": "Mobilization provisions, demobilization requirements, mobilization payment, site setup",
    "utility_coordination": "Utility coordination, locate risk, utility conflict avoidance, utility relocation",
    "delivery_deadlines": "Delivery deadlines, milestone dates, substantial completion, final completion standards",
    "punch_list": "Punch list procedures, closeout requirements, acceptance of work, final inspection",
    "worksite_coordination": "Worksite coordination, access restrictions, sequencing obligations, interface with other contractors",
    "deliverables": "Deliverables, digital submissions, documentation standards, as-built drawings",
    "emergency_contingency": "Emergency contingency provisions, contingency work obligations, emergency response",
    # Section IV: Legal Risk & Enforcement
    "indemnification": "Indemnification, defense, hold harmless provisions, indemnity scope and limitations",
    "duty_to_defend": "Duty to defend vs. indemnify, defense cost obligations, legal defense scope",
    "limitation_of_liability": "Limitations of liability, damage caps, waivers of consequential damages",
    "insurance_coverage": "Insurance coverage requirements, additional insured, waiver of subrogation, policy limits",
    "dispute_resolution": "Dispute resolution procedures, mediation, arbitration, litigation, claims process",
    "flow_down_clauses": "Flow-down clauses, prime-to-subcontract risk pass-through, subcontract requirements",
    "subcontracting": "Subcontracting restrictions, subcontractor approval, substitution requirements",
    "safety_osha": "Safety standards, OSHA compliance, site-specific safety obligations, safety programs",
    "site_conditions": "Site conditions, differing site conditions, changed circumstances, subsurface conditions, site access provisions, access to work site, other contractors in work area",
    "environmental": "Environmental hazards, waste disposal, hazardous materials, environmental compliance",
    "order_of_precedence": "Order of precedence, conflicting documents, document hierarchy, interpretation rules",
    "setoff_withholding": "Setoff rights, withholding rights, owner right to deduct or withhold payment",
    # Section V: Regulatory & Compliance Terms
    "certified_payroll": "Certified payroll requirements, payroll recordkeeping, reporting obligations",
    "prevailing_wage": "Prevailing wage, Davis-Bacon Act, federal or state wage rate compliance, wage determinations",
    "eeo": "Equal employment opportunity, non-discrimination requirements, affirmative action, anti-discrimination clauses, prohibition against discrimination",
    "mwbe_dbe": "Minority business enterprise, DBE participation, disadvantaged business requirements, MBE/WBE goals",
    "apprenticeship": "Apprenticeship requirements, training programs, workforce development obligations",
    "e_verify": "E-Verify enrollment, immigration compliance, Form I-9, employment eligibility verification",
    "worker_classification": "Worker classification, independent contractor restrictions, employee vs. contractor",
    "drug_free_workplace": "Drug-free workplace requirements, substance testing, drug and alcohol policies",
    # Section VI: Data, Technology & Deliverables
    "data_ownership": "Data ownership, access rights, rights to digital deliverables, data transfer",

    "ai_technology_use": "AI or technology use restrictions, automation policies, digital tool requirements",
    "cybersecurity": "Cybersecurity standards, breach notification, IT system use policies, data protection",
    "digital_deliverables": "BIM requirements, CAD deliverables, digital submission standards, model specifications",
    "document_retention": "Document retention periods, records preservation, data security, retention schedules",
    "confidentiality": "Confidentiality provisions, non-disclosure obligations, proprietary information protection",
}


def _is_general_conditions_section(header_normalized: str) -> bool:
    """Check if a section header is in Division 00-01 (general/admin) vs 02+ (technical)."""
    # CSI Division 00 (procurement) and 01 (general requirements)
    m = re.search(r'(?:section|division)\s+(\d{4,5})', header_normalized)
    if m:
        code = int(m.group(1))
        return code < 2000  # Divisions 00xxx and 01xxx
    # Named general sections
    general_keywords = ['general condition', 'supplemental condition', 'special condition',
                        'agreement', 'instruction', 'bid', 'proposal', 'preamble']
    return any(kw in header_normalized for kw in general_keywords)


def _score_match_by_section(
    position: int,
    category: str,
    section_index: List[SectionBlock]
) -> float:
    """
    Score a regex match based on which contract section it falls in.

    Returns:
        1.0  — CSI major section header contains a hint keyword
        0.85 — Article-level header contains a hint keyword
        0.7  — Sub-article header contains a hint keyword
        0.5  — Flat contract (no sections) — neutral
        0.4  — General conditions section (Division 00-01) but no hint match
        0.2  — Technical spec section (Division 02+) with no hint match
    """
    if not section_index:
        return 0.5

    # Find which section this position belongs to
    section = None
    section_idx = None
    for i, s in enumerate(section_index):
        if s.start_pos <= position < s.end_pos:
            section = s
            section_idx = i
            break

    if section is None:
        return 0.3  # Position before first or after last section

    # Flat contract — neutral score
    if section.section_type == 'flat':
        return 0.5

    # Preamble — contains contract-level terms, score moderately high
    if section.section_type == 'preamble':
        hints = CATEGORY_SECTION_HINTS.get(category, [])
        if hints and any(kw in section.header_normalized for kw in hints):
            return 0.8
        return 0.6

    hints = CATEGORY_SECTION_HINTS.get(category, [])

    # Check if THIS section's header contains a hint keyword
    hint_match = any(kw in section.header_normalized for kw in hints)

    if hint_match:
        score_map = {'csi_major': 1.0, 'article': 0.85, 'subarticle': 0.7}
        return score_map.get(section.section_type, 0.7)

    # For subarticles/articles, also check the nearest PARENT CSI major section
    # (subarticle 1.1 under SECTION 01505 should inherit 01505's hint score)
    if section.section_type in ('subarticle', 'article') and section_idx is not None:
        for j in range(section_idx - 1, -1, -1):
            parent = section_index[j]
            if parent.section_type == 'csi_major':
                parent_hint = any(kw in parent.header_normalized for kw in hints)
                if parent_hint:
                    return 0.95  # Slightly less than direct CSI match
                break  # Only check nearest parent CSI section

    # No hint match — score by whether it's general or technical
    if _is_general_conditions_section(section.header_normalized):
        return 0.4
    return 0.2


def get_relevant_text_for_category(
    contract_text: str,
    category_key: str,
    section_index: List[SectionBlock],
    max_chars: int = 12000
) -> str:
    """
    Get the most relevant contract text for a specific category.

    Uses CATEGORY_SECTION_HINTS to find sections whose headers match
    the category's expected location. Returns concatenated section text
    with headers for AI context.

    Args:
        contract_text: Full contract text
        category_key: Template category key (e.g., "mobilization_demobilization")
        section_index: Parsed section index from parse_contract_sections()
        max_chars: Maximum characters to return (default 12000 ≈ 3400 tokens)

    Returns:
        Relevant section text with headers, or first max_chars if no sections match.
    """
    if not section_index:
        return contract_text[:max_chars]

    # Flat contract — return first chunk
    if len(section_index) == 1 and section_index[0].section_type == 'flat':
        return contract_text[:max_chars]

    hints = CATEGORY_SECTION_HINTS.get(category_key, [])
    if not hints:
        return contract_text[:max_chars]

    # Score each section and collect matches
    scored_sections = []
    for i, section in enumerate(section_index):
        if section.section_type == 'flat':
            continue
        hint_match = any(kw in section.header_normalized for kw in hints)
        if hint_match:
            score_map = {'csi_major': 1.0, 'article': 0.85, 'subarticle': 0.7}
            score = score_map.get(section.section_type, 0.7)
            scored_sections.append((score, i, section))
        elif section.section_type in ('subarticle', 'article'):
            # Check parent CSI section
            for j in range(i - 1, -1, -1):
                parent = section_index[j]
                if parent.section_type == 'csi_major':
                    if any(kw in parent.header_normalized for kw in hints):
                        scored_sections.append((0.95, i, section))
                    break

    # Sort by score descending
    scored_sections.sort(key=lambda x: -x[0])

    if not scored_sections:
        # Fallback: collect general conditions sections
        for i, section in enumerate(section_index):
            if _is_general_conditions_section(section.header_normalized):
                scored_sections.append((0.4, i, section))
        scored_sections.sort(key=lambda x: -x[0])

    if not scored_sections:
        return contract_text[:max_chars]

    # Build output: concatenate matched sections with headers
    parts = []
    total_chars = 0
    for score, idx, section in scored_sections:
        section_text = contract_text[section.start_pos:section.end_pos]
        header = f"[{section.header_text.strip()}]"
        chunk = f"{header}\n{section_text}"

        if total_chars + len(chunk) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:  # Only add if meaningful amount remains
                parts.append(chunk[:remaining])
            break
        parts.append(chunk)
        total_chars += len(chunk)

    return "\n\n---\n\n".join(parts) if parts else contract_text[:max_chars]


def map_matches_to_sections(
    matches: List[Dict],
    section_index: List['SectionBlock'],
) -> List[Tuple[int, float]]:
    """Map regex match positions to section indices using bisect. O(log n) per match.

    Returns list of (section_idx, best_score) sorted by score descending.
    Deduplicates so each section appears at most once with its best score.
    """
    import bisect as _bisect
    if not section_index or not matches:
        return []
    starts = [s.start_pos for s in section_index]
    seen: Dict[int, float] = {}
    for m in matches:
        pos = m.get('position', 0)
        si = _bisect.bisect_right(starts, pos) - 1
        si = max(0, min(si, len(section_index) - 1))
        score = m.get('section_score', 0.5)
        if si not in seen or score > seen[si]:
            seen[si] = score
    return sorted(seen.items(), key=lambda x: -x[1])


def extract_clauses_for_category(
    contract_text: str,
    category: str,
    patterns: List[str],
    context_size: int = 3000,
    exclude_zones: List[Tuple[int, int]] = None,
    section_index: Optional[List[SectionBlock]] = None
) -> List[Dict]:
    """
    Extract all clauses matching a template category using regex patterns.

    Captures the FULL surrounding clause text (not just a snippet) by looking
    for section boundaries (headers, numbered sections) rather than just
    paragraph breaks.

    When section_index is provided, matches are scored by section relevance
    and sorted so the best-section match wins (instead of first-positional).

    Args:
        contract_text: Full contract text
        category: Template category name
        patterns: List of regex patterns for this category
        context_size: Characters to include before/after match
        exclude_zones: List of (start, end) position ranges to skip (TOC, indices, etc.)
        section_index: Optional list of SectionBlock for section-aware scoring

    Returns:
        List of extracted clauses with context
    """
    extracted = []
    seen_positions = set()

    # Pattern to detect section headers (used to find clause boundaries)
    section_header_re = re.compile(
        r'(?:^|\n)(?:'
        r'(?:SECTION|ARTICLE|PART)\s+[IVX0-9]'  # SECTION I, ARTICLE 1, PART I
        r'|[0-9]+\.[0-9]+\s+[A-Z]'               # 1.1 Title
        r'|[A-Z][A-Z\s]{5,40}(?:\n|$)'            # ALL CAPS HEADERS (6-40 chars)
        r')',
        re.IGNORECASE | re.MULTILINE
    )

    # Less aggressive pattern for forward context boundary — only major sections,
    # not sub-article headers. This prevents context from being cut too short.
    major_boundary_re = re.compile(
        r'(?:^|\n)\s*(?:SECTION|DIVISION)\s+\d{4,5}\b',
        re.MULTILINE
    )

    # Pattern to detect page footers/headers that repeat section
    # numbers (e.g., "01291 - 2 SECTION 01291") — these are NOT
    # real section boundaries and should be skipped.
    page_footer_re = re.compile(
        r'\d{4,5}\s*-\s*\d+\s+(?:SECTION|Section)\s+\d{4,5}'
    )

    for pattern in patterns:
        try:
            matches = re.finditer(pattern, contract_text, re.IGNORECASE | re.MULTILINE)

            for match in matches:
                position = match.start()

                # Skip matches in exclude zones (TOC, drawing index, project info)
                if exclude_zones and _position_in_exclude_zone(position, exclude_zones):
                    continue

                # Avoid duplicates from overlapping patterns
                if any(abs(position - seen_pos) < 100 for seen_pos in seen_positions):
                    continue

                seen_positions.add(position)

                # --- Find context START: look backward for section header ---
                search_start = max(0, position - context_size)
                before_text = contract_text[search_start:position]

                # Find the last section header before the match
                headers_before = list(section_header_re.finditer(before_text))
                if headers_before:
                    # Start from the last header found before the match
                    start = search_start + headers_before[-1].start()
                else:
                    # No header found — use paragraph boundary or raw offset
                    para_start = contract_text.rfind('\n\n', search_start, position)
                    start = para_start if para_start != -1 else search_start

                # --- Find context END: look forward for next section header ---
                search_end = min(len(contract_text), position + context_size)
                after_text = contract_text[match.end():search_end]

                # Find the next MAJOR section boundary after the match.
                # Use major_boundary_re (SECTION/DIVISION) for forward search
                # to avoid cutting context at sub-article headers (1.1, 1.2).
                # Skip page footers (e.g., "01291 - 2 SECTION 01291") and the
                # project info block (~200 chars) that follows each page footer.
                header_after = None
                if len(after_text) > 200:
                    search_offset = 200
                    while search_offset < len(after_text):
                        candidate = major_boundary_re.search(after_text[search_offset:])
                        if not candidate:
                            break
                        candidate_pos = search_offset + candidate.start()
                        # Check if this is a page footer, not a real section boundary
                        line_start = after_text.rfind('\n', 0, candidate_pos)
                        line_start = line_start + 1 if line_start != -1 else 0
                        line_text = after_text[line_start:candidate_pos + candidate.end() - candidate.start() + 20]
                        if page_footer_re.search(line_text):
                            # Skip footer + project info block (~200 chars after footer)
                            search_offset = candidate_pos + candidate.end() - candidate.start() + 200
                            continue
                        header_after = candidate
                        header_after_offset = candidate_pos
                        break

                if header_after:
                    end = match.end() + header_after_offset
                else:
                    # No major section boundary found — use generous context
                    # (up to context_size or minimum 1500 chars of content)
                    min_context = min(search_end, match.end() + 1500)
                    end = match.end()
                    para_count = 0
                    while end < search_end and para_count < 8:
                        next_para = contract_text.find('\n\n', end + 1, search_end)
                        if next_para == -1:
                            end = search_end
                            break
                        end = next_para
                        para_count += 1
                    # Ensure minimum context when paragraphs are very short
                    if end < min_context:
                        end = min_context
                    if end == match.end():
                        end = search_end

                context = contract_text[start:end].strip()

                # Ensure we captured meaningful text (at least 50 chars)
                if len(context) < 50:
                    # Fallback: raw character window
                    start = max(0, position - 500)
                    end = min(len(contract_text), position + 1500)
                    context = contract_text[start:end].strip()

                # Score by section relevance if section_index available
                section_score = _score_match_by_section(position, category, section_index) if section_index else 0.5

                extracted.append({
                    'category': category,
                    'matched_pattern': pattern,
                    'matched_text': match.group(0),
                    'context': context,
                    'position': position,
                    'confidence': 'regex_match',
                    'section_score': section_score
                })

        except re.error as e:
            # Skip invalid regex patterns
            continue

    # Soft ranking + overlap dedup + per-category cap
    # Section scores are used for RANKING only, never to discard matches.
    # The downstream AI validation step rejects false positives.
    MAX_CLAUSES_PER_CATEGORY = 25

    if extracted:
        # Sort by position first to spread across the document, then by
        # section_score within the same region.
        extracted.sort(key=lambda x: x['position'])

        # Overlap-based deduplication: if two nearby matches share >50% of
        # their context range, keep only the higher-scored one.
        deduped = []
        for clause in extracted:
            ctx_len = len(clause.get('context', ''))
            c_start = clause['position'] - 500
            c_end = clause['position'] + max(ctx_len, 500)
            is_dup = False
            for kept in deduped:
                k_ctx_len = len(kept.get('context', ''))
                k_start = kept['position'] - 500
                k_end = kept['position'] + max(k_ctx_len, 500)
                overlap_start = max(c_start, k_start)
                overlap_end = min(c_end, k_end)
                if overlap_end > overlap_start:
                    overlap_len = overlap_end - overlap_start
                    shorter_len = min(c_end - c_start, k_end - k_start)
                    if shorter_len > 0 and overlap_len / shorter_len > 0.5:
                        is_dup = True
                        break
            if not is_dup:
                deduped.append(clause)

        # If more than cap, select top-scored from the deduped set
        if len(deduped) > MAX_CLAUSES_PER_CATEGORY:
            deduped.sort(key=lambda x: (-x.get('section_score', 0.5), x['position']))
            extracted = deduped[:MAX_CLAUSES_PER_CATEGORY]
        else:
            extracted = deduped

    return extracted


def extract_all_template_clauses(
    contract_text: str,
    section_index: Optional[List[SectionBlock]] = None
) -> Dict[str, List[Dict]]:
    """
    Extract clauses for ALL template categories using regex.

    Args:
        contract_text: Full contract text
        section_index: Optional pre-computed section index for section-aware scoring

    Returns:
        Dictionary mapping category names to extracted clauses
    """
    results = {}

    # Compute exclude zones once for the entire document
    exclude_zones = detect_exclude_zones(contract_text)

    # Compute section index if not provided
    if section_index is None:
        section_index = parse_contract_sections(contract_text, exclude_zones=exclude_zones)

    for category, patterns in TEMPLATE_PATTERNS.items():
        clauses = extract_clauses_for_category(
            contract_text, category, patterns,
            exclude_zones=exclude_zones,
            section_index=section_index
        )
        if clauses:
            results[category] = clauses

    return results
