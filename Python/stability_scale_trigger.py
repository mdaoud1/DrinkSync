# File: stability_scale_trigger.py

import time
import sys
import math  # Required if using magnitude threshold

# Import the gyroscope library
try:
    from mpu6050 import mpu6050
except ImportError:
    print("ERROR: Could not import mpu6050 library.")
    print("Ensure it's installed (e.g., 'pip install mpu6050-raspberrypi')")
    sys.exit(1)

# Import functions from your scale script
# Ensure scale_persistent_tare.py is in the same directory or PYTHONPATH
try:
    import scale_persistent_tare as scale
except ImportError:
    print("ERROR: Could not import from scale_persistent_tare.py.")
    print("Ensure the file exists and is in the correct path.")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: An error occurred during import or initialization of the scale module: {e}")
    try:
        import RPi.GPIO as GPIO

        GPIO.cleanup()
        print("(Attempted basic GPIO cleanup)")
    except Exception as cleanup_e:
        print(f"(GPIO cleanup attempt failed: {cleanup_e})")
    sys.exit(1)

# --- Configuration ---
GYROSCOPE_I2C_ADDRESS = 0x68  # Default I2C address for MPU6050

# --- Stability Thresholds (*** ADJUST THESE VALUES! ***) ---
# Lower values mean it needs to be MORE still. Start higher and decrease.
GYRO_THRESHOLD_X = 4  # Max degrees/second allowed on X-axis for stability
GYRO_THRESHOLD_Y = 4  # Max degrees/second allowed on Y-axis for stability
GYRO_THRESHOLD_Z = 4  # Max degrees/second allowed on Z-axis for stability
# --- OR ---
# Optional: Use magnitude threshold instead of individual axes
# GYRO_MAGNITUDE_THRESHOLD = 3.0 # Example: sqrt(gx^2 + gy^2 + gz^2) < threshold

# --- Stability Duration ---
STABILITY_DURATION_REQUIRED = 3.0  # seconds
SAMPLE_INTERVAL = 0.1  # seconds between stability checks (10 Hz)
AWAITING_MOTION_TIMEOUT_S = 20.0

# --- State Variables ---
stability_start_time = None  # Tracks when the current stable period began
gyro_sensor = None  # Gyro sensor object
awaiting_motion = False  # After a reading, wait for a lift before the next one
awaiting_motion_since = None


