"""
Intel ARK source adapter.

Two ways to get raw rows:
  - fetch_odata(...)  live OData call (needs network + verified endpoint)
  - load_sample()     offline fixture, so the map+derive pipeline is testable now

EVERYTHING marked `# VERIFY` is an educated guess about Intel's API that
cannot be confirmed from this environment. The first time you run this against
a live endpoint, reconcile these names/URLs and the matching keys in fields.yaml.
"""

from typing import List

# VERIFY: Intel ARK has exposed OData at this host historically; confirm the
# base URL, entity path, and whether it still requires no auth in 2026.
ODATA_BASE = "https://odata.intel.com/API/v1_0/Products/Processors"
ODATA_PAGE_SIZE = 100


def fetch_odata(odata_filter: str = "", top: int = ODATA_PAGE_SIZE) -> List[dict]:
    """Pull raw processor rows from Intel ARK OData.

    httpx is imported lazily so the offline sample path has zero deps.
    Install with: pip install -e ".[fetch]"
    """
    import httpx  # lazy; only needed for the live path

    rows: List[dict] = []
    skip = 0
    params = {"$format": "json", "$top": str(top)}
    if odata_filter:
        params["$filter"] = odata_filter  # VERIFY: filter syntax/field names

    with httpx.Client(timeout=30, headers={"Accept": "application/json"}) as client:
        while True:
            params["$skip"] = str(skip)
            resp = client.get(ODATA_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            # VERIFY: OData v3/v4 wrap rows differently ("d"/"results" vs "value").
            batch = data.get("value") or data.get("d", {}).get("results") or []
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < top:
                break
            skip += top
    return rows


# --- offline fixture -------------------------------------------------------
# One Emerald Rapids 8562Y+ row keyed by the *guessed* ARK field names, so the
# transform pipeline can be exercised end-to-end with no network. Replace these
# keys with the real ones once verified.
SAMPLE_RAW = [
    {
        # direct fields (match fields.yaml 'direct' values)
        "ProcessorNumber": "8562Y+",
        "ProductName": "Intel Xeon Platinum 8562Y+",
        "Lithography": "Intel 7",
        "PackageCarrier": "FCLGA4677",
        "Cache": "60 MB",
        "TDP": "300 W",
        "CoreCount": "32",
        "ScalabilitySockets": "2P",            # VERIFY: ARK may say "2S"
        "ThreadCount": "64",
        "ProcessorBaseFrequency": "2.80 GHz",
        "MaxTurboFrequency": "4.10 GHz",
        "AllCoreTurboFrequency": "3.80 GHz",
        "MaxMemoryChannels": "8",
        "MaxUPILinks": "80",                   # VERIFY: GMI/DMI mapping
        "MaxPCIeLanes": "80",
        "PCIeRevision": "Gen 5",
        "RecommendedPrice1KU": "$5,945",
        "LaunchDate": "12/14/2023",
        # raw inputs used only by derivations
        "CodeNameText": "Products formerly Emerald Rapids",  # VERIFY field name
        "MemoryTypes": "DDR5-5600",            # VERIFY field name
        # NOTE: the raw OPN code (e.g. "X5-8562Y+") is likely NOT an ARK field;
        # it may come from your internal data. Left absent here on purpose so the
        # composed-OPN fallback path is exercised. Provide it to use raw-first.
        "OrderingCode": None,                  # VERIFY: source of raw OPN, if any
    }
]


def load_sample() -> List[dict]:
    """Offline raw rows for testing the pipeline without network."""
    return [dict(r) for r in SAMPLE_RAW]
