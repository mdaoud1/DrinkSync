import time
import sys
import numpy as np
from protocol import format_weight_difference

try:
    import RPi.GPIO as GPIO
    from hx711 import HX711
except ImportError:
    GPIO = None
    HX711 = None

from bt import send_message


def cleanAndExit():
    print("\nCleaning up...")
    if GPIO is not None:
        GPIO.cleanup()
    print("Bye!")
    sys.exit()


def stable_tare(hx, samples=20):
    readings = []
    print("Taring... Please wait.")
    for _ in range(samples):
        readings.append(hx.get_weight(5))
        time.sleep(0.1)
    avg_tare = np.median(readings)
    hx.set_offset(avg_tare)
    print(f"Tare complete. Offset set to: {avg_tare}")


def get_filtered_weight(hx, samples=15):
    readings = [hx.get_weight(5) for _ in range(samples)]
    return np.median(readings)


def take_reading(hx):
    """
    Takes a 3-second average reading from the scale and sends it as a message using bt.py.
    """
    try:
        start_time = time.time()
        readings = []

        while time.time() - start_time < 3:
            readings.append(hx.get_weight(5))
            time.sleep(0.1)

        average_weight = np.mean(readings)

        message = format_weight_difference(average_weight)
        if send_message(message):
            print(f"Message sent successfully: {message}")
        else:
            print("Failed to send the message.")

        print(f"Raw Values: {readings}")
        print(f"Average Weight Sent: {average_weight:.2f} grams\n")

        hx.power_down()
        hx.power_up()
        time.sleep(0.5)

    except Exception as e:
        print(f"Error during reading: {e}")
        cleanAndExit()


if __name__ == "__main__":
    if GPIO is None or HX711 is None:
        print("Raspberry Pi GPIO / HX711 is not available on this machine.")
        sys.exit(1)

    hx = HX711(5, 6)
    hx.set_reading_format("MSB", "MSB")
    hx.reset()
    stable_tare(hx)
    hx.set_reference_unit(425.37)
    print("\nTare done! Ready to take readings...")
    print("scale.py is a manual helper. Uncomment the loop below to send readings.")
    # try:
    #     while True:
    #         take_reading(hx)
    #         time.sleep(1)
    # except (KeyboardInterrupt, SystemExit):
    #     print("Exiting...")
    #     cleanAndExit()
