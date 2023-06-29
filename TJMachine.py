from gpiozero import LED, Button, OutputDevice
from mfrc522 import SimpleMFRC522
import I2C_LCD_driver
from datetime import date, timedelta, datetime
import time
import csv
import os
import pickle
import mysql.connector

# PLC Number
with open("/etc/hostname", "r") as hn:
    pi = hn.readline().rstrip("\n")

    
count_num = int(''.join(i for i in pi if i.isdigit()))

# Sets up active GPIO's as variables

relay1 = OutputDevice(4, active_high=False)
relay2 = OutputDevice(17, active_high=False)
relay3 = OutputDevice(27, active_high=False)
relay4 = OutputDevice(22, active_high=False)
relays = (relay1, relay2, relay3, relay4)
hand_button = Button(26, pull_up=True)
gr_button = Button(16, pull_up=True, hold_time=2)
red_button = Button(12, pull_up=True, hold_time=3)
rfid_bypass = Button(23, pull_up=True)
reader = SimpleMFRC522()
lcd = I2C_LCD_driver.lcd()


# Variables/paths
csv_path = "/home/pi/Documents/CSV/"
count_pkl = "/home/pi/Documents/counts.pickle"
production_info = "/home/pi/Documents/production_info.txt"
employee_info = "/home/pi/Documents/employee_info.txt"
main = "/home/pi/Desktop/main"
file_path = ""
mode = "refresh"
startup = True

logon = "LOG_ON"
logout = "LOG_OFF"
timeout = "TIME_OUT"
shot = "SHOT"

#LCD Messages
csv_msg = "Updating CSV"
load_program_msg = "Loading Program"
load_part_msg = "Loading Part Info"
load_emp_msg = "Loading Emp Info"
load_count_msg = "Loading Count"
invalid_data_msg = "Invalid Data"
invalid_program_top = "Invalid Seq"
invalid_program_btm = "Grn=Try Again"
menu_msg_top = "Reset Counter?"
menu_msg_btm = "Gr=Yes Red=No"
count_reset_msg = "Counter= 0"
logoutm = "Logged Out"
timeoutm = "Timed Out"
db_name = "device_vars"



# Functions

def read_pckl_counts(pcklfile):
    # Retrieves backup info stored in pickle files
    pickle_in = open(pcklfile, "rb")
    pkl_dict = pickle.load(pickle_in)
    return pkl_dict

def save_vars(dict, pkl_file):
    # Saves info to pickle files as a backup
    with open(pkl_file, "wb") as pckl:
        pickle.dump(dict, pckl)

def read_production_info(filename=production_info):
    """Reads the part, machine, and count goal info from the production info text file
    saved in Documents.  Returns each value, and returns dummy values if not valid"""
    with open(filename, 'r') as text:
        for line in text:
            if len(line.strip()) == 0:      #skips any blank lines
                pass
            elif "#" in line:
                pass
            else:
                try:
                    valid = True
                    key, value = line.replace(' ','').strip().split(",")
                    key = key.lower()
                    if key == "part":
                        part = value
                    elif key == "mach":
                        machine = value
                    elif key == "count_goal":
                        count_goal = int(value)
                except:
                    part = "999"
                    machine = "UNK"
                    count_goal = 0
                    valid = False

    return part, machine, count_goal, valid

    
def ret_emp_names(filename=employee_info):
    # Attempts to retrieve employee name from DB based on the number on their ID card
    emps = {}
    with open(filename, 'r') as text:
        for line in text:
            if len(line.strip()) == 0:  # skips any blank lines
                pass
            elif "#" in line:
                pass
            else:
                key, value = line.replace(' ', '').strip().split(",")
                key = key.lower()
                emps[key] = value

    return emps


employees = ret_emp_names()

def read_main(path=main):
    """reads main to determine which
    file to read to create sequence"""
    with open(path, 'r') as m:
        txt = m.readline().rstrip("\n")
    return txt
 
