import time
from hardware import gate1, pulse_solenoid, USE_GPIO

if not USE_GPIO:
    print("USE_GPIO is False – turn it on in hardware.py")
    quit()

print("Pulsing gate1 every 2 seconds. Ctrl+C to stop.")

while True:
    pulse_solenoid(gate1, 0.2)  # 200 ms pulse
    time.sleep(2)
