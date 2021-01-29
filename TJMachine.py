import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from datetime import date
import time
import csv

# TJ Machine number
MACH_NUM = 100

today = date.today()

# Sets GPIO layout
GPIO.setmode(GPIO.BCM)
# Sets up RFID Reader
reader = SimpleMFRC522()
# Sets up active GPIO's as variables
led = 12
button = 22
relay1 = 4
relay2 = 17
relay3 = 27
relays = (relay1, relay2, relay3)

"""Creates functions to control GPIO.
gpio_low() is ON for Relays, off for LED
gpio_high() is OFF for Relays, on for LED"""
def gpio_high(gpio):
    GPIO.output(gpio, GPIO.HIGH)
def gpio_low(gpio):
    GPIO.output(gpio, GPIO.LOW)

# Sets up Button
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Sets up RFID LED indicator
GPIO.setup(led, GPIO.OUT)

# Sets up Relays
GPIO.setup(relay1, GPIO.OUT)
GPIO.setup(relay2, GPIO.OUT)
GPIO.setup(relay3, GPIO.OUT)

# Initializes relays to the off positions
gpio_high((relay1, relay2, relay3))
# Initializes rfid LED to off
gpio_low(led)

def create_sequence(filename):
    """Creates the order of relay operations by reading
    the text file.  Returns the sequence as a dict 
    and the part number being ran."""
    sequence = {}
    ind = 1
    with open(filename, 'r') as text:
        for line in text:
            if len(line.strip()) == 0:      #skips any blank lines
                pass
            else:
                key, value = line.strip().split(",")
                if "part" in key.lower():
                    part = value
                elif "tmr" in key.lower() or "trm" in key.lower():
                    value = float(value) / 1000
                    sequence[str(ind) + "- " + key] = float(value)
                    ind += 1
                elif "on" in key.lower():
                    sequence[str(ind) + "- " + key] = "relay" + value
                    ind += 1
                elif "off" in key.lower():
                    sequence[str(ind) + "- " + key] = "relay" + value
                    ind += 1
    return part, sequence

# Instantiates the sequence
txt_file = "/home/pi/Desktop/instructions"
part_num, seq = create_sequence(txt_file)


def run_sequence(seq_dict, relays):
    """Uses the dictionary returned by
    create_sequence() to trigger relays/timers."""
    try:
        for key, value in seq_dict.items():
            if "on" in key.lower():
                gpio_low(eval(value))
            elif "tmr" in key.lower() or "trm" in key.lower():
                time.sleep(value)
            elif "off" in key.lower():
                gpio_high(eval(value))
    except:
        for relay in relays:
            gpio_high(relay)


def csv_writer(day):
    """Used to create or open the csv file the
    data will be saved to.  Returns csv file
    and csv writer.  If creating a new file, it 
    adds a header"""
    path = "/home/pi/Documents/CSV/"
    filename = day.strftime("%Y%m%d") + f"Machine{MACH_NUM}.csv"
    fa = open(path + filename, "a", newline="")
    writer = csv.writer(fa, delimiter=",")
    with open(path + filename, "r", newline='') as fr:
        line = fr.readline()  # check if empty
        if not line:  # if empty, add header
            header = ("Machine", "Part", "Card_ID",
                      "User_ID", "Time", "Date")
            writer.writerow(header)
    return fa, writer


#Instantiates the csv writer
csv_f, writer = csv_writer(today)

# Used to append data to csv created by csv_writer()
def add_timestamp(writer, day):
    now = time.strftime("%H:%M:%S")
    data = (MACH_NUM, part_num, id_num, user.strip(), now, day)
    writer.writerow(data)


try:
    while True:
        # Creates a new csv every day
        if date.today() != today:
            csv_f.close()
            today = date.today()
            csv_f, writer = csv_writer(today)

        # Read info on RFID card, if present
        id_num, user = reader.read()

        if user is not None:
            gpio_high(led)         # Turns on RFID LED indicator
            
            # Waits 7 seconds for button press to trigger relay
            button = GPIO.wait_for_edge(22, GPIO.RISING, timeout=7000)
            if button is None:
                gpio_low(led)
                pass
            else:
                run_sequence(seq, relays)
                add_timestamp(writer, today)

            gpio_low(led)        # Turns off RFID LED indicator
            user = None

except KeyboardInterrupt:
    GPIO.cleanup()
    csv_f.close()
    print("exit")

except Exception as e:
    GPIO.cleanup()
    csv_f.close()
    print(e)
