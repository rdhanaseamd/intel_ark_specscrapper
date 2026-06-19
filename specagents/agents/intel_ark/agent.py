"""
IntelArkAgent -- turns raw ARK spec dicts into flat SpecRecords.

- `direct` fields copied from fields.yaml (config-driven), with light unit-strip.
- `derived` fields computed via core.derive (+ a few direct reads here:
  HyperThreading, StatusCodeText, MemoryMaxSpeedMhz, page name).
- `manual`/`unused` fields left blank.
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

# Raw ARK keys consumed by derivations / special handling (from _legend.json).
RAW_CODENAME = "CodeNameText"
RAW_NAME = "_ProductName"
RAW_STATUS = "StatusCodeText"
RAW_HT = "HyperThreading"
RAW_MEMTYPES = "MemoryTypes"
RAW_MEMSPEED = "MemoryMaxSpeedMhz"
RAW_OPN_CODE = "OrderingCode"   # raw OPN if ever present; else composed fallback

# Composed-OPN fallback lookups. Extend as code names appear. VERIFY values.
CODENAME_SHORTFORM = {
    "Emerald Rapids": "EMR", "Granite Rapids": "GNR",
    "Sierra Forest": "SRF", "Sapphire Rapids": "SPR",
}
CODENAME_GEN = {
    "Emerald Rapids": "X5", "Granite Rapids": "X6P",
    "Sierra Forest": "X6E", "Sapphire Rapids": "X4",
}


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
    m = re.search(r"(\d+)", str(s))   # "Gen 5" / "5.0" -> "5"
    return m.group(1) if m else None


def _num_only(s) -> Optional[str]:
    if s is None or s == "":
        return None
    m = re.search(r"[\d.]+", str(s).replace(",", ""))
    return m.group(0) if m else str(s)


class IntelArkAgent(Agent):
    name = "intel_ark"

    def __init__(self, fields_path: Path = FIELDS_YAML):
        with open(fields_path) as f:
            self.field_map = yaml.safe_load(f) or {}
        self.direct = self.field_map.get("direct", {}) or {}

    def fetch_raw(self, *, sample: bool = False, product_urls: Optional[List[str]] = None,
                  series_url: Optional[str] = None, **_) -> List[dict]:
        if sample:
            return fetcher.load_sample()
        if series_url:
            product_urls = (product_urls or []) + fetcher.fetch_series(series_url)
        if not product_urls:
            raise ValueError("Provide sample=True, product_urls=[...], or series_url=...")
        return [fetcher.fetch_product(u) for u in product_urls]

    def to_records(self, raw_rows: List[dict]) -> List[SpecRecord]:
        return [self._build(r) for r in raw_rows]

    def _build(self, raw: dict) -> SpecRecord:
        rec = SpecRecord()

        # 1) direct map (config-driven)
        for schema_field, ark_field in self.direct.items():
            setattr(rec, schema_field, raw.get(ark_field))

        # light unit tidy for the flat row
        rec.TDP = _num_only(rec.TDP)
        rec.cTDP_Min = _num_only(rec.cTDP_Min)
        rec.cTDP_Max = _num_only(rec.cTDP_Max)
        rec.L3_Cache = _num_only(rec.L3_Cache)
        rec.PCIe_Generation = _gen_num(rec.PCIe_Generation)
        rec._1kU = ("$" + _num_only(rec._1kU)) if rec._1kU else None
        if rec._1P_2P and str(rec._1P_2P).strip().isdigit():
            rec._1P_2P = f"{rec._1P_2P}P"   # "2" -> "2P"

        # 2) derivations + special direct reads
        cores = _int(raw.get(self.direct.get("Density", "CoreCount")))
        threads = _int(raw.get(self.direct.get("Threads", "ThreadCount")))

        codename = raw.get(RAW_CODENAME)
        rec.Product = derive.classify_product(codename) if codename else None
        rec.Processor_Name = raw.get(RAW_NAME)

        status = (raw.get(RAW_STATUS) or "").lower()
        rec.Active = "Y" if "launch" in status else ("N" if status else None)
        rec.Forecast_Start_Date = raw.get("BornOnDate")

        ht = (raw.get(RAW_HT) or "").lower()
        if ht in ("yes", "true"):
            rec.SMT = "ON"
        elif ht in ("no", "false"):
            rec.SMT = "OFF"
        else:
            rec.SMT = derive.infer_smt(threads, cores)

        fbase = _ghz(rec.Fbase)
        rec.Fbase = fbase
        rec.Fbase_Low, rec.Fbase_High = derive.freq_bounds(fbase)
        fmax = _ghz(rec.Fmax)
        rec.Fmax = fmax
        rec.Fmax_Low, rec.Fmax_High = derive.freq_bounds(fmax)

        # memory: prefer the explicit max-speed field, else parse the type string
        rate = _int(raw.get(RAW_MEMSPEED))
        prate, ptech = derive.parse_memory(raw.get(RAW_MEMTYPES))
        rec.Max_DDR_Rate = rate if rate is not None else prate
        rec.DIMM_Technology = ptech or (raw.get(RAW_MEMTYPES) or None)

        # OPN: raw-first, else composed
        base_name = rec.Product.split("-")[0].strip() if rec.Product else None
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
