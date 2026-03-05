"""
Bid Review Data Models

Dataclasses for the Bid Specification Review Checklist analysis type.
Each checklist item extracts a specific value from bid specs rather than
performing legal risk analysis.
"""

import logging
from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.analysis_models import ContractMetadata

logger = logging.getLogger(__name__)


@dataclass
class ChecklistItem:
    """A single checklist item with an extracted value from a bid spec."""
    value: str = ""
    location: str = ""
    confidence: str = "not_found"  # high, medium, low, not_found
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "location": self.location,
            "confidence": self.confidence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data) -> "ChecklistItem":
        if data is None:
            return cls()
        if isinstance(data, str):
            return cls(value=data, confidence="high" if data else "not_found")
        return cls(
            value=data.get("value", ""),
            location=data.get("location", ""),
            confidence=data.get("confidence", "not_found"),
            notes=data.get("notes", ""),
        )

    @property
    def found(self) -> bool:
        return self.confidence != "not_found" and bool(self.value)


# ---------------------------------------------------------------------------
# Section dataclasses
# ---------------------------------------------------------------------------

# Display-name -> field-name mapping for each section is stored as a class
# attribute FIELD_MAP so the engine/UI can translate between the two.


@dataclass
class StandardContractItems:
    """Section 1: Standard Contract Items (17 items)."""
    pre_bid: Optional[ChecklistItem] = None
    submission_format: Optional[ChecklistItem] = None
    bid_bond: Optional[ChecklistItem] = None
    payment_performance_bonds: Optional[ChecklistItem] = None
    contract_time: Optional[ChecklistItem] = None
    liquidated_damages: Optional[ChecklistItem] = None
    warranty: Optional[ChecklistItem] = None
    contractor_license: Optional[ChecklistItem] = None
    insurance: Optional[ChecklistItem] = None
    minority_dbe_goals: Optional[ChecklistItem] = None
    working_hours: Optional[ChecklistItem] = None
    subcontracting: Optional[ChecklistItem] = None
    funding: Optional[ChecklistItem] = None
    certified_payroll: Optional[ChecklistItem] = None
    retainage: Optional[ChecklistItem] = None
    safety: Optional[ChecklistItem] = None
    qualifications: Optional[ChecklistItem] = None

    FIELD_MAP = {
        "Pre-Bid": "pre_bid",
        "Submission Format": "submission_format",
        "Bid Bond": "bid_bond",
        "Payment & Performance Bonds": "payment_performance_bonds",
        "Contract Time": "contract_time",
        "Liquidated Damages": "liquidated_damages",
        "Warranty": "warranty",
        "Contractor License": "contractor_license",
        "Insurance": "insurance",
        "Minority/DBE Goals": "minority_dbe_goals",
        "Working Hours": "working_hours",
        "Subcontracting": "subcontracting",
        "Funding": "funding",
        "Certified Payroll": "certified_payroll",
        "Retainage": "retainage",
        "Safety": "safety",
        "Qualifications": "qualifications",
    }

    def to_dict(self) -> Dict[str, Any]:
        return _section_to_dict(self)

    @classmethod
    def from_dict(cls, data) -> "StandardContractItems":
        return _section_from_dict(cls, data)


@dataclass
class SiteConditions:
    """Section 2: Site Conditions Contract Items (6 items)."""
    site_access: Optional[ChecklistItem] = None
    site_restoration: Optional[ChecklistItem] = None
    bypass: Optional[ChecklistItem] = None
    traffic_control: Optional[ChecklistItem] = None
    disposal: Optional[ChecklistItem] = None
    water_hydrant_meter: Optional[ChecklistItem] = None

    FIELD_MAP = {
        "Site Access": "site_access",
        "Site Restoration": "site_restoration",
        "Bypass": "bypass",
        "Traffic Control": "traffic_control",
        "Disposal": "disposal",
        "Water & Hydrant Meter": "water_hydrant_meter",
    }

    def to_dict(self) -> Dict[str, Any]:
        return _section_to_dict(self)

    @classmethod
    def from_dict(cls, data) -> "SiteConditions":
        return _section_from_dict(cls, data)


@dataclass
class Cleaning:
    """Section 3: Cleaning (3 items)."""
    cleaning_method: Optional[ChecklistItem] = None
    cleaning_passes: Optional[ChecklistItem] = None
    notifications: Optional[ChecklistItem] = None

    FIELD_MAP = {
        "Cleaning Method": "cleaning_method",
        "Cleaning Passes": "cleaning_passes",
        "Notifications": "notifications",
    }

    def to_dict(self) -> Dict[str, Any]:
        return _section_to_dict(self)

    @classmethod
    def from_dict(cls, data) -> "Cleaning":
        return _section_from_dict(cls, data)


