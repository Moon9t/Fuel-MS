import sqlite3
import hashlib
from decimal import Decimal
import datetime
import PySimpleGUI as sg
import matplotlib.pyplot as plt
from io import BytesIO
import matplotlib.pyplot as plt
import csv
import keyboard
import requests
import schedule
import time
from threading import Thread
import json
import os
import datetime
from datetime import datetime

# Company name
COMPANY_NAME = "Jet Refuels"

# Database setup
DATABASE_NAME = "fuel_system.db"

CONFIG_FILE = 'fuel_prices.json'

def adapt_datetime(dt):
    return dt.isoformat()

sqlite3.register_adapter(datetime.datetime, adapt_datetime)

def setup_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees
                      (id INTEGER PRIMARY KEY, name TEXT, password TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS fuel_types
                      (id INTEGER PRIMARY KEY, name TEXT, price DECIMAL(10, 2), stock DECIMAL(10, 2))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions
                      (id INTEGER PRIMARY KEY, employee_id INTEGER, fuel_type_id INTEGER,
                       amount DECIMAL(10, 2), liters DECIMAL(10, 2), timestamp DATETIME)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins
                      (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    
    # Insert example employees
    cursor.execute("INSERT OR IGNORE INTO employees (id, name, password) VALUES (?, ?, ?)",
                   (123456, "Pluto", hashlib.sha256("pluto_pass".encode()).hexdigest()))
    cursor.execute("INSERT OR IGNORE INTO employees (id, name, password) VALUES (?, ?, ?)",
                   (789012, "Mickey", hashlib.sha256("mickey_pass".encode()).hexdigest()))
    cursor.execute("INSERT OR IGNORE INTO employees (id, name, password) VALUES (?, ?, ?)",
                   (345678, "Donald", hashlib.sha256("donald_pass".encode()).hexdigest()))

    # Insert initial fuel types
    cursor.execute("INSERT OR IGNORE INTO fuel_types (name, price, stock) VALUES (?, ?, ?)",
                   ("Regular", 16.67, 10000))
    cursor.execute("INSERT OR IGNORE INTO fuel_types (name, price, stock) VALUES (?, ?, ?)",
                   ("Premium", 18.99, 10000))
    cursor.execute("INSERT OR IGNORE INTO fuel_types (name, price, stock) VALUES (?, ?, ?)",
                   ("Diesel", 17.50, 10000))

    # Insert example admin
    cursor.execute("INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)",
                   ("admin", hashlib.sha256("admin_pass".encode()).hexdigest()))

    conn.commit()
    conn.close()

def authenticate_user(employee_id, password):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM employees WHERE id = ?", (employee_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result and result[0] == hashlib.sha256(password.encode()).hexdigest():
        return True
    return False

def authenticate_admin(username, password):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM admins WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result and result[0] == hashlib.sha256(password.encode()).hexdigest():
        return True
    return False

def load_fuel_prices():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    else:
        return {"Regular": 16.80, "Premium": 19.20, "Diesel": 17.75}

def save_fuel_prices(prices):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(prices, file, indent=4)

def  update_fuel_prices():
    prices = load_fuel_prices()
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    for fuel_type, price in prices.items():
        cursor.execute("UPDATE fuel_types SET price = ? WHERE name = ?", (price, fuel_type))
    
    conn.commit()
    conn.close()
    print("Fuel prices updated successfully.")

    # Call this function at program startup
    #update_fuel_prices()

def run_price_update_scheduler():
    schedule.every(1).hour.do(update_fuel_prices)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Start the automatic price update scheduler in a separate thread
price_update_thread = Thread(target=run_price_update_scheduler)
price_update_thread.daemon = True
price_update_thread.start()

            
def get_fuel_types():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, price FROM fuel_types")
    fuel_types = {row[0]: Decimal(str(row[1])) for row in cursor.fetchall()}
    
    conn.close()
    return fuel_types

def create_advanced_ui():
    sg.theme('DarkBlue13')
    
    fuel_types = get_fuel_types()
    
    layout = [
        [sg.Text(f'Welcome to {COMPANY_NAME}', font=('Helvetica', 24), pad=(0, 20))],
        [sg.Text('Employee ID:', size=(15, 1)), sg.Input(key='-ID-', size=(20, 1))],
        [sg.Text('Password:', size=(15, 1)), sg.Input(key='-PASSWORD-', password_char='*', size=(20, 1))],
        [sg.Text('Select Fuel Type:', font=('Helvetica', 14), pad=(0, 10))],
        *[[sg.Radio(f'{fuel} - R{price:.2f}/liter', group_id='FUEL', key=f'-{fuel.upper()}-', font=('Helvetica', 12))] for fuel, price in fuel_types.items()],
        [sg.Text('Amount (Rands):', size=(15, 1)), sg.Input(key='-AMOUNT-', size=(20, 1))],
        [sg.Button('Start Fueling', size=(15, 1), button_color=('white', '#007BFF'), border_width=0),
         sg.Button('Exit', size=(15, 1), button_color=('white', '#DC3545'), border_width=0)],
        [sg.Text('', key='-STATUS-', size=(50, 1), font=('Helvetica', 12), text_color='yellow')]
    ]
    
    return sg.Window(COMPANY_NAME, layout, finalize=True, element_justification='center', font=('Helvetica', 12), size=(600, 500), return_keyboard_events=True)

def view_reports():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT ft.name, SUM(t.amount) as total_sales, SUM(t.liters) as total_liters
        FROM transactions t
        JOIN fuel_types ft ON t.fuel_type_id = ft.id
        GROUP BY ft.name
    """)
    sales_data = cursor.fetchall()
    
    layout = [
        [sg.Text("Sales Report", font=('Helvetica', 20))],
        [sg.Table(values=sales_data, 
                  headings=['Fuel Type', 'Total Sales', 'Total Liters'], 
                  auto_size_columns=False, 
                  col_widths=[15, 15, 15],
                  justification='left',
                  key='-TABLE-')],
        [sg.Button("Generate Graph"), sg.Button("Close")]
    ]
    
    window = sg.Window("Sales Report", layout, size=(500, 400))
    
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Close'):
            break
        elif event == "Generate Graph":
            generate_sales_graph(sales_data)
    
    window.close()
    conn.close()

def generate_sales_graph(sales_data):
    fuel_types = [row[0] for row in sales_data]
    sales = [row[1] for row in sales_data]
    
    plt.figure(figsize=(10, 6))
    plt.bar(fuel_types, sales)
    plt.title('Sales by Fuel Type')
    plt.xlabel('Fuel Type')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    
    layout = [[sg.Image(data=buf.getvalue())]]
    window = sg.Window("Sales Graph", layout)
    window.read(close=True)

def create_admin_ui():
    sg.theme('DarkBlue13')
    
    layout = [        [sg.Text('Admin Panel', font=('Helvetica', 24), pad=(0, 20))],
        [sg.Button('Manage Employees', size=(20, 1), button_color=('white', '#007BFF'), border_width=0),
         sg.Button('Manage Fuel Types', size=(20, 1), button_color=('white', '#28A745'), border_width=0)],
        [sg.Button('View All Transactions', size=(20, 1), button_color=('white', '#FFC107'), border_width=0),
         sg.Button('Exit', size=(20, 1), button_color=('white', '#DC3545'), border_width=0)]
    ]
    
    return sg.Window('Admin Panel', layout, finalize=True, element_justification='center', font=('Helvetica', 12), size=(500, 300))

def process_transaction(employee_id, fuel_type, amount):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT price, stock FROM fuel_types WHERE name = ?", (fuel_type,))
    fuel_price, fuel_stock = cursor.fetchone()
    fuel_price = Decimal(str(fuel_price))
    fuel_stock = Decimal(str(fuel_stock))
    
    total_liters = Decimal(amount) / fuel_price
    
    if total_liters > fuel_stock:
        conn.close()
        return None, "Insufficient fuel stock"
    
    pumped_liters = 0
    layout = [[sg.Text('Press and hold Enter to pump fuel')],
              [sg.ProgressBar(100, orientation='h', size=(20, 20), key='progressbar')]]
    window = sg.Window('Fueling', layout, return_keyboard_events=True, finalize=True)
    
    total_liters = Decimal(amount) / fuel_price
    pumped_liters = Decimal('0')

    flow_rate = Decimal('0.5')  # liters per second
    time_increment = Decimal('0.1')  # 0.1 seconds per loop
    
    while pumped_liters < total_liters:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED:
            break
        if keyboard.is_pressed('enter'):
            pumped_liters += flow_rate * time_increment
            if pumped_liters > total_liters:
                pumped_liters = total_liters
            progress = int((pumped_liters / total_liters) * 100)
            window['progressbar'].update(progress)
        if pumped_liters >= total_liters:
            break
        
    window.close()
    
    cursor.execute("UPDATE fuel_types SET stock = stock - ? WHERE name = ?", (float(pumped_liters), fuel_type))
    
    cursor.execute('''INSERT INTO transactions (employee_id, fuel_type_id, amount, liters, timestamp)
                      VALUES (?, (SELECT id FROM fuel_types WHERE name = ?), ?, ?, ?)''',
                   (employee_id, fuel_type, float(pumped_liters * fuel_price), float(pumped_liters), datetime.datetime.now()))
    
    conn.commit()
    conn.close()
    
    return generate_invoice(employee_id, fuel_type, pumped_liters * fuel_price, pumped_liters), None

def generate_invoice(employee_id, fuel_type, amount, liters):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM employees WHERE id = ?", (employee_id,))
    employee_name = cursor.fetchone()[0]
    
    conn.close()
    
    now = datetime.datetime.now()
    invoice = f"""
    {COMPANY_NAME}
    -------------------------
    Date: {now.strftime("%Y-%m-%d %H:%M:%S")}
    Employee: {employee_name}
    
    Fuel type: {fuel_type}
    Amount paid: R{amount:.2f}
    Liters dispensed: {liters:.2f}
    
    Thank you for choosing {COMPANY_NAME}!
    """
    return invoice

def generate_reports():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(amount) FROM transactions")
    total_sales = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT ft.name, SUM(t.amount)
        FROM transactions t
        JOIN fuel_types ft ON t.fuel_type_id = ft.id
        GROUP BY ft.name
    """)
    sales_by_fuel = cursor.fetchall()
    
    labels = [row[0] for row in sales_by_fuel]
    sizes = [float(row[1]) for row in sales_by_fuel]
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    plt.title("Sales by Fuel Type")
    
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    
    conn.close()
    
    return f"Total Sales: R{total_sales:.2f}", buf.getvalue()

def manage_employees():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    def refresh_employee_list():
        cursor.execute("SELECT id, name FROM employees")
        return cursor.fetchall()

    employees = refresh_employee_list()
    
    layout = [
        [sg.Text("Manage Employees", font=('Helvetica', 20))],
        [sg.Table(values=employees, headings=['ID', 'Name'], auto_size_columns=False, col_widths=[10, 20], justification='left', key='-TABLE-')],
        [sg.Input(key='-EMP_ID-', size=(10, 1), default_text='ID'),
         sg.Input(key='-EMP_NAME-', size=(20, 1), default_text='Name'),
         sg.Input(key='-EMP_PASS-', size=(20, 1), default_text='Password')],
        [sg.Button("Add Employee"), sg.Button("Remove Employee"), sg.Button("Back")]
    ]
    window = sg.Window("Manage Employees", layout)
    
    while True:
          event, values = window.read()
          if event == sg.WINDOW_CLOSED or event == 'Back':
              break
          elif event == "Add Employee":
              if values['-EMP_ID-'] and values['-EMP_NAME-'] and values['-EMP_PASS-']:
                  cursor.execute("INSERT OR IGNORE INTO employees (id, name, password) VALUES (?, ?, ?)",
                               (values['-EMP_ID-'], values['-EMP_NAME-'], hashlib.sha256(values['-EMP_PASS-'].encode()).hexdigest()))
                  conn.commit()
                  employees = refresh_employee_list()
                  window['-TABLE-'].update(values=employees)
          elif event == "Remove Employee":
              if values['-TABLE-']:
                  selected_employee = employees[values['-TABLE-'][0]]
                  cursor.execute("DELETE FROM employees WHERE id = ?", (selected_employee[0],))
                  conn.commit()
                  employees = refresh_employee_list()
                  window['-TABLE-'].update(values=employees)
    
    window.close()
    conn.close()

def manage_fuel_types():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    def refresh_fuel_types():
        cursor.execute("SELECT name, price, stock FROM fuel_types")
        return cursor.fetchall()

    fuel_types = refresh_fuel_types()
    
    layout = [
        [sg.Text("Manage Fuel Types", font=('Helvetica', 20))],
        [sg.Table(values=fuel_types, headings=['Name', 'Price', 'Stock'], auto_size_columns=False, col_widths=[15, 10, 10], justification='left', key='-TABLE-')],
        [sg.Input(key='-FUEL_NAME-', size=(15, 1), default_text='Fuel Name'),
         sg.Input(key='-FUEL_PRICE-', size=(10, 1), default_text='Price'),
         sg.Input(key='-FUEL_STOCK-', size=(10, 1), default_text='Stock')],
        [sg.Button("Add Fuel Type"), sg.Button("Update Price"), sg.Button("Update Stock"), sg.Button("Remove Fuel Type"), sg.Button("Back")]
    ]
    
    window = sg.Window("Manage Fuel Types", layout)
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Back':
            break
        elif event == "Add Fuel Type":
            if values['-FUEL_NAME-'] and values['-FUEL_PRICE-'] and values['-FUEL_STOCK-']:
                cursor.execute("INSERT OR IGNORE INTO fuel_types (name, price, stock) VALUES (?, ?, ?)",
                               (values['-FUEL_NAME-'], float(values['-FUEL_PRICE-']), float(values['-FUEL_STOCK-'])))
                conn.commit()
                fuel_types = refresh_fuel_types()
                window['-TABLE-'].update(values=fuel_types)
        elif event == "Update Price":
            if values['-TABLE-'] and values['-FUEL_PRICE-']:
                selected_fuel = fuel_types[values['-TABLE-'][0]]
                cursor.execute("UPDATE fuel_types SET price = ? WHERE name = ?",
                               (float(values['-FUEL_PRICE-']), selected_fuel[0]))
                conn.commit()
                fuel_types = refresh_fuel_types()
                window['-TABLE-'].update(values=fuel_types)
        elif event == "Update Stock":
            if values['-TABLE-'] and values['-FUEL_STOCK-']:
                selected_fuel = fuel_types[values['-TABLE-'][0]]
                cursor.execute("UPDATE fuel_types SET stock = ? WHERE name = ?",
                               (float(values['-FUEL_STOCK-']), selected_fuel[0]))
                conn.commit()
                fuel_types = refresh_fuel_types()
                window['-TABLE-'].update(values=fuel_types)
        elif event == "Remove Fuel Type":
            if values['-TABLE-']:
                selected_fuel = fuel_types[values['-TABLE-'][0]]
                cursor.execute("DELETE FROM fuel_types WHERE name = ?", (selected_fuel[0],))
                conn.commit()
                fuel_types = refresh_fuel_types()
                window['-TABLE-'].update(values=fuel_types)
    
    window.close()
    conn.close()

def view_all_transactions():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.id, e.name, ft.name, t.amount, t.liters, t.timestamp
        FROM transactions t
        JOIN employees e ON t.employee_id = e.id
        JOIN fuel_types ft ON t.fuel_type_id = ft.id
        ORDER BY t.timestamp DESC
    """)
    transactions = cursor.fetchall()
    
    layout = [
        [sg.Text("All Transactions", font=('Helvetica', 20))],
        [sg.Table(values=transactions, headings=['ID', 'Employee', 'Fuel Type', 'Amount', 'Liters', 'Timestamp'], 
                  auto_size_columns=False, col_widths=[5, 15, 10, 10, 10, 20], justification='left', key='-TABLE-')],
        [sg.Button("Back")]
    ]
    
    window = sg.Window("All Transactions", layout, size=(800, 600))
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Back':
            break
    
    window.close()
    conn.close()

def worker_tracking():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.id, e.name, 
               COUNT(t.id) as transaction_count, 
               SUM(t.amount) as total_sales,
               AVG(t.amount) as avg_sale,
               MAX(t.timestamp) as last_transaction
        FROM employees e
        LEFT JOIN transactions t ON e.id = t.employee_id
        GROUP BY e.id
        ORDER BY total_sales DESC
    """)
    worker_stats = cursor.fetchall()
    
    layout = [
        [sg.Text("Worker Performance Tracking", font=('Helvetica', 20))],
        [sg.Table(values=worker_stats, 
                  headings=['ID', 'Employee', 'Transactions', 'Total Sales', 'Avg Sale', 'Last Transaction'], 
                  auto_size_columns=False, 
                  col_widths=[5, 20, 15, 15, 15, 20],
                  justification='left',
                  key='-TABLE-',
                  enable_events=True)],
        [sg.Button("View Performance Graph"), sg.Button("Export to CSV"), sg.Button("Back")]
    ]
    
    window = sg.Window("Worker Tracking", layout, size=(800, 600))
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Back':
            break
        elif event == "View Performance Graph":
            plot_worker_performance(worker_stats)
        elif event == "Export to CSV":
            export_to_csv(worker_stats)
    
    window.close()
    conn.close()

