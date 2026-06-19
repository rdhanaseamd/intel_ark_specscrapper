"""
IntelArkAgent — turns raw ARK rows into flat SpecRecords.

- `direct` fields are copied generically from the fields.yaml map (config-driven:
  add a direct field there, no code change here).
- `derived` fields are computed explicitly via core.derive (OPN, Product, SMT,
  frequency bounds, memory rate/tech, PCIe gen).
- `manual`/`unused` fields are left blank.

Raw-string parsing (e.g. "2.80 GHz" -> 2.80) lives here, close to the source
quirks. Keys read out of the raw row are marked `# VERIFY` where the ARK field
name is a guess.
"""

import re
from pathlib import Path
from typing import List, Optional

import yaml

from specagents.core.base_agent import Agent
from specagents.core.schema import SpecRecord
from specagents.core import derive
from specagents.agents.intel_ark import fetcher

FIELDS_YAML = Path(__file__).with_name("fields.yaml")

# Raw keys consumed by derivations (not part of the 'direct' map). VERIFY names.
RAW_CODENAME = "CodeNameText"
RAW_MEMORY = "MemoryTypes"
RAW_OPN_CODE = "OrderingCode"   # raw OPN if available; else composed fallback

# For the composed-OPN fallback only. Extend as you add code names. VERIFY.
CODENAME_SHORTFORM = {
    "Emerald Rapids": "EMR",
    "Granite Rapids": "GNR",
    "Sierra Forest": "SRF",
    "Sapphire Rapids": "SPR",
}
CODENAME_GEN = {            # Xeon generation prefix used in composed OPN
    "Emerald Rapids": "X5",
    "Granite Rapids": "X6P",
    "Sierra Forest": "X6E",
    "Sapphire Rapids": "X4",
}


# --- small raw-string parsers ---------------------------------------------
def _ghz(s) -> Optional[float]:
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(s))
    return float(m.group(1)) if m else None


def _int(s) -> Optional[int]:
    if s is None or s == "":
        return None
    m = re.search(r"(\d+)", str(s))
    return int(m.group(1)) if m else None


def _gen_num(s) -> Optional[str]:
    if not s:
        return None
    m = re.search(r"(\d+)", str(s))   # "Gen 5" -> "5"
    return m.group(1) if m else None


def _num_only(s) -> Optional[str]:
    """Strip units/symbols but keep the value as string for the flat row."""
    if s is None or s == "":
        return None
    m = re.search(r"[\d.,]+", str(s).replace(",", ""))
    return m.group(0) if m else str(s)


class IntelArkAgent(Agent):
    name = "intel_ark"

    def __init__(self, fields_path: Path = FIELDS_YAML):
        with open(fields_path) as f:
            self.field_map = yaml.safe_load(f) or {}
        self.direct = self.field_map.get("direct", {}) or {}

    def fetch_raw(self, *, sample: bool = False, odata_filter: str = "",
                  **_) -> List[dict]:
        if sample:
            return fetcher.load_sample()
        return fetcher.fetch_odata(odata_filter=odata_filter)

    def to_records(self, raw_rows: List[dict]) -> List[SpecRecord]:
        return [self._build(r) for r in raw_rows]

    def _build(self, raw: dict) -> SpecRecord:
        rec = SpecRecord()

        # 1) direct map (config-driven). Numeric-ish fields get unit-stripped.
        for schema_field, ark_field in self.direct.items():
            val = raw.get(ark_field)
            setattr(rec, schema_field, val)
        # tidy a few units for the flat row
        rec.TDP = _num_only(rec.TDP)
        rec.L3_Cache = _num_only(rec.L3_Cache)
        rec.PCIe_Generation = _gen_num(rec.PCIe_Generation)
        rec.Active = "Y"  # default; manual review can flip to N

        # 2) derivations
        cores = _int(raw.get(self.direct.get("Density", "CoreCount")))
        threads = _int(raw.get(self.direct.get("Threads", "ThreadCount")))
        codename = raw.get(RAW_CODENAME)

        rec.Product = derive.classify_product(codename) if codename else None
        rec.SMT = derive.infer_smt(threads, cores)

        fbase = _ghz(rec.Fbase)
        fb_lo, fb_hi = derive.freq_bounds(fbase)
        rec.Fbase = fbase
        rec.Fbase_Low, rec.Fbase_High = fb_lo, fb_hi

        fmax = _ghz(rec.Fmax)
        fm_lo, fm_hi = derive.freq_bounds(fmax)
        rec.Fmax = fmax
        rec.Fmax_Low, rec.Fmax_High = fm_lo, fm_hi
        rec.All_Core_Boost_Freq = _ghz(rec.All_Core_Boost_Freq)

        rate, tech = derive.parse_memory(raw.get(RAW_MEMORY))
        rec.Max_DDR_Rate, rec.DIMM_Technology = rate, tech

        # OPN: raw-first, else composed X<gen>-<shortform>-<variant>-<cores>C-<tdp>W
        base_name = (rec.Product or "").split("-")[0].strip() if rec.Product else None
        variant = rec.Product.split("-", 1)[1] if rec.Product and "-" in rec.Product else None
        rec.OPN = derive.build_opn(
            raw.get(RAW_OPN_CODE),
            proc_gen=CODENAME_GEN.get(base_name),
            shortform=CODENAME_SHORTFORM.get(base_name),
            variant=variant,
            cores=cores,
            tdp=_int(rec.TDP),
        )
        return rec