@dataclass
class CCTV:
    """Section 4: CCTV (3 items)."""
    nassco: Optional[ChecklistItem] = None
    cctv_submittal_format: Optional[ChecklistItem] = None
    notifications: Optional[ChecklistItem] = None

    FIELD_MAP = {
        "NASSCO": "nassco",
        "CCTV Submittal Format": "cctv_submittal_format",
        "Notifications": "notifications",
    }

    def to_dict(self) -> Dict[str, Any]:
        return _section_to_dict(self)

    @classmethod
    def from_dict(cls, data) -> "CCTV":
        return _section_from_dict(cls, data)


@dataclass
class CIPPDesignRequirements:
    """CIPP Design & Performance Requirements sub-section (16 items)."""
    design_life: Optional[ChecklistItem] = None
    astm_standard: Optional[ChecklistItem] = None
    gravity_pipe_conditions: Optional[ChecklistItem] = None
    flexural_strength: Optional[ChecklistItem] = None
    flexural_modulus: Optional[ChecklistItem] = None
    tensile_strength: Optional[ChecklistItem] = None
    design_safety_factor: Optional[ChecklistItem] = None
    short_term_flexural_modulus: Optional[ChecklistItem] = None
    long_term_flexural_modulus: Optional[ChecklistItem] = None
    creep_retention_factor: Optional[ChecklistItem] = None
    ovality: Optional[ChecklistItem] = None
    soil_modulus: Optional[ChecklistItem] = None
    soil_density: Optional[ChecklistItem] = None
    groundwater_depth: Optional[ChecklistItem] = None
    live_load: Optional[ChecklistItem] = None
    poissons_ratio: Optional[ChecklistItem] = None

    FIELD_MAP = {
        "Design Life": "design_life",
        "ASTM Standard": "astm_standard",
        "Gravity Pipe Conditions": "gravity_pipe_conditions",
        "Flexural Strength": "flexural_strength",
        "Flexural Modulus": "flexural_modulus",
        "Tensile Strength": "tensile_strength",
        "Design Safety Factor": "design_safety_factor",
        "Short-Term Flexural Modulus": "short_term_flexural_modulus",
        "Long-Term Flexural Modulus": "long_term_flexural_modulus",
        "Creep Retention Factor": "creep_retention_factor",
        "Ovality": "ovality",
        "Soil Modulus": "soil_modulus",
        "Soil Density": "soil_density",
        "Groundwater Depth": "groundwater_depth",
        "Live Load": "live_load",
        "Poisson's Ratio": "poissons_ratio",
    }

    def to_dict(self) -> Dict[str, Any]:
        return _section_to_dict(self)

    @classmethod
    def from_dict(cls, data) -> "CIPPDesignRequirements":
        return _section_from_dict(cls, data)


@dataclass
class CIPPItems:
    """Section 5: CIPP (18 items + design sub-section)."""
    curing_method: Optional[ChecklistItem] = None
    cure_water: Optional[ChecklistItem] = None
    warranty: Optional[ChecklistItem] = None
    notifications: Optional[ChecklistItem] = None
    contractor_qualifications: Optional[ChecklistItem] = None
    wet_out_facility: Optional[ChecklistItem] = None
    end_seals: Optional[ChecklistItem] = None
    mudding_the_ends: Optional[ChecklistItem] = None
    conditions_above_pipes: Optional[ChecklistItem] = None
    pre_liner: Optional[ChecklistItem] = None
    pipe_information: Optional[ChecklistItem] = None
    resin_type: Optional[ChecklistItem] = None
    testing: Optional[ChecklistItem] = None
    engineered_design_stamp: Optional[ChecklistItem] = None
    calculations: Optional[ChecklistItem] = None
    air_testing: Optional[ChecklistItem] = None
    design_requirements: Optional[CIPPDesignRequirements] = None

    FIELD_MAP = {
        "Curing Method": "curing_method",
        "Cure Water": "cure_water",
        "Warranty": "warranty",
        "Notifications": "notifications",
        "Contractor Qualifications": "contractor_qualifications",
        "Wet-Out Facility": "wet_out_facility",
        "End Seals": "end_seals",
        "Mudding the Ends": "mudding_the_ends",
        "Conditions Above Pipes/Overhead": "conditions_above_pipes",
        "Pre-Liner": "pre_liner",
        "Pipe Information": "pipe_information",
        "Resin Type": "resin_type",
        "Testing": "testing",
        "Engineered Design Stamp": "engineered_design_stamp",
        "Calculations": "calculations",
        "Air Testing": "air_testing",
    }

    def to_dict(self) -> Dict[str, Any]:
        d = _section_to_dict(self)
        if self.design_requirements:
            d["design_performance_requirements"] = self.design_requirements.to_dict()
        else:
            d["design_performance_requirements"] = {}
        return d

    @classmethod
    def from_dict(cls, data) -> "CIPPItems":
        if data is None:
            return cls()
        obj = _section_from_dict(cls, data)
        design_data = data.get("design_performance_requirements")
        if design_data and isinstance(design_data, dict):
            obj.design_requirements = CIPPDesignRequirements.from_dict(design_data)
        return obj


