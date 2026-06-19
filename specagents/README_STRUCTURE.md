# specagents

Core scaffold for the Intel ARK spec pipeline.

## Layout
```
specagents/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── schema.py      # flat SpecRecord (canonical column order) + mandatory check
│   └── derive.py      # OPN, variant, SMT, frequency, memory derivation rules
└── agents/
    ├── __init__.py
    └── intel_ark/
        ├── __init__.py
        └── fields.yaml  # ARK section/OData -> field mapping (direct/derived/manual)
```

## Next (not yet built)
- agents/intel_ark/fetcher.py  — OData client filling `direct` fields
- core/exporter.py             — flat CSV export + missing-mandatory report
- api/                         — FastAPI agent registry
- ui/                          — React dashboard
