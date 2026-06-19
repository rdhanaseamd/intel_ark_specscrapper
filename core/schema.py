"""
Flat specification record for Intel Xeon datacenter processors.

One product = one row. Field order below is canonical and matches the
source spreadsheet exactly, so to_row()/HEADER can drive CSV export
directly. Wafer fields are intentionally NOT here yet; they will be
appended as optional columns later without disturbing this order.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

# Canonical column order (do not reorder — CSV export depends on it).
FIELD_ORDER = [
    "Product", "UPFM_ID", "OPN", "OPN_Wave", "OPN_Slot", "OPN_Sub_Slot",
    "Active", "Model", "Processor_Name", "Wafer", "CCD_Technology",
    "IOD_Technology", "Package", "SOC_Config", "CCD_Count", "CCD_Cores",
    "Density", "_1P_2P", "TDP", "cTDP_Min", "cTDP_Max", "PPT_Min", "PPT_Max",
    "L3_Cache", "IRM_Group", "Prime_Sub", "CCD_Distribution",
    "IOD_Distribution", "Sweeper", "Roadmap", "Target_Customer",
    "Target_Workload", "_1kU", "ASP", "Forecast_Start_Date", "Threads",
    "SMT", "Fbase_Low", "Fbase_High", "Fbase", "Fmax_Low", "Fmax_High",
    "Fmax", "All_Core_Boost_Freq", "DDR_Channels", "Max_DDR_Rate",
    "DIMM_Technology", "GMI", "PCIe_Lanes", "PCIe_Generation", "TPL_Version",
]

# Fields the spec marks mandatory. Used by the (manual) validation step to
# flag rows that are missing required data before you approve them.
MANDATORY = {
    "Product", "OPN", "Active", "Model", "Processor_Name", "CCD_Technology",
    "Package", "Density", "_1P_2P", "TDP", "L3_Cache", "Roadmap",
    "Target_Customer", "Target_Workload", "_1kU", "Forecast_Start_Date",
    "Threads", "SMT", "Fbase_Low", "Fbase_High", "Fbase", "Fmax_Low",
    "Fmax_High", "Fmax", "All_Core_Boost_Freq", "DDR_Channels",
    "Max_DDR_Rate", "DIMM_Technology", "GMI", "PCIe_Lanes", "PCIe_Generation",
}


@dataclass
class SpecRecord:
    # --- identity / product ---
    Product: Optional[str] = None
    UPFM_ID: Optional[str] = None
    OPN: Optional[str] = None
    OPN_Wave: Optional[str] = None
    OPN_Slot: Optional[str] = None
    OPN_Sub_Slot: Optional[str] = None
    Active: Optional[str] = None
    Model: Optional[str] = None
    Processor_Name: Optional[str] = None
    Wafer: Optional[str] = None
    # --- silicon / package ---
    CCD_Technology: Optional[str] = None
    IOD_Technology: Optional[str] = None
    Package: Optional[str] = None
    SOC_Config: Optional[str] = None
    CCD_Count: Optional[str] = None
    CCD_Cores: Optional[str] = None
    Density: Optional[str] = None
    _1P_2P: Optional[str] = None
    # --- power ---
    TDP: Optional[str] = None
    cTDP_Min: Optional[str] = None
    cTDP_Max: Optional[str] = None
    PPT_Min: Optional[str] = None
    PPT_Max: Optional[str] = None
    # --- cache / internal grouping ---
    L3_Cache: Optional[str] = None
    IRM_Group: Optional[str] = None
    Prime_Sub: Optional[str] = None
    CCD_Distribution: Optional[str] = None
    IOD_Distribution: Optional[str] = None
    Sweeper: Optional[str] = None
    # --- business / positioning ---
    Roadmap: Optional[str] = None
    Target_Customer: Optional[str] = None
    Target_Workload: Optional[str] = None
    _1kU: Optional[str] = None
    ASP: Optional[str] = None
    Forecast_Start_Date: Optional[str] = None
    # --- threads / frequency ---
    Threads: Optional[str] = None
    SMT: Optional[str] = None
    Fbase_Low: Optional[str] = None
    Fbase_High: Optional[str] = None
    Fbase: Optional[str] = None
    Fmax_Low: Optional[str] = None
    Fmax_High: Optional[str] = None
    Fmax: Optional[str] = None
    All_Core_Boost_Freq: Optional[str] = None
    # --- memory / IO ---
    DDR_Channels: Optional[str] = None
    Max_DDR_Rate: Optional[str] = None
    DIMM_Technology: Optional[str] = None
    GMI: Optional[str] = None
    PCIe_Lanes: Optional[str] = None
    PCIe_Generation: Optional[str] = None
    TPL_Version: Optional[str] = None  # per spec: not applicable, leave empty

    def to_row(self) -> dict:
        """Ordered dict matching FIELD_ORDER, blanks as empty string."""
        d = asdict(self)
        return {k: ("" if d.get(k) is None else d.get(k)) for k in FIELD_ORDER}

    def missing_mandatory(self) -> list:
        """Mandatory fields that are empty — surfaced for your manual sign-off."""
        d = asdict(self)
        return [k for k in MANDATORY if not d.get(k) and d.get(k) != 0]
