# SDK wheel installation boundary

The default pure-Python SDK workflow can run from an installed wheel outside the
source checkout. Verify it with:

```bash
python scripts/check_wheel_sdk.py
```

The check builds a wheel, creates a fresh virtual environment without system-site
packages, installs that wheel and its declared runtime dependencies, verifies the
import comes from that environment, then copies and runs the documented offline
SDK example in a separate empty working directory using isolated Python mode.
It strips PYTHONPATH/PYTHONHOME, uses no editable install and makes no provider
requests. It prints `WHEEL_SDK_VERIFIED` only after all subprocesses succeed.
Network or a populated dependency cache is required; temporary environments are
removed after the check. CI runs this independently of checkout-based pytest.

This verifies the ordinary `Contract` / `run_workflow` / Python validator path.
It does not certify the full CLI/API/frontend, benchmark datasets, provider
configuration or optional native Blaze worker from a wheel. Those features still
have checkout-relative assets and their documented setup requirements. JSON
Schema fixtures and external record archives are not implicitly bundled by this
check. PostgreSQL additionally needs its driver and an actual database.

FastAPI, NumPy and SciPy currently remain default dependencies in pyproject.toml.
This change does not measure their install size, show a measured onboarding
problem, or split extras speculatively. If users report SDK installation friction,
measure clean-install time/size and test core/API/research/native installation
profiles before proposing optional-dependency groups. Keep existing installs
compatible while making that decision.
