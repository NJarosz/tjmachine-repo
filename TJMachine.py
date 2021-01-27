import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
from datetime import date
import time
import csv

# TJ Machine number
mach_num = 100
# set GPIO layout
GPIO.setmode(GPIO.BCM)
# RFID Reader
reader = SimpleMFRC522()
# Button
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# RFID LED indicator
GPIO.setup(12, GPIO.OUT)
GPIO.output(12, GPIO.LOW)


def rf_led_on():
    GPIO.output(12, GPIO.HIGH)


def rf_led_off():
    GPIO.output(12, GPIO.LOW)


# Relays
relay1 = 4
GPIO.setup(relay1, GPIO.OUT)

relay2 = 17
GPIO.setup(relay2, GPIO.OUT)

relay3 = 27
GPIO.setup(relay3, GPIO.OUT)


def relay_on(relay):
    GPIO.output(relay, GPIO.LOW)


def relay_off(relay):
    GPIO.output(relay, GPIO.HIGH)


relay_off((relay1, relay2, relay3))

"""Used to create and run sequence of relays
Needs to be manually set for relays in physical use
Set key as int to match physical relay number
Set value to match variable name for that relay"""
rl_dict = {1: relay1, 2: relay2, 3: relay3}


def create_sequence(filename):
    """creates the order of relay operations from
    the text file.  Returns the sequence and part
    number being ran"""
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


txt_file = "/home/pi/Desktop/instructions"
part_num, seq = create_sequence(txt_file)


def run_sequence(seq_dict):
    """uses the dictionary returned by
    create_sequence to trigger relays/timers"""
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
    """used to create the dated csv file the
    data will be saved to.  Returns csv writer
    csv file, and date of creation"""
    today = date.today().strftime("%Y%m%d")
    path = "/home/pi/Documents/CSV/"
    filename = today + "Machine100.csv"

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


csv_f, writer, today = csv_writer()


# append data to csv
def add_timestamp():
    now = time.strftime("%H:%M:%S")
    day = date.today()
    data = (mach_num, part_num, id_num, user.strip(), now, day)
    writer.writerow(data)


try:
    while True:
        # create a new csv every day
        if date.today().strftime("%Y%m%d") != today:
            csv_f.close()
            csv_f, writer, today = csv_writer()

        # read RFID card
        id_num, user = reader.read()

        if user is not None:
            rf_led_on()
            # wait up for 7 seconds for button press to trigger relay
            button = GPIO.wait_for_edge(22, GPIO.RISING, timeout=7000)
            if button is None:
                rf_led_off()
                pass
            else:
                run_sequence(seq)
                add_timestamp()

            rf_led_off()
            user = None

except KeyboardInterrupt:
    GPIO.cleanup()
    csv_f.close()
    print("exit")

except Exception as e:
    GPIO.cleanup()
    csv_f.close()
    print(e)


