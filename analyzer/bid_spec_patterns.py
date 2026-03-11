"""
Bid Specification Regex Patterns

Regex patterns for extracting bid specification checklist items from
construction contract documents. Designed to find and extract specific
values (numbers, percentages, durations, yes/no) rather than detect
clause presence.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern definitions: item_key -> list of regex patterns
# ---------------------------------------------------------------------------

BID_SPEC_PATTERNS: Dict[str, List[str]] = {
    # ===== Section 1: Standard Contract Items =====
    "pre_bid": [
        r"(?:mandatory|required|optional)\s+pre[\-\s]?bid\s+(?:meeting|conference|site\s+visit)",
        r"pre[\-\s]?bid\s+(?:meeting|conference)\s+(?:is|shall\s+be)\s+(?:mandatory|required|optional)",
        r"pre[\-\s]?bid\s+(?:meeting|conference|site\s+visit)",
        r"PRE[\-\s]?BID\s+Meeting",
        r"(?:virtual|in[\-\s]?person|online)\s+(?:pre[\-\s]?bid|meeting)",
        r"(?:Teams|Zoom|Webex|WebEx|GoToMeeting)\s+(?:webinar|meeting|call)",
    ],
    "submission_format": [
        r"(?:sealed|original)\s+(?:bid|proposal)\s+(?:shall|must|should)\s+be\s+(?:submitted|delivered)",
        r"(?:hard\s*copy|hardcopy|electronic|digital)\s+(?:submission|submittal|copy|copies)",
        r"(?:submit|deliver)\s+(?:\w+\s+){0,3}(?:copies|originals)",
        r"(?:email|online\s+portal|electronic)\s+(?:submission|submittal|bid)",
        r"USB\s+(?:drive|flash|digital|copy)",
        r"(?:FedEx|UPS|mail|courier|hand[\-\s]?deliver)",
        r"(?:Bonfire|BidExpress|Quest CDN|PlanetBids|OpenGov|Jaggaer|DemandStar)\s+(?:Portal|portal|platform)",
        r"[Bb]ids\s+shall\s+(?:only\s+)?be\s+(?:accepted|submitted)\s+(?:online|through|via)",
        r"(?:accepted|submitted)\s+(?:online|through|via)\s+(?:the\s+)?(?:\w+\s+)?[Pp]ortal",
    ],
    "bid_bond": [
        r"bid\s+bond\s+(?:in\s+the\s+amount\s+of\s+)?(\d+)\s*(?:%|percent)",
        r"(\d+)\s*(?:%|percent)\s+bid\s+(?:bond|security|guarantee)",
        r"bid\s+bond",
        r"bid\s+(?:guarantee|security|deposit)",
    ],
    "payment_performance_bonds": [
        r"(?:payment|performance)\s+(?:and|&)\s+(?:payment|performance)\s+bond",
        r"(?:payment|performance)\s+bond\s*(?:.*?)?(\d+)\s*(?:%|percent)",
        r"(\d+)\s*(?:%|percent)\s+(?:payment|performance)\s+bond",
        r"(?:100|110)\s*(?:%|percent)\s+(?:of\s+)?(?:the\s+)?contract\s+(?:amount|price|sum)",
        r"faithful\s+performance\s+bond",
    ],
    "contract_time": [
        r"(?:substantial|final)\s+completion\s*(?:.*?)(\d+)\s*(?:calendar|consecutive|working)?\s*days",
        r"(\d+)\s*(?:calendar|consecutive|working)\s+days\s*(?:.*?)(?:substantial|final)\s+completion",
        r"(?:contract|completion)\s+time\s*(?:.*?)(\d+)\s*(?:calendar|consecutive|working)?\s*days",
        r"time\s+(?:of|for)\s+completion",
        r"notice\s+to\s+proceed",
    ],
    "liquidated_damages": [
        r"liquidated\s+damages?\s*(?:.*?)\$\s*([\d,]+(?:\.\d+)?)\s*(?:per|each|/)\s*(?:calendar|working)?\s*day",
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:per|each|/)\s*(?:calendar|working)?\s*day\s*(?:.*?)liquidated",
        r"liquidated\s+damages?",
    ],
    "warranty": [
        r"warrant(?:y|ies)\s+(?:period|term)\s*(?:.*?)(\d+)\s*(?:year|month|day)",
        r"(\d+)\s*[\-\s]?year\s+warrant(?:y|ies)",
        r"warrant(?:y|ies)\s+(?:shall\s+be|of)\s+(\d+)",
        r"guarantee\s+(?:period|term)\s*(?:.*?)(\d+)\s*(?:year|month)",
    ],
    "contractor_license": [
        r"(?:contractor|bidder)\s+(?:shall|must)\s+(?:hold|possess|have)\s+(?:a\s+)?(?:valid\s+)?(?:\w+\s+)?license",
        r"(?:class|type)\s+[A-Z]\s+(?:contractor\s+)?license",
        r"license\s+(?:type|class|requirement)",
        r"licensed\s+(?:in|by)\s+(?:the\s+)?(?:state|commonwealth)",
    ],
    "insurance": [
        r"(?:certificate|proof)\s+of\s+insurance",
        r"(?:general|commercial)\s+liability\s*(?:.*?)\$\s*([\d,]+(?:\.\d+)?)",
        r"(?:automobile|auto|vehicle)\s+liability\s*(?:.*?)\$\s*([\d,]+(?:\.\d+)?)",
        r"(?:workers?['\u2019]?\s*compensation|worker['\u2019]?s\s+comp)",
        r"(?:umbrella|excess)\s+liability\s*(?:.*?)\$\s*([\d,]+(?:\.\d+)?)",
        r"additional\s+insured",
        r"waiver\s+of\s+subrogation",
        r"railroad\s+(?:protective|insurance)",
    ],
    "minority_dbe_goals": [
        r"(?:DBE|MBE|WBE|MWBE|minority|disadvantaged)\s+(?:goal|participation|requirement)\s*(?:.*?)(\d+)\s*(?:%|percent)",
        r"(\d+)\s*(?:%|percent)\s+(?:DBE|MBE|WBE|MWBE|minority)",
        r"good\s+faith\s+effort",
        r"(?:DBE|MBE|WBE|MWBE|minority)\s+(?:goal|participation|requirement)",
    ],
    "working_hours": [
        r"(?:working|work)\s+hours?\s*(?:.*?)(\d{1,2})\s*(?::00)?\s*(?:a\.?m\.?|AM)\s*(?:to|through|-)\s*(\d{1,2})\s*(?::00)?\s*(?:p\.?m\.?|PM)",
        r"(?:Monday|Mon)\s+(?:through|thru|to|-)\s+(?:Friday|Fri)",
        r"(?:no|prohibited)\s+(?:work|construction)\s+(?:on\s+)?(?:Saturday|Sunday|weekend|holiday)",
        r"(?:night|nighttime|evening)\s+(?:work|shift|operation)",
        r"working\s+hours\s+(?:shall\s+be|are)\s+(?:limited|restricted)",
    ],
    "subcontracting": [
        r"(?:subcontract|sub[\-\s]?contract)\s*(?:.*?)(\d+)\s*(?:%|percent)",
        r"(\d+)\s*(?:%|percent)\s*(?:.*?)(?:subcontract|sub[\-\s]?contract)",
        r"(?:list|identify)\s+(?:all\s+)?(?:subcontractor|sub[\-\s]?contractor)",
        r"(?:subcontract|sub[\-\s]?contract)\s+(?:limitation|restriction|requirement)",
    ],
    "funding": [
        r"(?:federal|state|grant|USDA|EPA|SRF|CWSRF|DWSRF)\s+(?:fund|financ|grant)",
        r"(?:fund|financ|grant)(?:ed|ing)\s+(?:by|through|from|via)\s+(?:federal|state|USDA|EPA|SRF)",
        r"(?:American\s+Rescue|ARPA|Infrastructure\s+Investment)",
    ],
    "certified_payroll": [
        r"certified\s+payroll",
        r"prevailing\s+wage",
        r"Davis[\-\s]?Bacon",
        r"wage\s+(?:rate|determination|schedule)",
    ],
    "retainage": [
        r"retainage\s*(?:.*?)(\d+)\s*(?:%|percent)",
        r"(\d+)\s*(?:%|percent)\s+(?:retainage|retention)",
        r"retainage\s+(?:shall\s+be|of|at)\s+(\d+)",
        r"(?:retain|withhold)\s+(\d+)\s*(?:%|percent)",
    ],
    "safety": [
        r"safety\s+(?:plan|program|questionnaire|manual|requirement)",
        r"(?:OSHA|MSHA)\s+(?:compliance|requirement|standard)",
        r"site[\-\s]?specific\s+safety",
        r"safety\s+(?:officer|manager|director|coordinator)",
        r"[Ss]afety\s+[Pp]rovisions",
        r"(?:electrical|construction|job\s+site|work\s+zone)\s+safety",
    ],
    "qualifications": [
        r"(?:minimum|at\s+least)\s+(\d+)\s*(?:linear\s+feet|LF)\s+(?:of\s+)?CIPP",
        r"(?:minimum|at\s+least)\s+(\d+)\s*(?:vertical\s+feet|VF)\s+(?:of\s+)?(?:manhole|MH)\s+(?:rehab|rehabilitation)",
        r"(?:minimum|at\s+least)\s+(\d+)\s+years?\s+(?:of\s+)?(?:experience|in\s+business)",
        r"(?:contractor|bidder)\s+(?:shall|must)\s+(?:have|demonstrate)\s+(?:experience|qualification)",
        r"(?:similar|comparable)\s+(?:project|work|experience)",
        r"(?:qualified|experienced)\s+(?:to\s+)?(?:provide|perform|furnish)",
        r"(?:contractor|bidder)\s+qualif",
    ],

    # ===== Section 2: Site Conditions =====
    "site_access": [
        r"(?:site|project)\s+access",
        r"(?:contractor|city|owner)\s+(?:shall\s+)?(?:provide|responsible\s+for)\s+(?:site\s+)?access",
        r"(?:access|entry)\s+(?:to|for)\s+(?:the\s+)?(?:site|work\s+area|project\s+area)",
        r"right[\-\s]?of[\-\s]?way\s+access",
        r"[Aa]ccess\s+to\s+[Ww]ork",
    ],
    "site_restoration": [
        r"(?:site|surface|pavement|road)\s+restoration",
        r"(?:restore|restoration)\s+(?:to\s+)?(?:original|existing|pre[\-\s]?construction)\s+condition",
        r"(?:contractor|city|owner)\s+(?:shall\s+)?(?:restore|responsible\s+for\s+restor)",
        r"[Cc]leaning\s+the\s+[Pp]roject\s+[Ss]ite",
        r"(?:cleanup|clean[\-\s]?up|clean\s+up)\s+(?:the\s+)?(?:site|project|work\s+area)",
    ],
    "bypass": [
        r"bypass\s+pump",
        r"(?:sewage|sewer|flow)\s+bypass",
        r"(?:temporary|temp)\s+(?:bypass|diversion|flow\s+control)",
        r"force\s+main",
        r"(\d+)[\"'\u2033\u2019]?\s*(?:inch|in\.?|diameter)\s*(?:.*?)bypass",
    ],
    "traffic_control": [
        r"(?:traffic|MOT)\s+(?:control|management|maintenance)\s+(?:plan|program)",
        r"(?:certified|approved)\s+traffic\s+control\s+plan",
        r"maintenance\s+of\s+traffic",
        r"(?:lane|road)\s+closure",
        r"(?:flagging|flagger|flag\s+person)",
        r"TRAFFIC\s+CONTROL\s+(?:LS|EA|DAY)",
        r"traffic\s+control",
    ],
    "disposal": [
        r"(?:disposal|dispose)\s+(?:of\s+)?(?:debris|waste|spoil|material)",
        r"(?:contractor|owner)\s+(?:shall\s+)?(?:provide|responsible\s+for)\s+disposal",
        r"(?:landfill|dump\s+site|disposal\s+site)",
        r"(?:debris|waste|spoil|excavated)\s+(?:removal|hauling|disposal|material)",
        r"(?:remove|haul)\s+(?:all\s+)?(?:debris|waste|spoil|excess\s+material)",
    ],
    "water_hydrant_meter": [
        r"(?:water|hydrant)\s+(?:meter|supply|source)",
        r"(?:contractor|owner)\s+(?:shall\s+)?(?:provide|supply|furnish)\s+(?:water|hydrant)",
        r"fire\s+hydrant\s+(?:meter|permit|use)",
        r"(?:potable|construction)\s+water\s+(?:supply|source)",
    ],

    # ===== Section 3: Cleaning =====
    "cleaning_method": [
        r"(?:sewer|pipe|line|storm|drain)\s+cleaning",
        r"(?:mechanical|hydraulic|high[\-\s]?pressure)\s+cleaning",
        r"(?:heavy|light|root)\s+(?:cleaning|cutting)",
        r"(?:jetting|jet\s+cleaning|hydro[\-\s]?clean)",
        r"(?:cleaning|flushing)\s+(?:of\s+)?(?:pipe|line|sewer|storm|drain)",
    ],
    "cleaning_passes": [
        r"(\d+)\s+(?:cleaning\s+)?pass(?:es)?",
        r"(?:pass|passes)\s+(?:of\s+)?cleaning",
        r"(?:standard|minimum)\s+(?:of\s+)?(\d+)\s+pass(?:es)?",
    ],
    "cleaning_notifications": [
        r"(?:door\s+hanger|notification|notice)\s*(?:.*?)(?:resident|business|homeowner|property\s+owner)",
        r"(?:24|48|72)\s+hours?\s+(?:advance\s+)?(?:notice|notification|prior)",
        r"(?:notify|notification)\s+(?:resident|homeowner|property\s+owner|business)",
    ],

    # ===== Section 4: CCTV =====
    "nassco": [
        r"NASSCO",
        r"PACP\s+(?:certified|certification|trained)",
        r"Pipeline\s+Assessment\s+(?:and\s+)?Certification\s+Program",
    ],
    "cctv_submittal_format": [
        r"CCTV\s+(?:report|data|submittal|video|inspection)\s*(?:.*?)(?:USB|digital|DVD|CD|format)",
        r"(?:USB|digital|DVD|CD)\s*(?:.*?)CCTV",
        r"(?:weekly|daily|monthly)\s+(?:CCTV\s+)?(?:USB|submittal|report)",
        r"(?:WinCan|GraniteNet|PipeLogix|ITpipes)\s+(?:format|compatible|software)",
    ],
    "cctv_notifications": [
        r"(?:door\s+hanger|notification|notice)\s*(?:.*?)(?:CCTV|inspection|televising)",
        r"(?:24|48|72)\s+hours?\s*(?:.*?)(?:CCTV|inspection|televising)",
    ],

    # ===== Section 5: CIPP =====
    "cipp_curing_method": [
        r"(?:curing|cure|installation)\s+method\s*(?:.*?)(?:steam|hot\s+water|\bUV\b|ambient\s+cur)",
        r"\b(?:steam|hot\s+water|UV)\s*cur(?:e|ing|ed)",
        r"(?:PVC|fold\s+(?:and|&)\s+form)\s+(?:lining|liner|pipe)",
        r"(?:inversion|pull[\-\s]?in)\s+(?:method|installation)",
        r"cured[\-\s]?in[\-\s]?place",
        r"(?:CMP|corrugated\s+metal)\s+(?:pipe\s+)?(?:CIPP|lining|liner)",
        r"CIPP\s+(?:LINING|lining|installation)",
        r"(?:trenchless|no[\-\s]?dig)\s+(?:pipe\s*)?lin(?:ing|er)",
        r"pipelining\s+technique",
    ],
    "cipp_cure_water": [
        r"(?:cure|curing)\s+water\s+(?:discharge|disposal|management)",
        r"(?:discharge|dispose)\s+(?:of\s+)?(?:cure|curing)\s+water",
        r"(?:frac[\-\s]?out|frac\s+out)",
        r"(?:cool\s+down|cooling)\s+(?:period|time|requirement)",
    ],
    "cipp_warranty": [
        r"(?:CIPP|liner|lining)\s+warrant(?:y|ies)\s*(?:.*?)(\d+)\s*(?:year|month)",
        r"(\d+)\s*[\-\s]?year\s+(?:CIPP|liner|lining)\s+warrant(?:y|ies)",
    ],
    "cipp_notifications": [
        r"(?:door\s+hanger|notification|notice)\s*(?:.*?)(?:CIPP|lining|liner|curing)",
        r"(?:24|48|72)\s+hours?\s*(?:.*?)(?:CIPP|lining|liner)",
    ],
    "cipp_contractor_qualifications": [
        r"(?:CIPP|lining)\s+(?:contractor|installer)\s+(?:shall|must)\s+(?:have|demonstrate|possess)",
        r"(?:minimum|at\s+least)\s+(\d+)\s*(?:linear\s+feet|LF)\s+(?:of\s+)?(?:CIPP|lining)",
        r"(?:minimum|at\s+least)\s+(\d+)\s+years?\s*(?:.*?)(?:CIPP|lining)\s+(?:experience|installation)",
    ],
    "cipp_wet_out_facility": [
        r"wet[\-\s]?out\s+(?:facility|plant|shop)",
        r"(?:own|operate)\s+(?:.*?)wet[\-\s]?out",
        r"(?:contractor|installer)\s+(?:shall|must)\s+(?:own|operate)\s+(?:.*?)wet[\-\s]?out",
    ],
    "cipp_end_seals": [
        r"end\s+seal",
        r"(?:Hydrotite|LMK|Insignia|mechanical\s+seal)",
        r"(?:terminal|end)\s+(?:point\s+)?seal",
    ],
    "cipp_mudding_the_ends": [
        r"(?:mud|mudding)\s+(?:the\s+)?end",
        r"hydraulic\s+cement\s*(?:.*?)(?:end|liner|pipe)",
        r"(?:end|terminal)\s+(?:point\s+)?(?:grouting|sealing|cementing)",
    ],
    "cipp_conditions_above": [
        r"(?:tree|powerline|power\s+line|overhead)\s*(?:.*?)(?:above|over)\s+(?:pipe|manhole|structure|MH)",
        r"(?:above|over)\s+(?:pipe|manhole|structure|MH)\s*(?:.*?)(?:tree|powerline|power\s+line|overhead)",
        r"(?:clearance|height|overhead)\s+(?:restriction|limitation|requirement)",
    ],
    "cipp_pre_liner": [
        r"pre[\-\s]?liner",
        r"(?:pre[\-\s]?liner|inner\s+liner)\s*(?:.*?)(?:infiltration|inflow|I&I|I/I)",
        r"(?:infiltration|inflow)\s*(?:.*?)pre[\-\s]?liner",
    ],
    "cipp_pipe_information": [
        r"(?:pipe|line)\s+(?:schedule|list|segment|inventory|data)",
        r"(?:diameter|length|material|depth)\s+(?:of\s+)?(?:pipe|line|sewer)",
        r"(?:LS|lump\s+sum)\s+(?:sheet|schedule|listing)\s*(?:.*?)(?:pipe|segment|line)",
    ],
    "cipp_resin_type": [
        r"(?:polyester|vinylester|vinyl\s+ester|epoxy)\s+resin",
        r"resin\s+(?:type|system|material)\s*(?:.*?)(?:polyester|vinylester|vinyl\s+ester|epoxy)",
    ],
    "cipp_testing": [
        r"(?:third[\-\s]?party|independent)\s+(?:testing|test\s+lab)",
        r"(?:PVC|plate|coupon)\s+(?:sample|specimen|test)",
        r"(?:CIPP|liner)\s+(?:test|testing|sample)\s+(?:requirement|specification)",
    ],
    "cipp_engineered_design_stamp": [
        r"(?:engineer(?:ed|ing)?|PE)\s+(?:design\s+)?(?:stamp|seal|certification)",
        r"(?:stamp|seal|certif)\s*(?:.*?)(?:design\s+)?(?:calculation|calc)",
        r"(?:professional\s+engineer|P\.?E\.?)\s+(?:shall\s+)?(?:stamp|seal|certify|sign)",
    ],
    "cipp_calculations": [
        r"(?:design|thickness|structural)\s+calculation",
        r"(?:minimum\s+)?(?:wall\s+)?thickness\s+(?:calculation|design)",
        r"(?:ASTM\s+)?F\s*1216\s+(?:calculation|design|appendix)",
    ],
    "cipp_air_testing": [
        r"(?:air|pressure)\s+test(?:ing)?\s*(?:.*?)(?:CIPP|liner|service|lateral|reinstate)",
        r"(?:reinstate|reconnect)\s+(?:service|lateral)\s*(?:.*?)(?:air|pressure)\s+test",
        r"(?:low[\-\s]?pressure\s+)?air\s+test",
    ],

    # CIPP Design & Performance Requirements
    "cipp_design_life": [
        r"design\s+life\s*(?:.*?)(\d+)\s*(?:year|yr)",
        r"(\d+)\s*[\-\s]?year\s+design\s+life",
        r"(?:service|useful|expected)\s+life\s*(?:.*?)(\d+)\s*(?:year|yr)",
    ],
    "cipp_astm_standard": [
        r"ASTM\s+[FD]\s*\d{3,4}",
        r"(?:in\s+accordance\s+with|per|comply\s+with)\s+ASTM\s+[FD]\s*\d{3,4}",
    ],
    "cipp_gravity_pipe_conditions": [
        r"(?:fully|partially)\s+deteriorated",
        r"(?:gravity\s+)?pipe\s+condition\s*(?:.*?)(?:fully|partially)\s+deteriorated",
        r"(?:existing|original)\s+pipe\s+(?:condition|is\s+not\s+providing\s+structural\s+support)",
    ],
    "cipp_flexural_strength": [
        r"flexural\s+strength\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"([\d,]+)\s*(?:psi|PSI)\s*(?:.*?)flexural\s+strength",
        r"ASTM\s+D\s*790\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
    ],
    "cipp_flexural_modulus": [
        r"flexural\s+modulus\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"([\d,]+)\s*(?:psi|PSI)\s*(?:.*?)flexural\s+modulus",
        r"(?:initial|short[\-\s]?term|long[\-\s]?term)\s+flexural\s+modulus\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
    ],
    "cipp_tensile_strength": [
        r"tensile\s+strength\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"([\d,]+)\s*(?:psi|PSI)\s*(?:.*?)tensile\s+strength",
        r"ASTM\s+D\s*638\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
    ],
    "cipp_design_safety_factor": [
        r"(?:design\s+)?safety\s+factor\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"factor\s+of\s+safety\s*[:=]?\s*(\d+(?:\.\d+)?)",
        r"\bFS\s*[:=]\s*(\d+(?:\.\d+)?)",
        r"safety\s+factor",
    ],
    "cipp_short_term_flexural_modulus": [
        r"short[\-\s]?term\s+(?:flexural\s+)?modulus\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"(?:initial|short[\-\s]?term)\s+(?:flexural\s+)?modulus\s+of\s+elasticity\s*(?:.*?)([\d,]+)",
    ],
    "cipp_long_term_flexural_modulus": [
        r"long[\-\s]?term\s+(?:flexural\s+)?modulus\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"(?:50[\-\s]?year|long[\-\s]?term)\s+(?:flexural\s+)?modulus\s+of\s+elasticity\s*(?:.*?)([\d,]+)",
    ],
    "cipp_creep_retention_factor": [
        r"creep\s+(?:retention\s+)?factor\s*(?:.*?)(\d+(?:\.\d+)?)",
        r"(?:long[\-\s]?term\s+)?creep\s*(?:.*?)(\d+(?:\.\d+)?)\s*(?:%|percent)?",
    ],
    "cipp_ovality": [
        r"ovality\s*(?:.*?)(\d+(?:\.\d+)?)\s*(?:%|percent)",
        r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s*(?:.*?)ovality",
        r"(?:pipe\s+)?(?:deflection|ovality)\s+(?:shall\s+)?(?:not\s+exceed|be\s+less\s+than)",
    ],
    "cipp_soil_modulus": [
        r"(?:soil|E'|modulus\s+of\s+soil\s+reaction)\s+modulus\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"(?:soil\s+stiffness|E[\'\u2019]s?)\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
    ],
    "cipp_soil_density": [
        r"soil\s+density\s*(?:.*?)([\d.]+)\s*(?:pcf|lb/?ft|kN/m)",
        r"(?:unit\s+weight|density)\s+of\s+soil\s*(?:.*?)([\d.]+)",
    ],
    "cipp_groundwater_depth": [
        r"groundwater\s+(?:depth|level|elevation|table)\s*(?:.*?)(\d+(?:\.\d+)?)\s*(?:ft|feet|')",
        r"(?:depth\s+to|height\s+of)\s+groundwater\s*(?:.*?)(\d+(?:\.\d+)?)",
    ],
    "cipp_live_load": [
        r"(?:live|traffic|surface|HS[\-\s]?\d+)\s+load\s*(?:.*?)([\d,]+)\s*(?:psf|psi|lb|kip)",
        r"(?:H|HS)[\-\s]?(\d+)\s+(?:loading|load|truck)",
        r"AASHTO\s+(?:H|HS)[\-\s]?(\d+)",
    ],
    "cipp_poissons_ratio": [
        r"Poisson[\'\u2019]?s?\s+ratio\s*(?:.*?)(\d+(?:\.\d+)?)",
        r"(?:mu|\u03BC|v)\s*=?\s*(\d+\.\d+)\s*(?:.*?)Poisson",
    ],

    # ===== Section 6: Manhole Rehab =====
    "mh_information": [
        r"(?:manhole|MH)\s+(?:tracker|schedule|list|inventory|data)",
        r"(?:number|quantity)\s+of\s+(?:manhole|MH)s?\s*(?:.*?)(\d+)",
        r"(\d+)\s+(?:manhole|MH)s?",
        r"(?:manhole|MH)\s+(?:diameter|depth|size|type)",
    ],
    "mh_product_type": [
        r"(?:cementitious|calcium\s+aluminate|geopolymer|epoxy|polyurea|composite)\s*(?:.*?)(?:manhole|MH|lining|coating)",
        r"(?:manhole|MH)\s+(?:lining|coating|rehabilitation)\s*(?:.*?)(?:cementitious|calcium\s+aluminate|geopolymer|epoxy|polyurea|composite)",
    ],
    "mh_products": [
        r"(?:infiltration\s+control|plug|grout|repair)\s+(?:material|product)",
        r"(?:approved\s+)?(?:product|material)\s+(?:list|schedule)\s*(?:.*?)(?:manhole|MH)",
        r"(?:chemical|cementitious)\s+grout",
    ],
    "mh_testing": [
        r"(?:cube|test)\s+sample\s*(?:.*?)(?:manhole|MH|coating|lining)",
        r"(?:vacuum|mandrel|spark|holiday)\s+test(?:ing)?\s*(?:.*?)(?:manhole|MH)",
        r"(?:wet\s+film|dry\s+film)\s+(?:thickness\s+)?gauge",
    ],
    "mh_warranty": [
        r"(?:manhole|MH)\s+(?:rehabilitation|rehab|lining|coating)\s+warrant(?:y|ies)\s*(?:.*?)(\d+)\s*(?:year|month)",
        r"(\d+)\s*[\-\s]?year\s+(?:manhole|MH)\s+(?:rehabilitation|rehab|lining|coating)\s+warrant(?:y|ies)",
    ],
    "mh_thickness": [
        r"(?:manhole|MH)\s+(?:lining|coating)\s+(?:minimum\s+)?thickness\s*(?:.*?)(\d+(?:\.\d+)?)\s*(?:inch|in|mm|mil)",
        r"(\d+(?:\.\d+)?)\s*(?:inch|in|mm|mil)\s*(?:.*?)(?:manhole|MH)\s+(?:lining|coating)",
    ],
    "mh_compressive_strength": [
        r"compressive\s+strength\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"([\d,]+)\s*(?:psi|PSI)\s*(?:.*?)compressive\s+strength",
    ],
    "mh_bond_strength": [
        r"bond\s+strength\s*(?:.*?)([\d,]+)\s*(?:psi|PSI)",
        r"([\d,]+)\s*(?:psi|PSI)\s*(?:.*?)bond\s+strength",
    ],
    "mh_shrinkage": [
        r"shrinkage\s*(?:.*?)(\d+(?:\.\d+)?)\s*(?:%|percent)",
        r"(?:linear|volumetric)\s+shrinkage",
    ],
    "mh_grout": [
        r"(?:polyurethane|acrylamide|chemical|cementitious)\s+grout",
        r"grout\s+(?:type|material|product)\s*(?:.*?)(?:polyurethane|acrylamide|chemical|cementitious)",
        r"(?:injection|chemical)\s+grouting",
    ],
    "mh_measurement_payment": [
        r"(?:measurement\s+(?:and|&)\s+payment|pay\s+item)\s*(?:.*?)(?:manhole|MH)",
        r"(?:manhole|MH)\s*(?:.*?)(?:measurement\s+(?:and|&)\s+payment|pay\s+item|line\s+item)",
        r"(?:per|each|lump\s+sum|vertical\s+foot|VF)\s*(?:.*?)(?:manhole|MH)",
    ],
    "mh_external_coating": [
        r"(?:external|exterior|outside)\s+(?:coating|manhole)\s+(?:coating|protection)",
        r"(?:coat|protect)\s+(?:the\s+)?(?:exterior|outside|external)\s+(?:of\s+)?(?:the\s+)?(?:manhole|MH)",
    ],
    "mh_notifications": [
        r"(?:door\s+hanger|notification|notice)\s*(?:.*?)(?:manhole|MH)",
        r"(?:24|48|72)\s+hours?\s*(?:.*?)(?:manhole|MH)",
    ],
    "mh_nace": [
        r"NACE\s+(?:inspector|certified|certification|standard|SP|TM)",
        r"(?:NACE\s+)?(?:holiday|spark)\s+(?:test|inspection|inspector)",
    ],
    "mh_bypass": [
        r"(?:manhole|MH)\s*(?:.*?)(?:bypass|flow[\-\s]?through|flow\s+thru)",
        r"(?:coat|line)\s+(?:the\s+)?invert",
        r"(?:bypass|flow[\-\s]?through)\s*(?:.*?)(?:manhole|MH)",
    ],
    "mh_substitution_requirements": [
        r"(?:substitution|alternate|equal)\s+(?:request|requirement|procedure)",
        r"(?:or\s+)?(?:approved\s+)?equal",
        r"(?:pre[\-\s]?approved|approved)\s+(?:product|material|manufacturer)\s+list",
    ],

    # Spincast sub-section
    "spincast_product_type": [
        r"spincast\s*(?:.*?)(?:cementitious|calcium\s+aluminate|geopolymer|epoxy|polyurea|composite)",
        r"(?:cementitious|calcium\s+aluminate|geopolymer|epoxy|polyurea)\s*(?:.*?)spincast",
        r"(?:centrifugal|spun|spin[\-\s]?cast)\s+(?:lining|coating|application)",
    ],
    "spincast_testing": [
        r"spincast\s*(?:.*?)(?:cube|test)\s+sample",
        r"(?:cube|test)\s+sample\s*(?:.*?)spincast",
    ],
    "spincast_warranty": [
        r"spincast\s*(?:.*?)warrant(?:y|ies)\s*(?:.*?)(\d+)\s*(?:year|month)",
        r"(\d+)\s*[\-\s]?year\s*(?:.*?)spincast\s+warrant(?:y|ies)",
    ],
    "spincast_thickness": [
        r"spincast\s*(?:.*?)thickness\s*(?:.*?)(\d+(?:\.\d+)?)\s*(?:inch|in|mm|mil)",
        r"(\d+(?:\.\d+)?)\s*(?:inch|in|mm|mil)\s*(?:.*?)spincast",
    ],
    "spincast_corrugations": [
        r"corrugat(?:ion|ed)\s*(?:.*?)(?:fill|smooth|remove|eliminate)",
        r"(?:fill|smooth|remove|eliminate)\s*(?:.*?)corrugat(?:ion|ed)",
    ],
}


# ---------------------------------------------------------------------------
# Guidance text from the PDF checklist "Notes" column — used in AI prompts
# ---------------------------------------------------------------------------

BID_ITEM_DESCRIPTIONS: Dict[str, str] = {
    "pre_bid": "Is there a pre-bid meeting? Is it mandatory or optional? Is it in person or is there a virtual option?",
    "submission_format": "Do we need to submit hard copies via FedEx/UPS or is it an online portal/email submission? If hardcopy, is it 1 original only? Any copies? Any USB digital copies?",
    "bid_bond": "Is there a bid bond required? Typically 5% or 10%",
    "payment_performance_bonds": "Are they required? Are they both 100%? Or is one 100% and one 110%?",
    "contract_time": "What is the substantial and final completion time? Is it consecutive days or working/week days?",
    "liquidated_damages": "Amount we need to pay if we go over contract time",
    "warranty": "How long is the project warranty? The CIPP and/or MH Rehab might have a longer warranty",
    "contractor_license": "What type of license do we need to have to bid? Any certain requirements?",
    "insurance": "Do we need a COI to submit with bid? Does the owner need to be listed as additional insured? What are the minimum coverages needed? Is additional property or railroad insurance needed?",
    "minority_dbe_goals": 'Search for: "Good Faith", "Minority", "DBE", "MBE", "Goals". Is it mandatory or a good faith effort?',
    "working_hours": "When are we allowed to work? Only Monday-Friday? Only 8:00 AM to 5:00 PM? If there's traffic control, are we limited to only working 9:00 AM to 3:00 PM or night shift?",
    "subcontracting": "How much work are we allowed to subcontract as a PRIME? Do we need to list our SUBS on bid paperwork? Any documents they need to fill out?",
    "funding": "Any grants involved? Any funding needed?",
    "certified_payroll": "Is certified payroll required?",
    "retainage": "Is there any retainage? If so, how much? Typically 5% or 10%.",
    "safety": "Any safety questionnaire we need to fill out? Send out to safety as soon as possible.",
    "qualifications": "Minimum LF of CIPP or VF of MH Rehab or years in business?",
    "site_access": "Is contractor responsible for access? Will City help at all?",
    "site_restoration": "Is contractor responsible for restoration? Will City help at all?",
    "bypass": "Is it needed? Anything 10\" or greater need to start looking at bypass for sanitary sewer. Are there any force mains discharging into the lines we are working on? Look at plans in detail if it is larger sanitary sewer",
    "traffic_control": "Is there a line item? Do we need to submit a certified traffic control plan? (additional costs typically)",
    "disposal": "Contractor to provide or Owner? What are the requirements?",
    "water_hydrant_meter": "Contractor to provide or Owner?",
    "cleaning_method": "What line items do we have to bid on? Is the line item all inclusive for mechanical, heavy cleaning, root cutting?",
    "cleaning_passes": "How many passes are included in the 'Standard' cleaning item? Typically 3 or 5.",
    "cleaning_notifications": "Do we need to leave door hangers on residences/businesses? How long before we are working on that line/manhole? (Ex: 24, 48 or 72 hours)",
    "nassco": "Ex: PACP Certified",
    "cctv_submittal_format": "USB? Digital Format? Weekly USB's?",
    "cctv_notifications": "Do we need to leave door hangers on residences/businesses? How long before we are working on that line/manhole? (Ex: 24, 48 or 72 hours)",
    "cipp_curing_method": "Ex: Air/Steam, Water, UV, PVC/Fold & Form",
    "cipp_cure_water": "If we are doing water install, are we able to let our cure water just go downstream? Do we have to discharge into a nearby sanitary sewer system? Or do we have to frac out and discharge at another location? Do we have to let the cure water cool down before we can do anything with it?",
    "cipp_warranty": "How many years for warranty?",
    "cipp_notifications": "Do we need to leave door hangers on residences/businesses? How long before we are working on that line/manhole? (Ex: 24, 48 or 72 hours)",
    "cipp_contractor_qualifications": "Certain amount of LF or years in business?",
    "cipp_wet_out_facility": "Any note that contractor must own and operate their own wet-out facility?",
    "cipp_end_seals": "Hydrotite, LMK/Insignia",
    "cipp_mudding_the_ends": "Applying hydraulic cement to the liner ends of the pipe in the MH/Structure",
    "cipp_conditions_above": "Any potential issues with install? Are there trees over top the MH/structure? Any powerlines? How far above if so for either?",
    "cipp_pre_liner": "Is a preliner required? Typically high infiltration spots",
    "cipp_pipe_information": "LS Sheet listing out Pipe Segments - Including Pipe Diameter, length, material, depths, access, TC, etc.",
    "cipp_resin_type": "Polyester, Vinylester, Epoxy, etc.",
    "cipp_testing": "Third-Party Testing Required? PVC samples? How long? Plate Samples?",
    "cipp_engineered_design_stamp": "Is the owner requiring us to engineer stamp design calculations for the CIPP?",
    "cipp_calculations": "Design calculations for minimum thickness",
    "cipp_air_testing": "Does the line have to be air tested before we can reinstate services?",
    "cipp_design_life": "Typically fifty (50) years or greater",
    "cipp_astm_standard": "ASTM F1216 - CC to add the others",
    "cipp_gravity_pipe_conditions": "Fully Deteriorated?",
    "cipp_flexural_strength": "Typically 4,500 psi (in accordance with ASTM D 790)",
    "cipp_flexural_modulus": "Typically 250,000 - 400,000 psi (in accordance with ASTM D 790)",
    "cipp_tensile_strength": "3,000 psi (in accordance with ASTM D 638)",
    "cipp_design_safety_factor": "Typically 2.0",
    "cipp_short_term_flexural_modulus": "",
    "cipp_long_term_flexural_modulus": "",
    "cipp_creep_retention_factor": "",
    "cipp_ovality": "Typically 2%",
    "cipp_soil_modulus": "",
    "cipp_soil_density": "",
    "cipp_groundwater_depth": "",
    "cipp_live_load": "",
    "cipp_poissons_ratio": "",
    "mh_information": "MH Tracker LS including # of manholes, MH numbers, diameters, MH depths, type of manholes (brick, precast, etc.), active infiltration?, access info/MOT etc.",
    "mh_product_type": "Ex: Cementitious, Calcium Aluminate, Geopolymer, Epoxy, Polyurea, Composite (cementitious + epoxy)",
    "mh_products": "Search for types of products listed/approved: Infiltration Control Materials, Plugs, Grouts, Repair Materials, etc.",
    "mh_testing": "Cube Samples, Vacuum Testing, Holiday Spark Testing, Wet Film Gauge",
    "mh_warranty": "How many years for warranty?",
    "mh_thickness": "How many inches of cementitious, calcium aluminate or geopolymer OR how many mils of epoxy/polyurea?",
    "mh_compressive_strength": "",
    "mh_bond_strength": "",
    "mh_shrinkage": "",
    "mh_grout": "Any grouts listed? Polyurethane or Acrylamide?",
    "mh_measurement_payment": "What does this line item consist of?",
    "mh_external_coating": "Does the outside of the manhole need to be coated if it is exposed?",
    "mh_notifications": "Do we need to leave door hangers on residences/businesses? How long before we are working on that manhole? (Ex: 24, 48 or 72 hours)",
    "mh_nace": "Is a NACE Inspector required?",
    "mh_bypass": "Flow through allowed? Coat Invert?",
    "mh_substitution_requirements": "",
    "spincast_product_type": "Ex: Cementitious, Calcium Aluminate, Geopolymer, Epoxy, Polyurea, Composite (cementitious + epoxy)",
    "spincast_testing": "Cube Samples",
    "spincast_warranty": "How many years for warranty?",
    "spincast_thickness": "How many inches of cementitious, calcium aluminate or geopolymer OR how many mils of epoxy/polyurea?",
    "spincast_corrugations": "What size corrugations on pipe? Do we need to fill in corrugations?",
}


# ---------------------------------------------------------------------------
# Fallback keyword phrases for items where regex may miss
# Used by BidReviewEngine._keyword_search when regex finds nothing
# ---------------------------------------------------------------------------

SEARCH_KEYWORDS: Dict[str, List[str]] = {
    "pre_bid": ["pre-bid", "pre bid", "pre-bid meeting", "pre-bid conference", "site visit", "Teams webinar", "Zoom meeting"],
    "submission_format": ["submit", "submission", "portal", "bonfire", "bidexpress", "hard copy", "electronic", "online", "email bid", "sealed bid"],
    "bid_bond": ["bid bond", "bid security", "bid guarantee", "bid deposit"],
    "payment_performance_bonds": ["performance bond", "payment bond", "surety bond", "faithful performance"],
    "contract_time": ["calendar days", "working days", "substantial completion", "final completion", "contract time", "notice to proceed", "NTP"],
    "liquidated_damages": ["liquidated damage", "per day", "per calendar day"],
    "warranty": ["warranty", "guarantee period", "correction period", "defect"],
    "contractor_license": ["license", "licensed", "registration", "registered contractor"],
    "insurance": ["insurance", "liability", "workers compensation", "additional insured", "certificate of insurance", "COI", "waiver of subrogation"],
    "minority_dbe_goals": ["minority", "DBE", "MBE", "WBE", "MWBE", "disadvantaged business", "good faith effort", "equal opportunity"],
    "working_hours": ["working hours", "work hours", "Monday through Friday", "night work", "weekend", "work schedule"],
    "subcontracting": ["subcontract", "sub-contract", "subcontractor listing", "self-perform"],
    "funding": ["federal fund", "state fund", "grant", "USDA", "EPA", "SRF", "ARPA", "Infrastructure Investment"],
    "certified_payroll": ["certified payroll", "prevailing wage", "Davis-Bacon", "wage rate", "wage determination"],
    "retainage": ["retainage", "retention", "retain", "withhold"],
    "safety": ["safety", "OSHA", "safety plan", "safety program", "safety provision"],
    "qualifications": ["qualif", "experience", "years in business", "similar project", "references"],
    "site_access": ["site access", "access to work", "right-of-way", "ROW access", "project access"],
    "site_restoration": ["restoration", "restore", "cleanup", "clean up", "repair damage", "final cleanup"],
    "bypass": ["bypass pump", "flow bypass", "dewatering", "pump around", "temporary diversion"],
    "traffic_control": ["traffic control", "MOT", "maintenance of traffic", "lane closure", "road closure", "flagging", "flagger"],
    "disposal": ["disposal", "debris removal", "waste removal", "haul off", "spoil disposal", "excess material"],
    "water_hydrant_meter": ["water meter", "hydrant meter", "construction water", "water supply", "fire hydrant"],
    "cleaning_method": ["cleaning", "flushing", "jetting", "hydro clean", "pipe cleaning"],
    "cleaning_passes": ["cleaning pass", "number of passes"],
    "cleaning_notifications": ["door hanger", "notification", "advance notice", "notify resident"],
    "nassco": ["NASSCO", "PACP", "Pipeline Assessment"],
    "cctv_submittal_format": ["CCTV", "television", "video inspection", "camera inspection"],
    "cctv_notifications": ["CCTV", "inspection notification"],
    "cipp_curing_method": ["CIPP", "cured-in-place", "cured in place", "pipelining", "CMP lining", "pipe lining", "trenchless lining"],
    "cipp_pipe_information": ["pipe schedule", "line segment", "pipe diameter", "pipe length", "pipe inventory", "bid item", "line item"],
    "cipp_warranty": ["CIPP warranty", "liner warranty", "lining warranty"],
    "cipp_contractor_qualifications": ["CIPP experience", "lining experience", "installer qualification"],
}


# ---------------------------------------------------------------------------
# Maps item_key -> (section_key, display_name) for engine/UI translation
# ---------------------------------------------------------------------------

BID_ITEM_MAP: Dict[str, Tuple[str, str]] = {
    # Section 1: Standard Contract Items
    "pre_bid": ("standard_contract_items", "Pre-Bid"),
    "submission_format": ("standard_contract_items", "Submission Format"),
    "bid_bond": ("standard_contract_items", "Bid Bond"),
    "payment_performance_bonds": ("standard_contract_items", "Payment & Performance Bonds"),
    "contract_time": ("standard_contract_items", "Contract Time"),
    "liquidated_damages": ("standard_contract_items", "Liquidated Damages"),
    "warranty": ("standard_contract_items", "Warranty"),
    "contractor_license": ("standard_contract_items", "Contractor License"),
    "insurance": ("standard_contract_items", "Insurance"),
    "minority_dbe_goals": ("standard_contract_items", "Minority/DBE Goals"),
    "working_hours": ("standard_contract_items", "Working Hours"),
    "subcontracting": ("standard_contract_items", "Subcontracting"),
    "funding": ("standard_contract_items", "Funding"),
    "certified_payroll": ("standard_contract_items", "Certified Payroll"),
    "retainage": ("standard_contract_items", "Retainage"),
    "safety": ("standard_contract_items", "Safety"),
    "qualifications": ("standard_contract_items", "Qualifications"),
    # Section 2: Site Conditions
    "site_access": ("site_conditions", "Site Access"),
    "site_restoration": ("site_conditions", "Site Restoration"),
    "bypass": ("site_conditions", "Bypass"),
    "traffic_control": ("site_conditions", "Traffic Control"),
    "disposal": ("site_conditions", "Disposal"),
    "water_hydrant_meter": ("site_conditions", "Water & Hydrant Meter"),
    # Section 3: Cleaning
    "cleaning_method": ("cleaning", "Cleaning Method"),
    "cleaning_passes": ("cleaning", "Cleaning Passes"),
    "cleaning_notifications": ("cleaning", "Notifications"),
    # Section 4: CCTV
    "nassco": ("cctv", "NASSCO"),
    "cctv_submittal_format": ("cctv", "CCTV Submittal Format"),
    "cctv_notifications": ("cctv", "Notifications"),
    # Section 5: CIPP
    "cipp_curing_method": ("cipp", "Curing Method"),
    "cipp_cure_water": ("cipp", "Cure Water"),
    "cipp_warranty": ("cipp", "Warranty"),
    "cipp_notifications": ("cipp", "Notifications"),
    "cipp_contractor_qualifications": ("cipp", "Contractor Qualifications"),
    "cipp_wet_out_facility": ("cipp", "Wet-Out Facility"),
    "cipp_end_seals": ("cipp", "End Seals"),
    "cipp_mudding_the_ends": ("cipp", "Mudding the Ends"),
    "cipp_conditions_above": ("cipp", "Conditions Above Pipes/Overhead"),
    "cipp_pre_liner": ("cipp", "Pre-Liner"),
    "cipp_pipe_information": ("cipp", "Pipe Information"),
    "cipp_resin_type": ("cipp", "Resin Type"),
    "cipp_testing": ("cipp", "Testing"),
    "cipp_engineered_design_stamp": ("cipp", "Engineered Design Stamp"),
    "cipp_calculations": ("cipp", "Calculations"),
    "cipp_air_testing": ("cipp", "Air Testing"),
    # CIPP Design Requirements
    "cipp_design_life": ("cipp.design_performance_requirements", "Design Life"),
    "cipp_astm_standard": ("cipp.design_performance_requirements", "ASTM Standard"),
    "cipp_gravity_pipe_conditions": ("cipp.design_performance_requirements", "Gravity Pipe Conditions"),
    "cipp_flexural_strength": ("cipp.design_performance_requirements", "Flexural Strength"),
    "cipp_flexural_modulus": ("cipp.design_performance_requirements", "Flexural Modulus"),
    "cipp_tensile_strength": ("cipp.design_performance_requirements", "Tensile Strength"),
    "cipp_design_safety_factor": ("cipp.design_performance_requirements", "Design Safety Factor"),
    "cipp_short_term_flexural_modulus": ("cipp.design_performance_requirements", "Short-Term Flexural Modulus"),
    "cipp_long_term_flexural_modulus": ("cipp.design_performance_requirements", "Long-Term Flexural Modulus"),
    "cipp_creep_retention_factor": ("cipp.design_performance_requirements", "Creep Retention Factor"),
    "cipp_ovality": ("cipp.design_performance_requirements", "Ovality"),
    "cipp_soil_modulus": ("cipp.design_performance_requirements", "Soil Modulus"),
    "cipp_soil_density": ("cipp.design_performance_requirements", "Soil Density"),
    "cipp_groundwater_depth": ("cipp.design_performance_requirements", "Groundwater Depth"),
    "cipp_live_load": ("cipp.design_performance_requirements", "Live Load"),
    "cipp_poissons_ratio": ("cipp.design_performance_requirements", "Poisson's Ratio"),
    # Section 6: Manhole Rehab
    "mh_information": ("manhole_rehab", "MH Information"),
    "mh_product_type": ("manhole_rehab", "Product Type"),
    "mh_products": ("manhole_rehab", "Products"),
    "mh_testing": ("manhole_rehab", "Testing"),
    "mh_warranty": ("manhole_rehab", "Warranty"),
    "mh_thickness": ("manhole_rehab", "Thickness"),
    "mh_compressive_strength": ("manhole_rehab", "Compressive Strength"),
    "mh_bond_strength": ("manhole_rehab", "Bond Strength"),
    "mh_shrinkage": ("manhole_rehab", "Shrinkage"),
    "mh_grout": ("manhole_rehab", "Grout"),
    "mh_measurement_payment": ("manhole_rehab", "Measurement & Payment"),
    "mh_external_coating": ("manhole_rehab", "External Coating"),
    "mh_notifications": ("manhole_rehab", "Notifications"),
    "mh_nace": ("manhole_rehab", "NACE"),
    "mh_bypass": ("manhole_rehab", "Bypass"),
    "mh_substitution_requirements": ("manhole_rehab", "Substitution Requirements"),
    # Spincast
    "spincast_product_type": ("manhole_rehab.spincast", "Product Type"),
    "spincast_testing": ("manhole_rehab.spincast", "Testing"),
    "spincast_warranty": ("manhole_rehab.spincast", "Warranty"),
    "spincast_thickness": ("manhole_rehab.spincast", "Thickness"),
    "spincast_corrugations": ("manhole_rehab.spincast", "Corrugations"),
}


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_bid_spec_items(text: str) -> Dict[str, List[Dict]]:
    """
    Run all bid spec regex patterns against the contract text.

    Returns a dict of item_key -> list of match dicts, where each match has:
      - matched_text: the full matched string
      - captured_value: first capture group value (if any)
      - position: character offset in text
      - context: surrounding text snippet
    """
    results: Dict[str, List[Dict]] = {}
    text_lower = text.lower()

    for item_key, patterns in BID_SPEC_PATTERNS.items():
        matches = []
        for pattern in patterns:
            try:
                for m in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                    start = max(0, m.start() - 500)
                    end = min(len(text), m.end() + 500)
                    matches.append({
                        "matched_text": m.group(0),
                        "captured_value": m.group(1) if m.lastindex and m.lastindex >= 1 else "",
                        "position": m.start(),
                        "context": text[start:end],
                    })
            except re.error as e:
                logger.warning("Regex error for %s pattern %r: %s", item_key, pattern, e)

        if matches:
            # Deduplicate by position (keep earliest per unique position)
            seen_positions = set()
            unique = []
            for match in sorted(matches, key=lambda x: x["position"]):
                if match["position"] not in seen_positions:
                    seen_positions.add(match["position"])
                    unique.append(match)
            results[item_key] = unique

    logger.info(
        "Bid spec regex extraction: found matches for %d/%d items",
        len(results), len(BID_SPEC_PATTERNS),
    )
    return results
