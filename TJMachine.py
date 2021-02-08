from gpiozero import LED, Button, OutputDevice
from mfrc522 import SimpleMFRC522
from datetime import date
import os
import time
import csv

# TJ Machine number
PI_NUM = '01'
    
# Sets up active GPIO's as variables
rfid_led = LED(12)
err_led = LED(5)

relay1 = OutputDevice(4, active_high=False)
relay2 = OutputDevice(17, active_high=False)
relay3 = OutputDevice(27, active_high=False)
relay4 = OutputDevice(22, active_high=False)
relays = (relay1, relay2, relay3, relay4)

button1 = Button(13, pull_up=True)

# Sets up RFID Reader
reader = SimpleMFRC522()


def read_main():
    """reads main to determine which
    file to read to create sequence"""
    main = "/home/pi/Desktop/main"
    with open(main, 'r') as m:
        txt = m.readline().rstrip("\n")
    return txt
 
def create_sequence(filename):
    """Creates the order of relay operations by reading
    the text file.  Returns the sequence as a dict 
    and the part number being ran."""
    sequence = {}
    part = None
    mach = None
    ind = 1
    with open(filename, 'r') as text:
        for line in text:
            if len(line.strip()) == 0:      #skips any blank lines
                pass
            elif "#" in line:
                pass
            else:
                try:
                    key, value = line.replace(' ','').strip().split(",")
                    key = key.lower()
                    if "part" in key:
                        part = value
                    elif "mach" in key:
                        mach = value
                    elif key == "tmr":
                        value = float(value) / 1000
                        sequence[str(ind) + "- " + key] = float(value)
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


# Instantiates the sequence
txt_file = read_main()
filename = "/home/pi/Desktop/" + str(txt_file)
part_num, mach_num, seq = create_sequence(filename)


def evaluate_seq(seq_dict, relays, part, mach):
    """tries to catch any typos in relay 
    numbers in the sequence created by
    create_sequence(). If there's an invalid
    relay number in sequence, error led
    turns on."""
    b = False
    if part == None or mach == None:
        return b 
    if len(part) == 0 or len(mach) == 0:
        return b
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


def add_timestamp():
    """opens or creates a csv file with todays date in
    filename. Adds timestamp to that csv including machine
    number, part number, id number, user, time, date"""
    today = date.today()
    now = time.strftime("%H:%M:%S")
    data = (PI_NUM, mach_num, part_num, id_num, user, now, today)
    path = "/home/pi/Documents/CSV/"
    filename = today.strftime("%Y%m%d") + f"PI{PI_NUM}.csv"
    with open(path + filename, "a", newline="") as fa, \
            open(path + filename, "r", newline='') as fr:
        writer = csv.writer(fa, delimiter=",")
        line = fr.readline()  # check if empty
        if not line:  # if empty, add header
            header = ("pi", "Machine", "Part", "Card_ID",
                      "User_ID", "Time", "Date")
            writer.writerow(header)
        writer.writerow(data)

def gpio_on(pin):
    pin.on()
    
def gpio_off(pin):
    pin.off()
    
def run_sequence(seq_dict=seq, relays=relays):
    """Uses the dictionary returned by
    create_sequence() to trigger relays/timers."""
    try:
        for key, value in seq_dict.items():
            if "on" in key:
                gpio_on(eval(value))
            elif "tmr" in key:
                time.sleep(value)
            elif "off" in key:
                gpio_off(eval(value))
        for relay in relays:
            relay.off()
    except:
        for relay in relays:
            relay.off()

        
# Evaluates the sequence
gate = evaluate_seq(seq, relays, part_num, mach_num)

if gate:
    try:
        while True:

            # Read info on RFID card, if present
            id_num, user = reader.read()
            user = user.strip()

            if user is not None:
                rfid_led.on()

                # Waits 7 seconds for button press to trigger relay
                if button1.wait_for_press(timeout=7):
                    if button1.wait_for_release():
                        run_sequence()
                        add_timestamp()
                user = None   
                rfid_led.off()
                

    except KeyboardInterrupt:
        for relay in relays:
            relay.off()
            
else:
    err_led.on()
    time.sleep(10)
