from gpiozero import LED, Button, OutputDevice
from mfrc522 import SimpleMFRC522
import I2C_LCD_driver
from datetime import date
import time
import csv

# PLC Number
with open("/etc/hostname", "r") as hn:
    pi = hn.readline().rstrip("\n")
    
# Sets up active GPIO's as variables

relay1 = OutputDevice(4, active_high=False)
relay2 = OutputDevice(17, active_high=False)
relay3 = OutputDevice(27, active_high=False)
relay4 = OutputDevice(22, active_high=False)
relays = (relay1, relay2, relay3, relay4)
button1 = Button(26, pull_up=True)

# Variables/paths
csv_path = "/home/pi/Documents/CSV/"
file_path = ""
count_path = "/home/pi/Documents/totalcount"
main = "/home/pi/Desktop/main"
shot = "SHOT"
lcd = I2C_LCD_driver.lcd()

def read_main(path=main):
    """reads main to determine which
    file to read to create sequence"""
    with open(path, 'r') as m:
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


def read_count(file=count_path):
    """Reads/ returns running total part count"""
    with open(file, "r", newline="") as f:
        total_count = f.readline()
        if len(str(total_count)) == 0:
            total_count = 0
        else:
            total_count = int(total_count)
    return total_count


def write_count(part_count, file=count_path):
    """Writes total part count to totalcount file"""
    if part_count > 999999:
        part_count = 0
    with open(file, "w") as f:
        f.write(str(part_count))


count = read_count()

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

def create_file_path(day, path=csv_path):
    """Creates a new file path from today's date and pi name"""
    filename = day.strftime("%Y%m%d") + f"{pi}.csv"
    file_path = path + filename
    return file_path

def create_csv(file):
    """creates a new csv file, inserts a header"""
    with open(file, "a", newline="") as fa, \
            open(file, "r", newline='') as fr:
        writer = csv.writer(fa, delimiter=",")
        line = fr.readline()
        if not line:  # if CSV is empty, add header
            header = ("Type", "pi", "Machine", "Part",
                      "User_ID", "Time", "Date")
            writer.writerow(header)

def add_timestamp(cat, file):
    """opens or creates a csv file with todays date in
    filename. Adds timestamp to that csv including machine
    number, part number, id number, user, time, date"""
    now = time.strftime("%H:%M:%S")
    data = (cat, pi, mach_num, part_num, emp_num, now, today)
    with open(file, "a", newline="") as fa:
        writer = csv.writer(fa, delimiter=",")
        writer.writerow(data)


def update_csv():
    """Updates the CSV file path with Today's date
    and creates a new csv from that file name"""
    today = date.today()
    file_path = create_file_path(day=today)
    create_csv(file=file_path)
    return today, file_path

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
    lcd.clear()
    today, file_path = update_csv()

    try:
        while True:

            # Read info on RFID card, if present
            #id_num, user = reader.read()
            user = "tj user"
            lcd.message(f"{part_num} {mach_num}",1)
            if user != None:
                lcd.message(f"Cnt: {count}",2)
                # Waits 7 seconds for button press to trigger relay
                if button1.is_pressed:
                    button1.wait_for_release()
                    run_sequence()
                    add_timestamp(shot, file_path)
                    count += 1
                    write_count(count)

                if date.today() != today:
                    today, file_path = update_csv()
                


        
    except KeyboardInterrupt:
        for relay in relays:
            relay.off()

    except Exception as e:
        print(e)
        lcd.clear()
        lcd.message("except",1)
        time.sleep(10)

            
else:
    lcd.clear()
    lcd.message("NOTWORK",1)
    time.sleep(10)