# --- Main Function ---
def run_stability_monitor():
    global stability_start_time, gyro_sensor, awaiting_motion, awaiting_motion_since

    # --- Pre-checks ---
    # 1. Verify Scale Initialized (hx object should exist from import)
    if not scale.init_scale() or scale.hx is None:
        print("ERROR: Scale HX711 object was not initialized correctly.")
        print("The scale_persistent_tare.py script might have failed.")
        print("Cannot proceed without a working scale.")
        sys.exit(1)
    else:
        print("Scale module loaded and HX711 object appears initialized.")

    # 2. Initialize Gyroscope
    print(f"Initializing Gyroscope (MPU6050) at I2C address {hex(GYROSCOPE_I2C_ADDRESS)}...")
    try:
        gyro_sensor = mpu6050(GYROSCOPE_I2C_ADDRESS)
        # Optional: Add calibration/warm-up if library supports it or needed
        print("Gyroscope Initialized.")
        time.sleep(0.5)  # Small delay after init
    except Exception as e:
        print(f"FATAL ERROR: Failed to initialize MPU6050 sensor. Error: {e}")
        print("Check I2C connection, address (0x68 or 0x69?), and enable I2C in raspi-config.")
        # Attempt scale cleanup before exiting as scale *might* have initialized GPIO
        scale.cleanAndExit()
        sys.exit(1)

    # --- Monitoring Loop ---
    print(f"\nMonitoring for {STABILITY_DURATION_REQUIRED:.1f} seconds of stability...")
    print(f"Thresholds: Gyro(|X|,|Y|,|Z|) < ({GYRO_THRESHOLD_X}, {GYRO_THRESHOLD_Y}, {GYRO_THRESHOLD_Z}) deg/s")
    print("Press Ctrl+C to exit gracefully.")

    last_status_print_time = 0  # To avoid flooding the console

    while True:
        try:
            # 1. Read Gyroscope Data
            # It's good practice to handle potential errors during sensor reads
            try:
                gyro_data = gyro_sensor.get_gyro_data()
                gx = gyro_data['x']
                gy = gyro_data['y']
                gz = gyro_data['z']
            except Exception as read_err:
                print(f"\nWarning: Error reading gyroscope data: {read_err}")
                # Decide how to handle read errors - skip this cycle? Reset timer?
                stability_start_time = None  # Reset stability on sensor read error
                time.sleep(SAMPLE_INTERVAL * 2)  # Wait a bit longer after error
                continue  # Skip the rest of this loop iteration

            # 2. Check if Current Reading is Stable
            # --- Using individual axes ---
            is_stable_now = (abs(gx) < GYRO_THRESHOLD_X and
                             abs(gy) < GYRO_THRESHOLD_Y and
                             abs(gz) < GYRO_THRESHOLD_Z)
            # --- OR Using magnitude (uncomment the next 2 lines and comment out the block above) ---
            # gyro_magnitude = math.sqrt(gx**2 + gy**2 + gz**2)
            # is_stable_now = gyro_magnitude < GYRO_MAGNITUDE_THRESHOLD

            current_time = time.time()

            # Print current status periodically for feedback
            if current_time - last_status_print_time > 1.0:  # Print status once per second
                stability_status = "STABLE" if is_stable_now else "UNSTABLE"
                elapsed_stable_time = (current_time - stability_start_time) if stability_start_time else 0
                # Format gyro readings for cleaner output
                gyro_str = f"Gx={gx: >+6.1f}, Gy={gy: >+6.1f}, Gz={gz: >+6.1f}"
                print(f"Status: {stability_status: <8} | Stable Time: {elapsed_stable_time:4.1f}s | {gyro_str}",
                      end='\r')  # Use '\r' to update line
                last_status_print_time = current_time

            # 3. Update Stability Timer and Trigger Scale Reading
            if is_stable_now:
                if awaiting_motion:
                    if (
                        awaiting_motion_since is not None
                        and current_time - awaiting_motion_since >= AWAITING_MOTION_TIMEOUT_S
                    ):
                        awaiting_motion = False
                        awaiting_motion_since = None
                    else:
                        # Cup is still sitting. Do not re-read until it is lifted.
                        pass
                elif stability_start_time is None:
                    # Just became stable
                    stability_start_time = current_time
                    print("\n--> Stable condition met. Starting timer...      ",
                          end='\r')  # Extra spaces overwrite previous line
                    last_status_print_time = 0  # Force immediate status print update
                else:
                    # Already stable, check if duration met
                    elapsed_time = current_time - stability_start_time
                    if elapsed_time >= STABILITY_DURATION_REQUIRED:
                        print("\n*** Stability maintained for required duration! ***")  # Move to new line
                        print("--- Triggering Scale Reading ---")

                        # === CALL SCALE READING FUNCTION ===
                        weight = scale.take_reading()
                        # ===================================

                        if weight is not None:
                            print(f"--- Scale Reading Complete: {weight:.2f} grams ---")
                        else:
                            print("--- Scale Reading Failed (check scale script logs) ---")

                        print("\nWaiting for the cup to move before the next reading...")
                        awaiting_motion = True
                        awaiting_motion_since = current_time
                        stability_start_time = None
                        last_status_print_time = 0
                        time.sleep(0.5)

            else:  # Not stable now
                if awaiting_motion:
                    print("\n--> Motion detected. Ready for the next sip.     ", end='\r')
                elif stability_start_time is not None:
                    print("\n--> Unstable condition detected. Resetting timer...",
                          end='\r')
                awaiting_motion = False
                awaiting_motion_since = None
                stability_start_time = None
                last_status_print_time = 0

            # 4. Wait before next sample check
            time.sleep(SAMPLE_INTERVAL)

        except KeyboardInterrupt:
            print("\nCtrl+C detected. Exiting loop.")
            break  # Exit the while loop cleanly


# --- Script Execution ---
if __name__ == "__main__":
    try:
        run_stability_monitor()
    except Exception as main_err:
        # Catch unexpected errors in the main function itself
        print(f"\nAn unexpected error occurred in the main execution: {main_err}")
    finally:
        # This block executes whether the try block completed normally,
        # raised an exception, or exited via break (like Ctrl+C).
        print("\nExecuting final cleanup...")
        # Call the cleanup function imported from the scale script
        scale.cleanAndExit()
        print("Script finished.")
