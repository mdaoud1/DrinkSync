# DrinkSync bugfix and harden

> For Hermes: implement this plan task-by-task with TDD. Fast-path: no.

**Goal:** Make drink amounts, daily reset, and phone pairing actually trustworthy, and make both sides testable off the Pi / without a device.

**Architecture:** Extract pure drink math on the Pi (incremental sip vs refill) and keep the Android store as the source of truth for daily totals. RFCOMM stays Classic Bluetooth; one UTF-8 line per event, newline-terminated.

**Tech Stack:** Kotlin + Compose + SharedPreferences; CPython + HX711 + PyBluez; JUnit4; unittest.

**Constraints:**
- Do not change the public wire format prefix (`Weight difference: <grams> grams`).
- Do not rename `applicationId` (`com.example.drinksync`) — that would wipe existing installs.
- Do not add cloud, Room, or BLE.
- Keep the default Bluetooth MAC as a last-resort fallback so an already-paired Pi still works.
- Tests must run off-Pi (`python -m unittest discover -v` in `Python/`) and as `./gradlew :app:testDebugUnitTest` with JDK 21.

## Workstreams

| ID | Slice | Mode |
| --- | --- | --- |
| A | Pi drink delta + testable scale math | parallel-safe |
| B | Android daily reset + leftover grams + store guards | parallel-safe |
| C | RFCOMM framing, permissions, server retry, UI hygiene | serial after B (same Activity) |
| D | Build/CI/docs (gradlew +x, Java 21, README) | serial last |

---

### Task A1: Pure incremental drink math

**Files:**
- Create: `Python/drink_math.py`
- Create: `Python/test_drink_math.py`

**Behavior:**
- `next_drink(previous_weight, current_weight, min_grams=5.0) -> (grams_or_None, new_previous)`
- `previous is None` → adopt current, send nothing
- `previous - current >= min_grams` → send the delta, new previous = current
- `current - previous >= min_grams` → refill, send nothing, new previous = current
- else noise → send nothing, keep previous

**Tests:** first reading, sip, second sip not double-counted, refill, noise below 5g, exact 5g counts.

### Task A2: Wire take_reading to incremental math

**Files:**
- Modify: `Python/scale_persistent_tare.py`
- Modify: `Python/scale_config.py` (persist optional `lastWeight`)
- Test: extend `test_scale_config.py` / `test_drink_math.py`

**Behavior:**
- Config path is next to the script, not cwd.
- `take_reading` converts the median scale value with `next_drink`, not `initial_max - current`.
- Persist `lastWeight` after a successful decision so a restart does not invent a drink.
- `initialMaxWeight` is optional sanity only (ignore / warn if a delta exceeds it); not the drink amount.

### Task A3: Off-Pi safety + Bluetooth send

**Files:**
- Modify: `Python/hx711.py` (no crash when `GPIO is None`; raise only on real I/O)
- Modify: `Python/bt.py` (send UTF-8 bytes + trailing newline; still treat ACK timeout as success)
- Modify: `Python/gyroscope.py` (only run loop under `__main__`)
- Modify: `Python/scale.py` (no GPIO/HX711 at import)
- Modify: `Python/stability_scale_trigger.py` (lazy-init scale instead of import-time side effects if cheap; otherwise leave entrypoint as-is if A2 already lazy-inits)

**Tests:** existing hx711/protocol tests still pass; add bt newline encode unit test by extracting a `encode_message` helper.

---

### Task B1: Persist lastResetDate on first open

**Files:**
- Modify: `Android/.../HydrationStore.kt`
- Modify: `Android/.../HydrationStoreTest.kt`

**Failing test first:** empty prefs, intake 12, apply reset on day 1, reopen on day 2 → intake 0 and lastResetDate persisted.

**Fix:** if `LAST_RESET_DATE` is missing, write today. Do not treat a missing key as “already today.”

### Task B2: Leftover grams so small sips are not dropped

**Files:**
- Modify: `DrinkEvent.kt` (keep `gramsToOz`; add leftover helper or put it on the store)
- Modify: `HydrationStore.kt` (`addGrams`, persist leftover)
- Modify: `DrinkEventTest.kt`, `HydrationStoreTest.kt`
- Modify: `MainActivity.kt` serveClient / LaunchedEffect to add grams, always clear the trigger (including 0 oz)

**Behavior:**
- Store leftover grams (float via string prefs is fine).
- `addGrams(10)` → 0 oz this time, leftover ~10; another 20g → 1 oz logged, leftover remainder.
- Never leave `intakeToAddFromBluetooth == 0` stuck (always call `onIntakeProcessed`).

### Task B3: Store guards

- Reject `setDailyGoal` unless `1..500`.
- Clamp `totalIntake` at 0 when setIntake lowers the day total.
- Early bird hours 5–6 inclusive match “5:00–7:00”; late night 0–2 match “12:00–3:00”. Update copy if needed.

---

### Task C1: RFCOMM line buffer

**Files:**
- Create: `Android/.../LineBuffer.kt` + `LineBufferTest.kt`
- Modify: `MainActivity.serveClient`

**Behavior:** split on `\n`; also accept a remainder that already matches `DrinkEvent.parseGrams` (old Pi without newline).

### Task C2: Permissions + keep listening

- Pre-31: `BLUETOOTH` is enough; do not require `BLUETOOTH_CONNECT`.
- Android 12+: `BLUETOOTH_CONNECT` via Activity Result API (drop deprecated `onRequestPermissionsResult`).
- On `accept()` failure, recreate the listen socket and keep looping while `serverRunning`.
- Use `BluetoothManager.adapter` instead of `BluetoothAdapter.getDefaultAdapter()`.

### Task C3: UI hygiene

- `HorizontalDivider` instead of `Divider`.
- `androidx.lifecycle.compose.LocalLifecycleOwner`.
- Remove unused `package=` from `AndroidManifest.xml`.
- Add `coreLibraryDesugaring` so `java.time` is safe at minSdk 24.

---

### Task D: Build / docs

- Commit `gradlew` / `gradlew.bat` executable bit.
- Pin Java toolchain 21 in `Android/app/build.gradle.kts`.
- README: incremental drink math, leftover grams, `JAVA_HOME` 21, `DRINKSYNC_BT_MAC`.
- GitHub description still says BLE/Room — do not change remote settings unless asked.

## Test / verification

```bash
cd Python && python3 -m unittest discover -v
cd Android && JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home ./gradlew :app:testDebugUnitTest
```

## Fast-path

no