def plot_worker_performance(worker_stats):
    names = [stat[1] for stat in worker_stats]
    sales = [stat[3] if stat[3] is not None else 0 for stat in worker_stats]
    
    plt.figure(figsize=(10, 6))
    plt.bar(names, sales)
    plt.title('Worker Sales Performance')
    plt.xlabel('Employees')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    
    layout = [[sg.Image(data=buf.getvalue())]]
    window = sg.Window("Performance Graph", layout)
    window.read(close=True)
def export_to_csv(data):
    filename = f"worker_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Employee', 'Transactions', 'Total Sales', 'Avg Sale', 'Last Transaction'])
        writer.writerows(data)
    sg.popup(f"Data exported to {filename}")
  
def admin_main():
      window = create_admin_ui()
    
      while True:
          event, _ = window.read()
          if event == sg.WINDOW_CLOSED or event == 'Exit':
             break
          elif event == 'Manage Employees':
              manage_employees()
          elif event == 'Manage Fuel Types':
              manage_fuel_types()
          elif event == 'View All Transactions':
              view_all_transactions()
          elif event == 'Worker Tracking':
              worker_tracking()
    
      window.close()
      main()

def admin_update_prices():
    prices = load_fuel_prices()
    layout = [
        [sg.Text(f"{fuel}: ", size=(10, 1)), sg.Input(price, key=f'-{fuel.upper()}-')] for fuel, price in prices.items()
    ]
    layout.append([sg.Button('Update'), sg.Button('Cancel')])
    
    window = sg.Window('Update Fuel Prices', layout)
    
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Cancel'):
            break
        if event == 'Update':
            new_prices = {fuel: float(values[f'-{fuel.upper()}-']) for fuel in prices}
            save_fuel_prices(new_prices)
            update_fuel_prices()
            sg.popup('Prices updated successfully')
            break
    
    window.close()
    