def create_sequence():
    """Creates the order of relay operations by reading
    the text file.  Returns the sequence as a dict 
    and the part number being ran."""
    txt_file = read_main()
    filename = "/home/pi/Desktop/" + str(txt_file)
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
                    key, value = line.replace(' ','').strip().split(",")
                    key = key.lower()
                    if key == "tmr":
                        value = float(value) / 1000
                        sequence[str(ind) + "- " + key] = float(value)
                        ind += 1
                    elif key in ("on", "off"):
                        sequence[str(ind) + "- " + key] = "relay" + value
                        ind += 1
                    elif key not in ("on", "off", "tmr"):
                        sequence = {}
                        return sequence
                except:
                    sequence = {}
    return sequence


# Instantiates the sequence
seq = create_sequence()


def evaluate_params(part, mach, countset, dicti):
    b = False
    try:
        if part != None and len(part) != 0:
            if mach != None and len(mach) != 0:
                if type(countset) == int:
                    b = True
                    dicti['part'] = part
                    dicti['mach'] = mach
                    dicti['countset'] = countset
    except:
        b = False
    return b, dicti

def update_counts(totalcount, runcount):
    global count_dict
    totalcount +=1
    runcount +=1
    count_dict['totalcount'] = totalcount
    count_dict['runcount'] = runcount
    return totalcount, runcount

def count_reset(runcount):
    global count_dict
    runcount = 0
    count_dict['runcount'] = runcount
    save_vars(count_dict, count_pkl)
    lcd.clear()
    lcd.message("PRESS BLK BTN",1)
    lcd.message("TO RESET", 2)
    return runcount
                

def create_file_path(day, path=csv_path):
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
    data = (cat, count_num, mach_num, part_num, emp_num, now, today)
    with open(file, "a", newline="") as fa:
        writer = csv.writer(fa, delimiter=",")
        writer.writerow(data)

def update_csv():
    today = date.today()
    file_path = create_file_path(day=today)
    create_csv(file=file_path)
    return today, file_path


def display_run_info(last_display, last_disp_time):
    lcd.message(run_msg_btm, 2)
    if datetime.now() > last_disp_time + timedelta(seconds=5):
        if last_display != 1:
            lcd.message("                ",1)
            lcd.message(run_msg_top1, 1)
            last_display = 1
        else:
            lcd.message("                ",1)
            lcd.message(run_msg_top2, 1)
            last_display = 0
        last_disp_time = datetime.now()
    return last_display, last_disp_time

def change_msg(msg, sec=1, line=1):
    lcd.clear()
    lcd.message(msg, line)
    time.sleep(sec)

def logout_func(file_path):
    add_timestamp(logout, file_path)
    change_msg(logoutm, sec=1)


def evaluate_seq(seq_dict, relays):
    """tries to catch any typos in relay 
    numbers in the sequence created by
    create_sequence(). If there's an invalid
    relay number in sequence, error led
    turns on."""
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

def invalid_sequence():
    lcd.clear()
    lcd.message(invalid_program_top)
    time.sleep(60)
    lcd.clear()


def invalid_params():
    lcd.clear()
    lcd.message(invalid_data_msg)
    time.sleep(60)
    lcd.clear()

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


