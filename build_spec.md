<USER_REQUEST>
# BUILD SPEC: IEEE 14-Bus Single-Line Diagram — Live Digital Twin

## 0. Context — existing assets (do NOT rewrite from scratch, fix in place + reorganize)

**Reference image required:** attach `ieee14_reference_sld.png` (the IEEE 14-bus SLD figure) alongside this prompt. Every layout/icon decision below is taken from it — Antigravity needs the actual file, not just this description.

Current repo state (before this spec):
```
IEEE14Bus/
├── data/case14.m
└── python/
    ├── parse_case14.py
    ├── convert_case14.py
    ├── build_ieee14.py
    ├── test_builder.py
    └── test_converter.py
```

**Target repo structure (reorganize into this before/while applying fixes):**
```
IEEE14Bus/
├── backend/
│   ├── core/
│   │   ├── parse_case14.py        # moved from python/, CORRECT, leave logic as-is
│   │   ├── convert_case14.py       # moved from python/, fix per Section 1
<truncated 12329 bytes>