@dataclass
class SpincastItems:
    """Spincast sub-section of Manhole Rehab (5 items)."""
    product_type: Optional[ChecklistItem] = None
    testing: Optional[ChecklistItem] = None
    warranty: Optional[ChecklistItem] = None
    thickness: Optional[ChecklistItem] = None
    corrugations: Optional[ChecklistItem] = None

    FIELD_MAP = {
        "Product Type": "product_type",
        "Testing": "testing",
        "Warranty": "warranty",
        "Thickness": "thickness",
        "Corrugations": "corrugations",
    }

    def to_dict(self) -> Dict[str, Any]:
        return _section_to_dict(self)

    @classmethod
    def from_dict(cls, data) -> "SpincastItems":
        return _section_from_dict(cls, data)


@dataclass
class ManholeRehab:
    """Section 6: Manhole Rehab (16 items + spincast sub-section)."""
    mh_information: Optional[ChecklistItem] = None
    product_type: Optional[ChecklistItem] = None
    products: Optional[ChecklistItem] = None
    testing: Optional[ChecklistItem] = None
    warranty: Optional[ChecklistItem] = None
    thickness: Optional[ChecklistItem] = None
    compressive_strength: Optional[ChecklistItem] = None
    bond_strength: Optional[ChecklistItem] = None
    shrinkage: Optional[ChecklistItem] = None
    grout: Optional[ChecklistItem] = None
    measurement_payment: Optional[ChecklistItem] = None
    external_coating: Optional[ChecklistItem] = None
    notifications: Optional[ChecklistItem] = None
    nace: Optional[ChecklistItem] = None
    bypass: Optional[ChecklistItem] = None
    substitution_requirements: Optional[ChecklistItem] = None
    spincast: Optional[SpincastItems] = None

    FIELD_MAP = {
        "MH Information": "mh_information",
        "Product Type": "product_type",
        "Products": "products",
        "Testing": "testing",
        "Warranty": "warranty",
        "Thickness": "thickness",
        "Compressive Strength": "compressive_strength",
        "Bond Strength": "bond_strength",
        "Shrinkage": "shrinkage",
        "Grout": "grout",
        "Measurement & Payment": "measurement_payment",
        "External Coating": "external_coating",
        "Notifications": "notifications",
        "NACE": "nace",
        "Bypass": "bypass",
        "Substitution Requirements": "substitution_requirements",
    }

    def to_dict(self) -> Dict[str, Any]:
        d = _section_to_dict(self)
        if self.spincast:
            d["spincast"] = self.spincast.to_dict()
        else:
            d["spincast"] = {}
        return d

    @classmethod
    def from_dict(cls, data) -> "ManholeRehab":
        if data is None:
            return cls()
        obj = _section_from_dict(cls, data)
        spincast_data = data.get("spincast")
        if spincast_data and isinstance(spincast_data, dict):
            obj.spincast = SpincastItems.from_dict(spincast_data)
        return obj


# ---------------------------------------------------------------------------
# Top-level result
# ---------------------------------------------------------------------------

