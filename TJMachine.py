import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from datetime import date
import time
import csv

# TJ Machine number
MACH_NUM = 100
# Sets GPIO layout
GPIO.setmode(GPIO.BCM)
# Sets up RFID Reader
reader = SimpleMFRC522()
# Sets up button that triggers machine
someVar1=12
someVar2=22
relay1 = 4
relay2 = 17
relay3 = 27


GPIO.setup(someVar2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# Sets up RFID LED indicator
GPIO.setup(someVar1, GPIO.OUT)
GPIO.output(someVar1, GPIO.LOW)

# Creates functions to control RFID LED indicator
def rf_led_on():
    GPIO.output(someVar1, GPIO.HIGH)
def rf_led_off():
    GPIO.output(someVar1, GPIO.LOW)

# Sets up relays
GPIO.setup(relay1, GPIO.OUT)
GPIO.setup(relay2, GPIO.OUT)
GPIO.setup(relay3, GPIO.OUT)

# Sets up functions to control relays
def relay_on(relay):
    GPIO.output(relay, GPIO.LOW)

def relay_off(relay):
    GPIO.output(relay, GPIO.HIGH)

    
# Initializes relays to the off positions
relay_off((relay1, relay2, relay3))

"""Used to create and run sequence of relays.
Needs to be manually set for relays in physical use.
Set key as int to match physical relay number.
Set value to match variable name for that relay."""
rl_dict = {1: relay1, 2: relay2, 3: relay3}


def create_sequence(filename):
    """Creates the order of relay operations by reading
    the text file.  Returns the sequence as a dict 
    and the part number being ran."""
    sequence = {}
    ind = 1
    text = open(filename, 'r')
    for line in text:
        try:
            key, value = line.strip().split(",")
        except:
            pass
        if "part" in key.lower():
            part = value
        elif "tmr" in key.lower() or "trm" in key.lower():
            value = float(value) / 1000
            sequence[str(ind) + "- " + key] = float(value)
            ind += 1
        elif "on" in key.lower():
            sequence[str(ind) + "- " + key] = int(value)
            ind += 1
        elif "off" in key.lower():
            sequence[str(ind) + "- " + key] = int(value)
            ind += 1
    text.close()
    return part, sequence

# Instantiates the sequence
txt_file = "/home/pi/Desktop/instructions"
part_num, seq = create_sequence(txt_file)


def run_sequence(seq_dict):
    """Uses the dictionary returned by
    create_sequence() to trigger relays/timers."""
    try:
        for key, value in seq_dict.items():
            if "on" in key.lower():
                relay_on(rl_dict[value])
            elif "tmr" in key.lower() or "trm" in key.lower():
                time.sleep(value)
            elif "off" in key.lower():
                relay_off(rl_dict[value])
        for i in rl_dict.values():
            relay_off(i)
    except:
        for i in rl_dict.values():
            relay_off(i)


def csv_writer():
    """Used to create the csv file the
    data will be saved to.  Returns csv file,
    csv writer, and date of creation"""
    today = date.today()
    path = "/home/pi/Documents/CSV/"
    filename = today.strftime("%Y%m%d") + "Machine100.csv"
    fa = open(path + filename, "a", newline="")
    writer = csv.writer(fa, delimiter=",")
    fr = open(path + filename, "r", newline='')
    line = fr.readline()  # check if empty
    if not line:  # if empty, add header
        header = ("Machine", "Part", "Card_ID",
                  "User_ID", "Time", "Date")
        writer.writerow(header)
    fr.close()
    return fa, writer, today


#Instantiates the csv writer
csv_f, writer, today = csv_writer()

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
            csv_f, writer, today = csv_writer()

        # Read info on RFID card, if present
        id_num, user = reader.read()

        if user is not None:
            rf_led_on()         # Turns on RFID LED indicator
            
            # Waits 7 seconds for button press to trigger relay
            button = GPIO.wait_for_edge(22, GPIO.RISING, timeout=7000)
            if button is None:
                rf_led_off()
                pass
            else:
                run_sequence(seq)
                add_timestamp(writer, today)

            rf_led_off()        # Turns of RFID LED indicator
            user = None

except KeyboardInterrupt:
    GPIO.cleanup()
    csv_f.close()
    print("exit")

except Exception as e:
    GPIO.cleanup()
    csv_f.close()
    print(e)

