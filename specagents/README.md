# intel_ark_specscrapper

Competitive specification scraping for Intel Xeon datacenter processors.

Fetches product specifications from Intel ARK, normalizes them into a single
flat record (one row per processor), and derives the fields ARK does not expose
directly (OPN, SMT, frequency bounds, memory rate/technology). Business and
roadmap fields are entered/validated separately.

## Project layout

```
intel_ark_specscrapper/
├── README.md
├── LICENSE                 # Apache-2.0
├── .gitignore
├── pyproject.toml          # makes `specagents` installable
├── requirements.txt
└── specagents/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── schema.py        # flat SpecRecord (canonical column order) + mandatory check
    │   └── derive.py        # OPN, variant, SMT, frequency, memory derivation rules
    └── agents/
        ├── __init__.py
        └── intel_ark/
            ├── __init__.py
            └── fields.yaml  # ARK section/OData -> field mapping (direct/derived/manual)
```

## Install

From the repo root:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

`pip install -e .` puts `specagents` on the path, so imports resolve the same
way regardless of where you run from:

```python
from specagents.core.schema import SpecRecord
from specagents.core import derive
```

## Field model

One product = one flat row. Fields fall into four acquisition types:

- **direct** — read straight from Intel ARK (model, package, TDP, cache, frequencies, PCIe, etc.)
- **derived** — computed in `core/derive.py` (OPN, Product variant, SMT, Fbase/Fmax bounds, DDR rate/tech)
- **manual** — not on ARK; entered separately (UPFM_ID, Roadmap, Target_Customer/Workload, ASP, …)
- **unused** — left empty by design (TPL_Version)

Mandatory fields are checked via `SpecRecord.missing_mandatory()`; validation of
assumed/derived values is a manual sign-off step for now.

## Status

- [x] Core scaffold: flat schema, derivation rules, ARK field map
- [ ] ARK fetcher (OData client filling `direct` fields) — *OData field names need live verification*
- [ ] CSV exporter + missing-mandatory report
- [ ] FastAPI agent registry
- [ ] React management dashboard
- [ ] Wafer specifications (second source, future)