try:    
    while True:
        if mode == "standby":
            emp_name = None
            emp_num = None
            idn = None

            lcd.clear()
            standby_info_top = f"Part:{part_num}"
            standby_info_btm = f"Cnt:{total_count} Mch:{mach_num}"
            lcd.message(standby_info_top, 1)
            lcd.message(standby_info_btm, 2)


            while mode == "standby":
                if date.today() != today:
                    today, file_path = update_csv()

                if red_button.is_held:
                    lcd.clear()
                    red_button.wait_for_release()
                    time.sleep(0.2)
                    mode = "refresh"

                if rfid_bypass.is_pressed:
                    if gr_button.is_pressed:
                        gr_button.wait_for_release()
                        emp_num = 999
                        emp_count = 0
                        add_timestamp(logon, file_path)
                        mode = "run"

                else:
                    if gr_button.is_pressed:
                        gr_button.wait_for_release()
                        idn, emp_num = reader.read_no_block()
                        if emp_num != None:
                            emp_num = emp_num.strip()
                            if emp_num == '':
                                pass
                            else:
                                emp_name = employees[emp_num]
                                emp_count = 0
                                add_timestamp(logon, file_path)
                                mode = "run"


        elif mode == "refresh":

            #Load the Program
            lcd.message(load_program_msg, 1)
            seq = create_sequence()
            print(seq)
            sequence_test = evaluate_seq(seq, relays)
            time.sleep(1)
            if sequence_test is True:
                #Load part info
                lcd.clear()
                lcd.message(load_part_msg, 1)
                part_num, mach_num, count_goal, valid_info = read_production_info()
                time.sleep(1)
                if valid_info is True:
                    #Load employee info
                    lcd.clear()
                    lcd.message(load_emp_msg, 1)
                    employees = ret_emp_names()
                    time.sleep(1)
                else:
                    lcd.clear()
                    lcd.display(invalid_data_msg, 1)
            else:
                lcd.clear()
                lcd.display(invalid_program_top,1)
                lcd.display(invalid_program_btm,2)

            if startup is True:
                startup = False
                #Update the CSV
                lcd.clear()
                lcd.message(csv_msg, 1)
                today, file_path = update_csv()
                time.sleep(1)
                #Load the counts
                lcd.clear()
                lcd.message(load_count_msg)
                count_dict = read_pckl_counts(count_pkl)
                total_count = count_dict['totalcount']
                run_count = count_dict['runcount']
                time.sleep(1)
                mode = "standby"
            else:
                #Give option to Reset Counts
                lcd.clear()
                time.sleep(.5)
                lcd.message(menu_msg_top, 1)
                lcd.message(menu_msg_btm, 2)
                while mode == "refresh":
                    if gr_button.is_pressed:
                        gr_button.wait_for_release()
                        count_dict["totalcount"] = 0
                        count_dict["runcount"] = 0
                        save_vars(count_dict, count_pkl)
                        change_msg(count_reset_msg, sec=3)
                        mode = "standby"
                    if red_button.is_pressed:
                        red_button.wait_for_release()
                        mode = "standby"
                        lcd.clear()

        elif mode == "run":
            run_msg_top1 = f"Part: {part_num} "
            if emp_name != None:
                run_msg_top2 = f"Emp: {emp_name}"
            else:
                run_msg_top2 = f"Emp: {emp_num}"
            last_display = 0
            last_disp_time = datetime.now()
            now = datetime.now()
            lcd.clear()
            lcd.message(run_msg_top2, 1)
            print(seq)
            while mode == "run":
                run_msg_btm = f"Cnt:{emp_count}, {total_count}"
                last_display, last_disp_time = display_run_info(last_display, last_disp_time)
                if count_goal == 0:
                    pass
                elif run_count == count_goal:
                    run_count = count_reset(run_count)
                    gr_button.wait_for_press()
                    gr_button.wait_for_release()
                    lcd.clear()
                    lcd.message(run_msg_top2, 1)
                if datetime.now() >= now + timedelta(seconds=1):
                    if hand_button.is_pressed:
                        run_sequence(seq_dict=seq)
                        emp_count += 1
                        total_count, run_count = update_counts(total_count, run_count)
                        save_vars(count_dict, count_pkl)
                        add_timestamp(shot, file_path)
                        hand_button.wait_for_release()
                        now = datetime.now()
                if datetime.now() >= now + timedelta(seconds=300):
                    add_timestamp(timeout, file_path)
                    change_msg(timeoutm, sec=5)
                    mode = "standby"
                if red_button.is_pressed:
                    red_button.wait_for_release()
                    logout_func(file_path)
                    mode = "standby"


except KeyboardInterrupt:
    lcd.clear()
except Exception as e:
    lcd.clear()
    lcd.message("ERROR")
    print(e)
    counts_dict = {"totalcount": 0,
               "runcount": 0}
    save_vars(counts_dict, count_pkl)
    time.sleep(5)
    os.system("reboot")
