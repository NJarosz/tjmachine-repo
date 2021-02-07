import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from datetime import date
import time
import csv

# TJ Machine number
PI_NUM = 100

# Sets GPIO layout
GPIO.setmode(GPIO.BCM)
# Sets up RFID Reader
reader = SimpleMFRC522()
# Sets up active GPIO's as variables
rfid_led = 12
err_led = 6
button = 16
relay1 = 4
relay2 = 17
relay3 = 27
relay4 = 22
relays = (relay1, relay2, relay3, relay4)

# Sets up Button
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Sets up RFID LED indicator
GPIO.setup(rfid_led, GPIO.OUT)

#Sets up Error LED
GPIO.setup(err_led, GPIO.OUT)

# Sets up Relays
GPIO.setup(relay1, GPIO.OUT)
GPIO.setup(relay2, GPIO.OUT)
GPIO.setup(relay3, GPIO.OUT)
GPIO.setup(relay4, GPIO.OUT)


#Creates functions to control GPIO pins.
# gpio_high() is OFF for Relays, on for LED
def gpio_high(gpio):
    GPIO.output(gpio, GPIO.HIGH)
# gpio_low() is ON for Relays, off for LED
def gpio_low(gpio):
    GPIO.output(gpio, GPIO.LOW)
    
    
 
def create_sequence(filename):
    """Creates the order of relay operations by 
    reading the text file.  Returns the sequence 
    as a dict and the part number being ran."""
    sequence = {}
    ind = 1
    with open(filename, 'r') as text:
        for line in text:
            if len(line.strip()) == 0:      #skips any blank lines
                pass
            elif "#" in line:
                pass
            else:
                try:
                    key, value = line.replace(' ', '').strip().split(",")
                    key = key.lower()
                    if "part" in key:
                        part = value
                    elif "mach" in key:
                        mach = value
                    elif key == "tmr":
                        value = float(value) / 1000
                        sequence[str(ind) + "- " + key] = value
                        ind += 1
                    elif key in ("on", "off"):
                        sequence[str(ind) + "- " + key] = "relay" + value
                        ind += 1
                    elif key not in ("on", "off", "tmr"):
                        sequence = {}
                        part = None
                        mach = None
                        return part, mach, sequence
                except:
                    sequence = {}
                    part = None
                    mach = None
                    return part, mach, sequence               
    return part, mach, sequence


def evaluate_seq(seq_dict, relays):
    """Catches any typos in relay numbers in the sequence 
    created by create_sequence(). If there's an invalid
    relay number in sequence, Error LED turns on."""
    b = False
    if seq_dict:
        b = True
        for key, value in seq_dict.items():
            if "on" in key or "off" in key:
                try:
                    if eval(value) in relays:
                        pass
                    elif eval(value) not in relays:
                        b = False
                        return b
                except:
                    b = False
    return b

def run_sequence(seq_dict, relays):
    """Uses the dictionary returned by
    create_sequence() to trigger relays/timers."""
    try:
        for key, value in seq_dict.items():
            if "on" in key:
                gpio_low(eval(value))
            elif "tmr" in key:
                time.sleep(value)
            elif "off" in key:
                gpio_high(eval(value))
        gpio_high(relays)
    except:
        gpio_high(relays)
        

def add_timestamp():
    """opens or creates a csv file with todays date in
    filename. Adds timestamp to that csv including machine
    number, part number, id number, user, time, date"""
    today = date.today()
    now = time.strftime("%H:%M:%S")
    data = (PI_NUM, mach_num, part_num, id_num, user.strip(), now, today)
    path = "/home/pi/Documents/CSV/"
    filename = today.strftime("%Y%m%d") + f"Machine{PI_NUM}.csv"
    with open(path + filename, "a", newline="") as fa, \
            open(path + filename, "r", newline='') as fr:
        writer = csv.writer(fa, delimiter=",")
        line = fr.readline() 
        if not line:  # if CSV is empty, add header
            header = ("Pi", "Machine", "Part", "Card_ID",
                      "User_ID", "Time", "Date")
            writer.writerow(header)
        writer.writerow(data)


        
# Initializes relays to the off positions
gpio_high(relays)
# Initializes rfid LED to off
gpio_low(rfid_led)
# Initializes Error LED
gpio_low(err_led)

# Instantiates the sequence
txt_file = "/home/pi/Desktop/instructions"
part_num, mach_num, seq = create_sequence(txt_file)

# Evaluates the sequence
test = evaluate_seq(seq, relays)

if test:
    try:
        while True:
            # Read info on RFID card, if present
            id_num, user = reader.read()

            if user is not None:
                gpio_high(rfid_led)

                # Waits 7 seconds for button press to run the sequence
                trigger = GPIO.wait_for_edge(button, GPIO.RISING, timeout=7000)
                if trigger:
                    run_sequence(seq, relays)
                    add_timestamp()
                elif trigger is None:
                    pass
                    
                gpio_low(rfid_led)   
                user = None

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("exit")

    except Exception as e:
        GPIO.cleanup()
        print(e)

else:
    gpio_high(err_led)
    time.sleep(10)
    gpio.cleanup()
