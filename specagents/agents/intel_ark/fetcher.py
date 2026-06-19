"""
Intel ARK source adapter (HTML scraping).

The old odata.intel.com host is dead (NXDOMAIN). ARK serves spec data in the
product-page HTML: each spec value sits on an element carrying a `data-key`
attribute whose value is Intel's internal key (e.g. ClockSpeed, MaxTDP,
CoreCount) -- the same keys listed in raspi/scrapy-intel-ark's _legend.json.
We parse those into {data_key: value}.

Paths to verify against a live page are marked `# VERIFY`.

Three entry points:
  fetch_product(url)     one product page -> raw dict
  fetch_series(url)      a series page    -> list of product URLs
  load_sample()          offline fixture  -> testable with no network
"""

import re
from typing import Dict, List
from urllib.parse import urljoin

ARK_BASE = "https://ark.intel.com"
# ark.intel.com blocks default client UAs; present a browser-like one.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
# product page URL pattern: /content/www/us/en/ark/products/<id>/<slug>.html
PRODUCT_HREF = re.compile(r"/ark/products/\d+/[^\"'#]+\.html")


def _get(url: str) -> str:
    import httpx  # lazy; offline sample path needs no deps
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def parse_spec_page(html: str) -> Dict[str, str]:
    """Extract {data_key: value} from an ARK product page."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    specs: Dict[str, str] = {}
    # VERIFY: confirm the value text sits on the element carrying data-key.
    for el in soup.select("[data-key]"):
        key = el.get("data-key")
        val = el.get_text(strip=True)
        if key and key not in specs:
            specs[key] = val

    # product display name from the page heading/title
    h1 = soup.find("h1")
    if h1:
        specs["_ProductName"] = h1.get_text(strip=True)
    elif soup.title:
        specs["_ProductName"] = soup.title.get_text(strip=True)
    return specs


def fetch_product(url: str) -> Dict[str, str]:
    return parse_spec_page(_get(url))


def fetch_series(series_url: str) -> List[str]:
    """Return absolute product-page URLs linked from a series page."""
    html = _get(series_url)
    hrefs = {urljoin(ARK_BASE, m.group(0)) for m in PRODUCT_HREF.finditer(html)}
    return sorted(hrefs)


# --- offline fixture -------------------------------------------------------
# Emerald Rapids 8562Y+ keyed by ARK's REAL spec keys (from _legend.json),
# so the map+derive pipeline runs end-to-end with no network.
SAMPLE_RAW: List[Dict] = [
    {
        "ProcessorNumber": "8562Y+",
        "_ProductName": "Intel\u00ae Xeon\u00ae Platinum 8562Y+ Processor",
        "CodeNameText": "Products formerly Emerald Rapids",
        "StatusCodeText": "Launched",
        "BornOnDate": "Q4'23",
        "Lithography": "Intel 7",
        "SocketsSupported": "FCLGA4677",
        "Cache": "60 MB",
        "MaxTDP": "300 W",
        "CoreCount": "32",
        "MaxCPUs": "2",
        "ThreadCount": "64",
        "HyperThreading": "Yes",
        "ClockSpeed": "2.80 GHz",
        "ClockSpeedMax": "4.10 GHz",
        "NumMemoryChannels": "8",
        "MemoryTypes": "DDR5",
        "MemoryMaxSpeedMhz": "5600",
        "UltraPathInterconnectLinks": "4",
        "NumPCIExpressPorts": "80",
        "PCIExpressRevision": "5.0",
        "RecommendedCustomerPrice": "$5,945.00",
    }
]


def load_sample() -> List[Dict]:
    return [dict(r) for r in SAMPLE_RAW]