def worker_tracking():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.id, e.name, 
               COUNT(t.id) as transaction_count, 
               SUM(t.amount) as total_sales,
               AVG(t.amount) as avg_sale,
               MAX(t.timestamp) as last_transaction
        FROM employees e
        LEFT JOIN transactions t ON e.id = t.employee_id
        GROUP BY e.id
        ORDER BY total_sales DESC
    """)
    worker_stats = cursor.fetchall()
    
    layout = [
        [sg.Text("Worker Performance Tracking", font=('Helvetica', 20))],
        [sg.Table(values=worker_stats, 
                  headings=['ID', 'Employee', 'Transactions', 'Total Sales', 'Avg Sale', 'Last Transaction'], 
                  auto_size_columns=False, 
                  col_widths=[5, 20, 15, 15, 15, 20],
                  justification='left',
                  key='-TABLE-',
                  enable_events=True)],
        [sg.Button("View Performance Graph"), sg.Button("Export to CSV"), sg.Button("Back")]
    ]
    
    window = sg.Window("Worker Tracking", layout, size=(800, 600))
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Back':
            break
        elif event == "View Performance Graph":
            plot_worker_performance(worker_stats)
        elif event == "Export to CSV":
            export_to_csv(worker_stats)
    
    window.close()
    conn.close()
  
def create_admin_ui():  
      sg.theme('DarkBlue13')
    
      layout = [
          [sg.Text('Admin Panel', font=('Helvetica', 24), pad=(0, 20))],
          [sg.Button('Manage Employees', size=(20, 1), button_color=('white', '#007BFF'), border_width=0),
         sg.Button('Manage Fuel Types', size=(20, 1), button_color=('white', '#28A745'), border_width=0)],
          [sg.Button('View All Transactions', size=(20, 1), button_color=('white', '#FFC107'), border_width=0),
         sg.Button('Worker Tracking', size=(20, 1), button_color=('white', '#17A2B8'), border_width=0)],
         [sg.Button('Update Prices', size=(20, 1), button_color=('white', '#DC3545'), border_width=0),
         sg.Button('View Reports', size=(20, 1), button_color=('white', '#6C757D'), border_width=0)],
          [sg.Button('Exit', size=(20, 1), button_color=('white', '#DC3545'), border_width=0)]
      ]
    
      return sg.Window('Admin Panel', layout, finalize=True, element_justification='center', font=('Helvetica', 12), size=(500, 300))

def main():
    setup_database()
    
    layout = [
        [sg.Text('Select Login Type:', font=('Helvetica', 18), pad=(0, 20))],
        [sg.Button('Employee Login', size=(15, 1), button_color=('white', '#007BFF'), border_width=0),
         sg.Button('Admin Login', size=(15, 1), button_color=('white', '#28A745'), border_width=0)],
        [sg.Button('Exit', size=(15, 1), button_color=('white', '#DC3545'), border_width=0)]
    ]
    
    window = sg.Window('Login Selection', layout, finalize=True, element_justification='center', font=('Helvetica', 12), size=(400, 250))
    
    while True:
        event, _ = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break
        elif event == 'Employee Login':
            window.close()
            employee_main()
        elif event == 'Admin Login':
            window.close()
            admin_login()
    
    window.close()

def employee_main():
    window = create_advanced_ui()
    fueling_in_progress = False
    fuel_amount = 0
    selected_fuel = None
    
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break
        elif event == 'View Reports':
            view_reports()
        elif event == 'Update Prices':
            update_fuel_prices()
        elif event == 'Start Fueling':
            if update_fuel_prices():
                sg.popup("Fuel prices updated successfully!")
            else:
                sg.popup_error("Failed to update fuel prices.")
            if authenticate_user(values['-ID-'], values['-PASSWORD-']):
                selected_fuel = next((fuel for fuel in ['REGULAR', 'PREMIUM', 'DIESEL'] if values[f'-{fuel}-']), None)
                if selected_fuel and values['-AMOUNT-']:
                    try:
                        fuel_amount = float(values['-AMOUNT-'])
                        window['-STATUS-'].update("Authentication successful. Press Enter to start fueling.")
                        fueling_in_progress = True
                    except ValueError:
                        sg.popup_error("Invalid amount entered.")
            else:
                sg.popup_error("Authentication failed.")
        elif event == '\r' and fueling_in_progress:  # '\r' is the Enter key
            result, error = process_transaction(values['-ID-'], selected_fuel.capitalize(), fuel_amount)
            if error:
                sg.popup_error(error)
            else:
                sg.popup(result)
            fueling_in_progress = False
            window['-STATUS-'].update("Fueling complete. Ready for next transaction.")
        
        if fueling_in_progress:
            window['-STATUS-'].update("Ready to fuel. Press Enter to start pumping.")
    
    window.close()

def admin_login():
    layout = [
        [sg.Text('Admin Login', font=('Helvetica', 18), pad=(0, 20))],
        [sg.Text('Username:', size=(10, 1)), sg.Input(key='-USERNAME-', size=(20, 1))],
        [sg.Text('Password:', size=(10, 1)), sg.Input(key='-PASSWORD-', password_char='*', size=(20, 1))],
        [sg.Button('Login', size=(10, 1), button_color=('white', '#007BFF'), border_width=0),
         sg.Button('Exit', size=(10, 1), button_color=('white', '#DC3545'), border_width=0)],
        [sg.Text('Example credentials: admin / admin_pass', font=('Helvetica', 10), pad=(0, 10))]
    ]
    
    window = sg.Window('Admin Login', layout, finalize=True, element_justification='center', font=('Helvetica', 12), size=(400, 300))
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            window.close()
            main()
            return
        elif event == 'Login':
            if authenticate_admin(values['-USERNAME-'], values['-PASSWORD-']):
                window.close()
                admin_main()
                return
            else:
                sg.popup('Authentication Failed', font=('Helvetica', 12))
    
    window.close()

def admin_main():
    window = create_admin_ui()
    
    while True:
        event, _ = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break
        elif event == 'Manage Employees':
            manage_employees()
        elif event == 'Manage Fuel Types':
            manage_fuel_types()
        elif event == 'View All Transactions':
            view_all_transactions()
        elif event == 'Worker Tracking':
            worker_tracking()
        elif event == 'Update Prices':
            admin_update_prices()
        elif event == 'View Reports':
            view_reports()
    
    window.close()
    main()

if __name__ == "__main__":
    main()
            
