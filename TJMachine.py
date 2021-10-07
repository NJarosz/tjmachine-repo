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
hand_button = Button(26, pull_up=True, hold_time=3)
gr_button = Button(13, pull_up=True, hold_time=1)
red_button = Button(12, pull_up=True, hold_time=1)
rfid_bypass = Button (23, pull_up=True)
reader = SimpleMFRC522()
lcd = I2C_LCD_driver.lcd()


# Variables/paths
csv_path = "/home/pi/Documents/CSV/"
count_pkl = "/home/pi/Documents/counts.pickle"
prod_vars_pkl = "/home/pi/Documents/vars.pickle"
main = "/home/pi/Desktop/main"
file_path = ""
logon = "LOG_ON"
logout = "LOG_OFF"
timeout = "TIME_OUT"
mas = "MAS"
mae = "MAE"
shot = "SHOT"
modes = {"setup": 0,
         "standby": 1,
         "menu": 2,
         "run": 3,
         "maint": 4
         }
mode = modes["standby"]
startup = True
maint_msg = "Maintenance"
maint_end_msg = "Maintenance End"
invalid_msg = "Invalid Data"
invalid_seq = "Invalid Seq"
menu_msg_top = "Reset Counter?"
menu_msg_btm = "Gr=Yes Red=No"
count_reset_msg = "Counter= 0"
logoutm = "Logged Out"
timeoutm = "Timed Out"
db_name = "tjtest"


try:
    db_host = '10.0.0.167'
    db_user = os.environ.get("DB_USER_1")
    db_psw = os.environ.get("DB_PSW_1")
except:
    pass

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

prod_vars_dict = read_pckl_counts(prod_vars_pkl)

def read_machvars_db(count_num=count_num):
    # Attempts to pull current production variables from DB, or else from Pickle Files
    try:
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            passwd=db_psw,
            database=db_name
        )
        c = conn.cursor()
        c.execute("SELECT part FROM data_vars WHERE device_id=%s", (count_num,))
        part = c.fetchone()
        part = str(part[0])

        c.execute("SELECT machine FROM data_vars WHERE device_id=%s", (count_num,))
        mach = c.fetchone()
        mach = str(mach[0])

        c.execute("SELECT count_goal FROM data_vars WHERE device_id = %s", (count_num,))
        countset = c.fetchone()
        countset = int(countset[0])
        c.close()
    except:
        part = str(prod_vars_dict['part'])
        mach = str(prod_vars_dict['mach'])
        countset = int(prod_vars_dict['countset'])

    return part, mach, countset
    
def ret_emp_name(id_num):
    # Attempts to retrieve employee name from DB based on the number on their ID card
    try:
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            passwd=db_psw,
            database=db_name
        )
        c = conn.cursor()
        c.execute("SELECT name FROM employees WHERE emp_id=%s", (id_num,))
        emp_name=c.fetchone()
        emp_name=str(emp_name[0])
        c.close()
        return emp_name
    except:
        return None

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
txt_file = read_main()
filename = "/home/pi/Desktop/" + str(txt_file)
seq = create_sequence(filename)


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
    lcd.message(invalid_seq)
    time.sleep(30)
    lcd.clear()


