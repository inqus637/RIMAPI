#!/usr/bin/env python3
"""RIMAPI autonomous test conveyor — smoke suite.

Runs against a live RimWorld instance with the RIMAPI mod loaded
(http://localhost:8765) and verifies the core request pipeline end-to-end.

Steps:
    1. Wait for the API server to become reachable.
    2. Ensure a colony is running (devquick start via POST /api/v1/game/start/devquick).
    3. Read endpoints: version, game state, colonists, maps.
    4. Write endpoints: game speed, tick progression, save game.

Exit code 0 = all checks passed, 1 = at least one failure (printed per step).
Requires only the Python standard library so it can run in CI without extra installs.
"""
import json
import sys
import time
import urllib.request

BASE_URL = "http://localhost:8765"
GET_TIMEOUT_SECONDS = 10


def http(method: str, path: str, body=None, timeout: int = GET_TIMEOUT_SECONDS):
    """Perform an HTTP request against the RIMAPI server and parse the JSON envelope."""
    data = json.dumps(body if body is not None else {}).encode() if method == "POST" else None
    request = urllib.request.Request(BASE_URL + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode())
    if not payload.get("success", False):
        raise RuntimeError(f"API reported failure: {payload.get('errors')}")
    return payload


def run_check(name: str, check) -> bool:
    """Run a single named check, printing PASS/FAIL, and report the result."""
    try:
        detail = check()
        print(f"[PASS] {name}" + (f" -> {detail}" if detail else ""))
        return True
    except Exception as error:  # noqa: BLE001 - report any failure as a failed step
        print(f"[FAIL] {name}: {error}")
        return False


def wait_for_server(seconds: int = 120) -> None:
    """Block until the API server answers /api/v1/game/state or the timeout expires."""
    deadline = time.time() + seconds
    last_error = None
    while time.time() < deadline:
        try:
            http("GET", "/api/v1/game/state", timeout=3)
            return
        except Exception as error:  # noqa: BLE001 - connection refused while game boots
            last_error = error
            time.sleep(5)
    raise RuntimeError(f"API server not reachable within {seconds}s: {last_error}")


def ensure_colony(max_wait_seconds: int = 90) -> dict:
    """Start a colony via devquick when needed; return the running game state."""
    state = http("GET", "/api/v1/game/state")["data"]
    if state["program_state"] != "Playing":
        http("POST", "/api/v1/game/start/devquick", {})
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        state = http("GET", "/api/v1/game/state")["data"]
        if state["program_state"] == "Playing" and state["colonist_count"] > 0:
            return state
        time.sleep(4)
    raise RuntimeError(f"colony not running within {max_wait_seconds}s: {state}")


def check_version() -> str:
    payload = http("GET", "/api/v1/version")["data"]
    return (f"rimworld={payload['rim_world_version']} "
            f"mod={payload['mod_version']} api={payload['api_version']}")


def check_colonists() -> str:
    colonists = http("GET", "/api/v1/colonists")["data"]
    assert len(colonists) >= 3, f"expected >=3 colonists, got {len(colonists)}"
    for key in ("id", "name", "health", "mood", "position"):
        assert key in colonists[0], f"missing key '{key}' in colonist DTO"
    return ", ".join(f"{pawn['name']}#{pawn['id']}" for pawn in colonists)


def check_maps() -> str:
    maps = http("GET", "/api/v1/maps")["data"]
    assert len(maps) >= 1, "no maps returned"
    return f"map0 seed={maps[0]['seed']} size={maps[0]['size']}"


def check_speed_endpoint() -> None:
    # /game/speed reads the parameter from the query string, not the body.
    http("POST", "/api/v1/game/speed?speed=3", {})


def check_ticks_advance(seconds: int = 3) -> str:
    first = http("GET", "/api/v1/game/state")["data"]["game_tick"]
    time.sleep(seconds)
    second = http("GET", "/api/v1/game/state")["data"]["game_tick"]
    assert second > first, f"game tick frozen: {first} -> {second}"
    return f"{first} -> {second}"


def check_save_endpoint() -> str:
    # GameSaveRequestDto expects the snake_case key "file_name".
    name = "conveyor_autosave"
    http("POST", "/api/v1/game/save", {"file_name": name})
    return f"saved as {name}.rws"


def main() -> int:
    results = []

    print("== 1. API server ==")
    # Generous default: steam + engine + mod loading can take a while on a cold boot.
    server_timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    if not run_check("server reachable on :8765", lambda: wait_for_server(server_timeout)):
        return 1

    print("== 2. Ready start (devquick) ==")

    def colony_running():
        state = ensure_colony()
        return (f"tick={state['game_tick']} colonists={state['colonist_count']} "
                f"storyteller={state['storyteller']}")

    results.append(run_check("colony running", colony_running))
    if not results[-1]:
        return 1

    print("== 3. Read endpoints ==")
    results.append(run_check("GET /version", check_version))
    results.append(run_check("GET /game/state", lambda: http("GET", "/api/v1/game/state")["data"]))
    results.append(run_check("GET /colonists", check_colonists))
    results.append(run_check("GET /maps", check_maps))

    print("== 4. Write endpoints ==")
    results.append(run_check("POST /game/speed?speed=3", check_speed_endpoint))
    results.append(run_check("game ticks advance", check_ticks_advance))
    results.append(run_check("POST /game/save", check_save_endpoint))

    passed = sum(results)
    ok = passed == len(results)
    print(f"\n=== RESULT: {'ALL PASS' if ok else 'FAILURES'} ({passed}/{len(results)}) ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
