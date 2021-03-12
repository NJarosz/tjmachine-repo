import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()


try:
    idn, name = reader.read()
    print("Current Info:", str(idn), name)
finally:
    GPIO.cleanup()
    
