import time
import sqlite3
import hashlib
import requests
from decimal import Decimal
import datetime
from tqdm import tqdm
import PySimpleGUI as sg
import threading
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

# Company name
COMPANY_NAME = "Jet Refuels"

# Database setup
DATABASE_NAME = "fuel_system.db"

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

def update_fuel_prices():
    try:
        prices = {"Regular": 16.80, "Premium": 19.20, "Diesel": 17.75}
        
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        for fuel_type, price in prices.items():
            cursor.execute("UPDATE fuel_types SET price = ? WHERE name = ?", (price, fuel_type))
        
        conn.commit()
        conn.close()
        return True
    except:
        print("Failed to update fuel prices. Using existing prices.")
        return False

def get_fuel_types():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, price FROM fuel_types")
    fuel_types = {row[0]: Decimal(str(row[1])) for row in cursor.fetchall()}
    
    conn.close()
    return fuel_types

def create_advanced_ui():
    sg.theme('DarkBlue13')
    
    # Load and resize the logo
    logo_path = "jet.png"
    logo = Image.open(logo_path)
    logo = logo.resize((150, 150))  # Adjust size as needed
    
    fuel_types = get_fuel_types()
    
    layout = [
        [sg.Image(data=logo.tobytes(), size=logo.size)],
        [sg.Text(f'Welcome to {COMPANY_NAME}', font=('Helvetica', 24), pad=(0, 20))],
        [sg.Text(f'Welcome to {COMPANY_NAME}', font=('Helvetica', 24), pad=(0, 20))],
        [sg.Text('Employee ID:', size=(15, 1)), sg.Input(key='-ID-', size=(20, 1))],
        [sg.Text('Password:', size=(15, 1)), sg.Input(key='-PASSWORD-', password_char='*', size=(20, 1))],
        [sg.Text('Select Fuel Type:', font=('Helvetica', 14), pad=(0, 10))],
        *[[sg.Radio(f'{fuel} - R{price:.2f}/liter', group_id='FUEL', key=f'-{fuel.upper()}-', font=('Helvetica', 12))] for fuel, price in fuel_types.items()],
        [sg.Text('Amount (Rands):', size=(15, 1)), sg.Input(key='-AMOUNT-', size=(20, 1))],
        [sg.Button('Start Fueling', size=(15, 1), button_color=('white', '#007BFF'), border_width=0),
         sg.Button('View Reports', size=(15, 1), button_color=('white', '#28A745'), border_width=0),
         sg.Button('Update Prices', size=(15, 1), button_color=('white', '#FFC107'), border_width=0),
         sg.Button('Exit', size=(15, 1), button_color=('white', '#DC3545'), border_width=0)]
    ]
    
    return sg.Window(COMPANY_NAME, layout, finalize=True, element_justification='center', font=('Helvetica', 12), size=(600, 500))

def create_admin_ui():
    sg.theme('DarkBlue13')
    
    layout = [
        [sg.Text('Admin Panel', font=('Helvetica', 24), pad=(0, 20))],
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
    
    for _ in tqdm(range(int(total_liters * 2)), desc="Fueling Progress"):
        time.sleep(0.1)
    
    cursor.execute("UPDATE fuel_types SET stock = stock - ? WHERE name = ?", (float(total_liters), fuel_type))
    
    cursor.execute('''INSERT INTO transactions (employee_id, fuel_type_id, amount, liters, timestamp)
                      VALUES (?, (SELECT id FROM fuel_types WHERE name = ?), ?, ?, ?)''',
                   (employee_id, fuel_type, float(amount), float(total_liters), datetime.datetime.now()))
    
    conn.commit()
    conn.close()
    
    return generate_invoice(employee_id, fuel_type, amount, total_liters), None

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
    
    return f"Total Sales: R{total_sales:.2f}", buf

def manage_employees():
    # Implement employee management logic here
    sg.popup("Employee management functionality not implemented yet.")

def manage_fuel_types():
    # Implement fuel type management logic here
    sg.popup("Fuel type management functionality not implemented yet.")

def view_all_transactions():
    # Implement transaction viewing logic here
    sg.popup("Transaction viewing functionality not implemented yet.")

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
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break
        elif event == 'Start Fueling':
            employee_id = values['-ID-']
            password = values['-PASSWORD-']
            amount = values['-AMOUNT-']
            
            if not employee_id or not password or not amount:
                sg.popup('Please fill in all fields', font=('Helvetica', 12))
                continue
            
            try:
                employee_id = int(employee_id)
                amount = Decimal(amount)
            except ValueError:
                sg.popup('Employee ID and Amount must be numeric', font=('Helvetica', 12))
                continue
            
            if authenticate_user(employee_id, password):
                fuel_type = next(fuel for fuel in get_fuel_types() if values[f'-{fuel.upper()}-'])
                
                window.hide()
                invoice, error = process_transaction(employee_id, fuel_type, amount)
                if error:
                    sg.popup_error(error, font=('Helvetica', 12))
                else:
                    sg.popup_scrolled(invoice, title='Transaction Complete', font=('Helvetica', 12))
                window.un_hide()
            else:
                sg.popup('Authentication Failed', font=('Helvetica', 12))
        elif event == 'View Reports':
            total_sales, chart_image = generate_reports()
            sg.popup_scrolled(total_sales, image=chart_image.getvalue(), title='Sales Report', font=('Helvetica', 12))
        elif event == 'Update Prices':
            if update_fuel_prices():
                window.close()
                window = create_advanced_ui()
                sg.popup('Fuel prices updated successfully', font=('Helvetica', 12))
            else:
                sg.popup_error('Failed to update fuel prices', font=('Helvetica', 12))
    
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
    
    window.close()
    main()

if __name__ == "__main__":
    main()
            