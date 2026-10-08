# Autonomous Test Conveyor

End-to-end conveyor that boots RimWorld, starts a colony headlessly through
the RIMAPI REST API, and verifies core endpoints without any manual UI work.

## Requirements

- RimWorld 1.5+ (Steam) with Harmony + RIMAPI enabled.
- Python 3 (standard library only — no extra packages).

## Files

| File | Purpose |
|------|---------|
| `run_conveyor.sh` | Full cycle: launch RimWorld via Steam → run smoke suite → optionally close the game (`--quit`). |
| `smoke_test.py` | 8 checks: server reachability, devquick colony start, `version`, `game/state`, `colonists`, `maps`, `game/speed`, tick progression, `game/save`. Exit code 0 = all pass. |

## Usage

```bash
./run_conveyor.sh            # launches the game if needed, runs the suite
./run_conveyor.sh --quit     # same, then closes RimWorld
python3 smoke_test.py        # suite only (game must already be running)
```

The suite waits up to 180 s for the API server (override with the first CLI
argument, e.g. `python3 smoke_test.py 300`) and up to 90 s for map
generation, so it is safe to run immediately after booting the game.
