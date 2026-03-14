# pycircuitsim — Python Circuit Simulation Toolkit

Monorepo containing shared interfaces and tool-specific wrappers for circuit simulation.

## Packages

| Package | Description | Backend |
|---------|-------------|---------|
| `pycircuitsim-core` | Shared ABCs, models, and interfaces | — |
| `pyplecs` | PLECS wrapper (XML-RPC) | [PLECS](https://plexim.com/) |
| `pygeckocircuit` | GeckoCIRCUITS wrapper (REST API) | [GeckoCIRCUITS](https://github.com/geckocircuits/GeckoCIRCUITS) |

## Architecture

```
pycircuitsim-core (ABCs)
├── SimulationServer      — simulate(), simulate_batch(), is_available()
├── SimulationCache       — get/cache/invalidate/clear/stats
├── SimulationOrchestrator — submit/cancel/wait/start/stop
├── Models                — SimulationRequest, SimulationResult, SimulationStatus
├── StructuredLogger      — structured lifecycle logging
└── ConfigManager         — YAML config with typed sections

pyplecs (implements ABCs)          pygeckocircuit (implements ABCs)
├── PlecsServer (XML-RPC)          ├── GeckoServer (REST API)
├── PlecsCache                     ├── GeckoCache
├── PlecsOrchestrator              ├── GeckoOrchestrator
└── ...                            └── ...
```

## Installation

```bash
# Core only
pip install -e packages/pycircuitsim-core

# PLECS wrapper (includes core)
pip install -e packages/pyplecs

# GeckoCIRCUITS wrapper (includes core)
pip install -e packages/pygeckocircuit

# All packages
pip install -e packages/pycircuitsim-core -e packages/pyplecs -e packages/pygeckocircuit
```

## Tool-Agnostic Usage

```python
from pycircuitsim_core import SimulationServer

# Both PlecsServer and GeckoServer implement SimulationServer
def run_sweep(server: SimulationServer, param_sets: list[dict]):
    results = server.simulate_batch(param_sets)
    return [r for r in results if r.success]
```

## License

MIT
