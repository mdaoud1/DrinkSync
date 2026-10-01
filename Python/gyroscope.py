# Import the mpu6050 class and sleep function from respective modules.
from time import sleep

# Initialize the MPU-6050 sensor with the I2C address 0x68 only when run directly.


def main():
    from mpu6050 import mpu6050

    sensor = mpu6050(0x68)

    while True:
        accel_data = sensor.get_accel_data()
        gyro_data = sensor.get_gyro_data()
        temp = sensor.get_temp()

        print("Accelerometer data")
        print("x: " + str(accel_data["x"]))
        print("y: " + str(accel_data["y"]))
        print("z: " + str(accel_data["z"]))

        print("Gyroscope data")
        print("x: " + str(gyro_data["x"]))
        print("y: " + str(gyro_data["y"]))
        print("z: " + str(gyro_data["z"]))

        print("Temp: " + str(temp) + " C")

        sleep(0.5)


if __name__ == "__main__":
    main()
