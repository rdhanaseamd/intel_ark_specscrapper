"""
Derivation rules — the fields ARK does not hand over directly.

Every function here encodes one rule from the spec. They are deliberately
pure (input -> output, no I/O) so they're easy to unit-test and so the
manual validation step can re-run them on demand.
"""

import re
from typing import Optional, Tuple

# Variant suffixes seen on Xeon datacenter code names / models.
VARIANTS = ["AP", "SP", "D", "E", "P", "H", "N", "Q", "U", "+"]


def classify_product(codename: str, variant: Optional[str] = None) -> str:
    """Normalize an ARK code name into 'Granite Rapids-AP' form.

    - Drops the 'products formerly' marketing wrapper.
    - Strips parentheticals and surrounding punctuation.
    - Appends the variant: use the explicit `variant` arg if given,
      otherwise detect a trailing variant token in the source string.
    """
    if not codename:
        return ""
    s = re.sub(r"products formerly", " ", codename, flags=re.I)
    s = re.sub(r"\(.*?\)", " ", s)            # remove (...) chunks
    detected = variant
    if detected is None:
        for v in VARIANTS:
            if re.search(rf"[-\s]{re.escape(v)}(?:\b|$)", s):
                detected = v
                break
    # strip any trailing variant token from the base name before re-appending
    base = re.sub(r"[-\s]+(?:" + "|".join(re.escape(v) for v in VARIANTS) + r")\s*$", "", s)
    base = re.sub(r"\s+", " ", base).strip(" ,-")
    return f"{base}-{detected}" if detected else base


def build_opn(
    raw_spec_code: Optional[str],
    *,
    proc_gen: Optional[str] = None,
    shortform: Optional[str] = None,
    variant: Optional[str] = None,
    cores: Optional[int] = None,
    tdp: Optional[int] = None,
) -> str:
    """OPN, raw-first.

    If ARK exposes the spec/ordering code (e.g. 'X5-8562Y+'), use it verbatim.
    Otherwise compose '<gen>-<shortform>-<variant>-<cores>C-<tdp>W'
    (e.g. 'X6P-GNR-AP-128C-500W').
    """
    if raw_spec_code and raw_spec_code.strip():
        return raw_spec_code.strip()
    parts = [p for p in (proc_gen, shortform, variant) if p]
    if cores is not None:
        parts.append(f"{cores}C")
    if tdp is not None:
        parts.append(f"{tdp}W")
    return "-".join(parts)


def infer_smt(threads: Optional[int], cores: Optional[int]) -> str:
    """Hyper-Threading (SMT). 'ON' if threads == 2*cores, else 'OFF'.

    Returns '' when we lack the numbers to decide (flag for manual check).
    """
    if threads is None or cores is None or cores == 0:
        return ""
    return "ON" if threads == cores * 2 else "OFF"


def freq_bounds(
    listed: Optional[float],
    low: Optional[float] = None,
    high: Optional[float] = None,
    delta: float = 0.1,
) -> Tuple[Optional[float], Optional[float]]:
    """Return (low, high). If a published bound is missing, fall back to
    listed -/+ delta (default 0.1 GHz), per spec."""
    if listed is None:
        return low, high
    lo = low if low is not None else round(listed - delta, 2)
    hi = high if high is not None else round(listed + delta, 2)
    return lo, hi


def parse_memory(mem_type: str) -> Tuple[Optional[int], Optional[str]]:
    """'DDR5-6400' -> (6400, 'DDR5'); 'MRDIMM-8800' -> (8800, 'MRDIMM').

    Also handles MT/s shorthand like '12.8k' -> 12800. Returns
    (rate_MTs, technology).
    """
    if not mem_type:
        return None, None
    s = mem_type.strip()
    tech_match = re.match(r"([A-Za-z]+\d?[A-Za-z]*)", s)
    tech = tech_match.group(1) if tech_match else None

    rate = None
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k", s, flags=re.I)
    if k_match:
        rate = int(round(float(k_match.group(1)) * 1000))
    else:
        num_match = re.search(r"(\d{3,5})", s)
        if num_match:
            rate = int(num_match.group(1))
    return rate, tech