def invalid_params():
    lcd.clear()
    lcd.message(invalid_msg)
    time.sleep(30)
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
        if mode == modes["standby"]:
            emp_name = None
            emp_num = None
            idn = None
            count_dict = read_pckl_counts(count_pkl)
            total_count = count_dict['totalcount']
            run_count = count_dict['runcount']
            txt_file = read_main()
            filename = "/home/pi/Desktop/" + str(txt_file)
            seq = create_sequence(filename)
            part_num, mach_num, countset = read_machvars_db()
            param_test, prod_vars_dict = evaluate_params(part_num, mach_num, countset, prod_vars_dict)
            sequence_test = evaluate_seq(seq, relays)
            if param_test is True:
                if sequence_test is True:
                    save_vars(prod_vars_dict, prod_vars_pkl)
                    lcd.clear()
                    standby_info_top = f"Part:{part_num}"
                    standby_info_btm = f"Cnt:{total_count} Mch:{mach_num}"
                    lcd.message(standby_info_top, 1)
                    lcd.message(standby_info_btm, 2)
                    if startup is True:
                        today, file_path = update_csv()
                    while mode == modes["standby"]:
                        if date.today() != today:
                            today, file_path = update_csv()
                        if gr_button.is_pressed:
                            gr_button.wait_for_release()
                            txt_file = read_main()
                            filename = "/home/pi/Desktop/" + str(txt_file)
                            seq = create_sequence(filename)
                            part_num, mach_num, countset = read_machvars_db()
                            param_test, prod_vars_dict = evaluate_params(part_num, mach_num, countset, prod_vars_dict)
                            seq_test = evaluate_seq(seq, relays)
                            if param_test is True:
                                if seq_test is True:
                                    save_vars(prod_vars_dict, prod_vars_pkl)
                                    standby_info_top = f"Part:{part_num}"
                                    standby_info_btm = f"Cnt:{total_count} Mch:{mach_num}"
                                    lcd.clear()
                                    lcd.message(standby_info_top, 1)
                                    lcd.message(standby_info_btm, 2)
                                else:
                                    invalid_sequence()
                            else:
                                invalid_params()
                        if red_button.is_pressed:
                            red_button.wait_for_release()
                            time.sleep(0.2)
                            mode = modes["menu"]
                        if rfid_bypass.is_pressed:
                            emp_num = 999
                            emp_count = 0
                            add_timestamp(logon, file_path)
                            mode = modes["run"]
                        else:    
                            idn, emp_num = reader.read_no_block()
                            if emp_num != None:
                                emp_num = emp_num.strip()
                                if emp_num == '':
                                    pass
                                else:
                                    emp_name = ret_emp_name(emp_num)
                                    emp_count = 0
                                    add_timestamp(logon, file_path)
                                    mode = modes["run"]
                else:
                    invalid_sequence()
            else:
                invalid_params()
            startup = False
        elif mode == modes["menu"]:
            lcd.clear()
            time.sleep(.5)
            lcd.message(menu_msg_top, 1)
            lcd.message(menu_msg_btm,2)
            while mode == modes["menu"]:
                    if gr_button.is_pressed:
                        gr_button.wait_for_release()
                        count_dict["totalcount"] = 0
                        count_dict["runcount"] = 0
                        save_vars(count_dict, count_pkl)
                        change_msg(count_reset_msg, sec=3)
                        mode = modes["standby"]
                    if red_button.is_pressed:
                        red_button.wait_for_release()
                        mode = modes["standby"]
                        lcd.clear()
        elif mode == modes["run"]:
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
            while mode == modes["run"]:
                run_msg_btm = f"Cnt:{emp_count}, {total_count}"
                last_display, last_disp_time = display_run_info(last_display, last_disp_time)
                if countset == 0:
                    pass
                elif run_count == countset:
                    run_count = count_reset(run_count)
                    button2.wait_for_press()
                    button2.wait_for_release()
                    lcd.clear()
                    lcd.message(run_msg_top2, 1)
                if hand_button.is_pressed:
                    run_sequence()
                    emp_count += 1
                    total_count, run_count = update_counts(total_count, run_count)
                    save_vars(count_dict, count_pkl)
                    add_timestamp(shot, file_path)
                    now = datetime.now()
                    time.sleep(0.1)
                    hand_button.wait_for_release()
                if datetime.now() >= now + timedelta(seconds=300):
                    add_timestamp(timeout, file_path)
                    change_msg(timeoutm, sec=5)
                    mode = modes["standby"]
                if red_button.is_pressed:
                    red_button.wait_for_release()
                    logout_func(file_path)
                    mode = modes["standby"]
                if gr_button.is_pressed:
                    gr_button.wait_for_release()
                    mode = modes["maint"]
        elif mode == modes["maint"]:
            add_timestamp(mas, file_path)
            change_msg(maint_msg)
            while mode == modes["maint"]:
                if red_button.is_pressed:
                    red_button.wait_for_release()
                    add_timestamp(mae, file_path)
                    logout_func(file_path)
                    mode = modes["standby"]
                if gr_button.is_pressed:
                    gr_button.wait_for_release()
                    add_timestamp(mae, file_path)
                    change_msg(maint_end_msg, sec=1)
                    mode = modes["run"]
except KeyboardInterrupt:
    lcd.clear()
except Exception as e:
    lcd.clear()
    lcd.message("ERROR")
    print(e)