@dataclass
class BidChecklistResult:
    """Top-level result for a bid specification review checklist analysis."""
    schema_version: str = "v1.0.0"
    project_info: Dict[str, str] = field(default_factory=dict)
    standard_contract_items: StandardContractItems = field(default_factory=StandardContractItems)
    site_conditions: SiteConditions = field(default_factory=SiteConditions)
    cleaning: Cleaning = field(default_factory=Cleaning)
    cctv: CCTV = field(default_factory=CCTV)
    cipp: CIPPItems = field(default_factory=CIPPItems)
    manhole_rehab: ManholeRehab = field(default_factory=ManholeRehab)
    metadata: Optional[ContractMetadata] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "_analysis_type": "bid_checklist",
            "schema_version": self.schema_version,
            "project_info": self.project_info,
            "standard_contract_items": self.standard_contract_items.to_dict(),
            "site_conditions": self.site_conditions.to_dict(),
            "cleaning": self.cleaning.to_dict(),
            "cctv": self.cctv.to_dict(),
            "cipp": self.cipp.to_dict(),
            "manhole_rehab": self.manhole_rehab.to_dict(),
        }
        if self.metadata:
            d["metadata"] = self.metadata.to_dict()
        return d

    @classmethod
    def from_dict(cls, data) -> "BidChecklistResult":
        if data is None:
            return cls()
        result = cls(
            schema_version=data.get("schema_version", "v1.0.0"),
            project_info=data.get("project_info", {}),
            standard_contract_items=StandardContractItems.from_dict(
                data.get("standard_contract_items", {})
            ),
            site_conditions=SiteConditions.from_dict(
                data.get("site_conditions", {})
            ),
            cleaning=Cleaning.from_dict(data.get("cleaning", {})),
            cctv=CCTV.from_dict(data.get("cctv", {})),
            cipp=CIPPItems.from_dict(data.get("cipp", {})),
            manhole_rehab=ManholeRehab.from_dict(data.get("manhole_rehab", {})),
        )
        metadata = data.get("metadata")
        if metadata:
            result.metadata = ContractMetadata.from_dict(metadata)
        return result

    def get_completion_stats(self) -> Dict[str, Any]:
        """Return completion statistics across all sections."""
        sections = {
            "Standard Contract Items": self.standard_contract_items,
            "Site Conditions": self.site_conditions,
            "Cleaning": self.cleaning,
            "CCTV": self.cctv,
            "CIPP": self.cipp,
            "Manhole Rehab": self.manhole_rehab,
        }
        total = 0
        found = 0
        per_section = {}

        for section_name, section_obj in sections.items():
            s_total, s_found = _count_section(section_obj)
            total += s_total
            found += s_found
            per_section[section_name] = {"total": s_total, "found": s_found}

        return {
            "total_items": total,
            "found_count": found,
            "not_found_count": total - found,
            "completion_pct": round(found / total * 100, 1) if total else 0.0,
            "per_section": per_section,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section_to_dict(section_obj) -> Dict[str, Any]:
    """Serialize a section dataclass to dict using its FIELD_MAP."""
    fmap = getattr(section_obj, "FIELD_MAP", {})
    inv = {v: k for k, v in fmap.items()}
    result = {}
    for f in fields(section_obj):
        if f.name == "FIELD_MAP":
            continue
        val = getattr(section_obj, f.name)
        display_name = inv.get(f.name, f.name)
        if isinstance(val, ChecklistItem):
            result[display_name] = val.to_dict()
        elif val is None:
            result[display_name] = ChecklistItem().to_dict()
        # Skip sub-objects (design_requirements, spincast) — handled by caller
    return result


def _section_from_dict(cls, data):
    """Deserialize a section dataclass from dict using its FIELD_MAP."""
    if data is None:
        return cls()
    fmap = getattr(cls, "FIELD_MAP", {})
    kwargs = {}
    for display_name, field_name in fmap.items():
        item_data = data.get(display_name)
        if item_data is not None:
            kwargs[field_name] = ChecklistItem.from_dict(item_data)
    return cls(**kwargs)


def _count_section(section_obj) -> tuple:
    """Count (total, found) ChecklistItem fields in a section, including sub-sections."""
    total = 0
    found = 0
    # Known sub-section field names and their expected item counts
    SUB_SECTION_COUNTS = {
        "design_requirements": 16,  # CIPPDesignRequirements
        "spincast": 5,              # SpincastItems
    }
    for f in fields(section_obj):
        if f.name == "FIELD_MAP":
            continue
        val = getattr(section_obj, f.name)
        if isinstance(val, ChecklistItem):
            total += 1
            if val.found:
                found += 1
        elif val is not None and hasattr(val, "FIELD_MAP"):
            # Sub-section (CIPPDesignRequirements, SpincastItems)
            s_total, s_found = _count_section(val)
            total += s_total
            found += s_found
        elif val is None:
            fmap = getattr(section_obj, "FIELD_MAP", {})
            if f.name in fmap.values():
                # It's a ChecklistItem field that's None
                total += 1
            elif f.name in SUB_SECTION_COUNTS:
                # It's a None sub-section — count its expected items
                total += SUB_SECTION_COUNTS[f.name]
    return total, found
