import time
import sys
import numpy as np
import os

from bt import send_message
from drink_math import next_drink
from protocol import format_weight_difference
from scale_config import load_scale_config, save_scale_config

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

try:
    from hx711 import HX711
except ImportError:
    HX711 = None

# --- Configuration ---
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scale_config.json")
DEFAULT_REFERENCE_UNIT = 425.37
STABLE_TARE_SAMPLES = 20
GET_WEIGHT_SAMPLES = 5
TAKE_READING_DURATION_S = 3
TAKE_READING_SAMPLE_DELAY = 0.1
DOUT_PIN = 5
PD_SCK_PIN = 6

hx = None
initial_max_weight = None
last_weight = None
_initialized = False


def cleanAndExit():
    """Cleans up GPIO resources and exits."""
    print("\nCleaning up GPIO...")
    try:
        if hx:
            hx.power_down()
    except Exception as e:
        print(f"  Warning: Could not power down HX711 during cleanup: {e}")
    if GPIO is not None:
        try:
            GPIO.cleanup()
        except Exception as e:
            print(f"  Warning: GPIO cleanup failed: {e}")
    print("Bye!")
    sys.exit()


def persist_last_weight():
    if last_weight is None:
        return
    config = {
        "offset": hx.get_offset() if hx else None,
        "referenceUnit": hx.get_reference_unit() if hx else None,
        "initialMaxWeight": initial_max_weight,
        "lastWeight": last_weight,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            loaded = load_scale_config(CONFIG_FILE)
            config["offset"] = loaded["offset"]
            config["referenceUnit"] = loaded["referenceUnit"]
            if config["initialMaxWeight"] is None:
                config["initialMaxWeight"] = loaded["initialMaxWeight"]
        except Exception:
            pass
    if config["offset"] is None or config["referenceUnit"] is None:
        return
    try:
        save_scale_config(CONFIG_FILE, config)
    except Exception as e:
        print(f"Warning: Failed to persist last weight: {e}")


def stable_tare(hx_instance, samples=STABLE_TARE_SAMPLES):
    """Tare the scale and return the calculated offset."""
    if not hx_instance:
        print("Error: HX711 instance not provided for tare.")
        return None

    readings = []
    print("Taring... Please ensure scale is empty and stable.")
    try:
        hx_instance.power_down()
        hx_instance.power_up()
        time.sleep(0.5)
    except Exception as e:
        print(f"  Warning: Error during power cycle before tare: {e}")

    for i in range(samples):
        try:
            raw_reading = hx_instance.read_average(times=GET_WEIGHT_SAMPLES)
            if raw_reading is not False:
                readings.append(raw_reading)
                print(f"  Tare sample {i+1}/{samples}: {raw_reading}")
            else:
                print(f"  Warning: Got invalid raw reading during tare sample {i+1}")
            time.sleep(0.1)
        except Exception as e:
            print(f"  Error getting raw data during tare: {e}")

    if not readings:
        print("ERROR: Could not get any valid readings during tare. Cannot set offset.")
        return None

    avg_tare_offset = np.median(readings)
    hx_instance.set_offset(avg_tare_offset)
    print(f"Tare complete. Offset set to: {avg_tare_offset}")
    time.sleep(0.5)
    return avg_tare_offset


def take_reading():
    """Average the scale, send only the incremental sip, and return grams sent."""
    global hx, last_weight
    if not hx:
        print("Error: Scale (hx) not initialized. Cannot take reading.")
        return None

    try:
        start_time = time.time()
        readings = []
        print(f"Taking reading for {TAKE_READING_DURATION_S} seconds...")

        hx.power_down()
        hx.power_up()
        time.sleep(0.1)

        while time.time() - start_time < TAKE_READING_DURATION_S:
            try:
                val = hx.get_weight(GET_WEIGHT_SAMPLES)
                if val is not False and abs(val) < 100000:
                    readings.append(val)
                else:
                    print(f"  Warning: Discarding potentially erroneous reading: {val}")
                time.sleep(TAKE_READING_SAMPLE_DELAY)
            except OverflowError:
                print("  Warning: Overflow error during reading, discarding value.")
            except Exception as e:
                print(f"  Warning: Error during individual weight reading: {e}")

        if not readings:
            print("Error: No valid readings collected.")
            return None

        current_weight = float(np.median(readings))
        grams, new_previous = next_drink(last_weight, current_weight)

        if grams is None:
            last_weight = new_previous
            persist_last_weight()
            print(
                f"No drink event (current={current_weight:.2f} g, baseline={last_weight:.2f} g)"
            )
            hx.power_down()
            return None

        if initial_max_weight is not None and grams > initial_max_weight:
            print(
                f"Warning: Discarding implausible drink {grams:.2f} g "
                f"(above max {initial_max_weight:.2f} g)"
            )
            hx.power_down()
            return None

        message = format_weight_difference(grams)
        if send_message(message):
            last_weight = new_previous
            persist_last_weight()
            print(f"Message sent successfully: {message}")
        else:
            print(f"Failed to send the message: {message}")
            hx.power_down()
            return None

        hx.power_down()
        return grams

    except Exception as e:
        print(f"Error during take_reading: {e}")
        try:
            if hx:
                hx.power_down()
        except Exception:
            pass
        return None


def init_scale():
    """Initialize HX711 from saved config, or tare on first run."""
    global hx, initial_max_weight, last_weight, _initialized
    if _initialized:
        return hx is not None
    _initialized = True

    if GPIO is None or HX711 is None:
        print("ERROR: Raspberry Pi GPIO / HX711 is not available on this machine.")
        return False

    print("--- Initializing Scale ---")
    config_loaded_successfully = False
    loaded_offset = None
    loaded_reference_unit = None
    loaded_initial_max_weight = None
    loaded_last_weight = None

    if os.path.exists(CONFIG_FILE):
        print(f"Found configuration file: {CONFIG_FILE}")
        try:
            loaded = load_scale_config(CONFIG_FILE)
            loaded_offset = loaded["offset"]
            loaded_reference_unit = loaded["referenceUnit"]
            loaded_initial_max_weight = loaded.get("initialMaxWeight")
            loaded_last_weight = loaded.get("lastWeight")
            print("Successfully loaded configuration:")
            print(f"  Offset: {loaded_offset}")
            print(f"  Reference Unit: {loaded_reference_unit}")
            if loaded_initial_max_weight is not None:
                print(f"  Initial Max Weight: {loaded_initial_max_weight:.2f} grams")
            if loaded_last_weight is not None:
                print(f"  Last weight: {loaded_last_weight:.2f} grams")
            config_loaded_successfully = True
        except Exception as e:
            print(f"Warning: Error reading config file '{CONFIG_FILE}'. Error: {e}")
            print("Ignoring invalid or incomplete config file. Will perform tare.")

    try:
        hx = HX711(DOUT_PIN, PD_SCK_PIN)
        hx.set_reading_format("MSB", "MSB")
        print("HX711 sensor initialized.")
    except Exception as e:
        print(f"FATAL ERROR: Failed to initialize HX711 sensor. Error: {e}")
        print("Check GPIO connections, permissions, and numbering scheme (BCM).")
        if GPIO is not None:
            GPIO.cleanup()
        hx = None
        return False

    if config_loaded_successfully and loaded_offset is not None and loaded_reference_unit is not None:
        print("Applying loaded offset and reference unit...")
        hx.set_offset(loaded_offset)
        hx.set_reference_unit(loaded_reference_unit)
        initial_max_weight = loaded_initial_max_weight
        last_weight = loaded_last_weight
        hx.power_down()
        hx.power_up()
        time.sleep(0.5)
        print("Scale configured using saved settings.")
    else:
        print("No valid configuration found or loaded. Performing initial tare...")
        hx.reset()
        calculated_offset = stable_tare(hx)

        if calculated_offset is not None:
            current_reference_unit = DEFAULT_REFERENCE_UNIT
            hx.set_reference_unit(current_reference_unit)
            print(f"Reference unit set to default: {current_reference_unit}")

            print("\nTaking initial 'max' measurement...")
            print("Ensure the item representing the maximum weight is on the scale NOW.")
            time.sleep(10)

            try:
                hx.power_down()
                hx.power_up()
                time.sleep(0.5)
                first_measurement_val = hx.get_weight(GET_WEIGHT_SAMPLES)
                if first_measurement_val is not False:
                    initial_max_weight = first_measurement_val
                    last_weight = first_measurement_val
                    print(f"Initial 'max' weight measured: {initial_max_weight:.2f} grams")
                else:
                    print("Warning: Failed to get valid initial 'max' weight reading.")
                    initial_max_weight = None
            except Exception as e:
                print(f"ERROR: Could not take initial 'max' weight measurement: {e}")
                initial_max_weight = None

            print(f"Saving configuration to {CONFIG_FILE}...")
            try:
                save_scale_config(
                    CONFIG_FILE,
                    {
                        "offset": calculated_offset,
                        "referenceUnit": current_reference_unit,
                        "initialMaxWeight": initial_max_weight,
                        "lastWeight": last_weight,
                    },
                )
                print("Configuration saved successfully.")
            except Exception as e:
                print(f"Warning: Failed to save configuration to {CONFIG_FILE}. Error: {e}")

            hx.power_down()
        else:
            print("ERROR: Tare process failed. Scale may not read accurately.")
            hx.set_reference_unit(DEFAULT_REFERENCE_UNIT)
            initial_max_weight = None

    print("\n--- Scale Ready ---")
    if initial_max_weight is not None:
        print(f"Current Initial Max Weight set to: {initial_max_weight:.2f} grams")
    else:
        print("Initial Max Weight is not set (optional).")
    return True


if __name__ == "__main__":
    print("\nRunning direct execution test loop...")
    try:
        if not init_scale():
            sys.exit(1)
        while True:
            input("Press Enter to take a reading (or Ctrl+C to exit)...")
            weight = take_reading()
            if weight is not None:
                print(f"--> Drink sent: {weight:.2f} grams")
            else:
                print("--> No drink sent.")
    except (KeyboardInterrupt, SystemExit):
        print("\nExit requested.")
    finally:
        cleanAndExit()
