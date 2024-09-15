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
    
    fuel_types = get_fuel_types()
    
    layout = [
        [sg.Text(f'Welcome to {COMPANY_NAME}', font=('Helvetica', 20))],
        [sg.Text('Employee ID:'), sg.Input(key='-ID-')],
        [sg.Text('Password:'), sg.Input(key='-PASSWORD-', password_char='*')],
        [sg.Text('Select Fuel Type:')],
        [sg.Radio(f'{fuel} - R{price:.2f}/liter', group_id='FUEL', key=f'-{fuel.upper()}-') for fuel, price in fuel_types.items()],
        [sg.Text('Amount (Rands):'), sg.Input(key='-AMOUNT-')],
        [sg.Button('Start Fueling'), sg.Button('View Reports'), sg.Button('Update Prices'), sg.Button('Exit')]
    ]
    
    return sg.Window(COMPANY_NAME, layout, finalize=True)

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

def main():
    setup_database()
    window = create_advanced_ui()
    
    while True:
        event, values = window.read()
        if event == sg.WINDOW_CLOSED or event == 'Exit':
            break
        elif event == 'Start Fueling':
            employee_id = int(values['-ID-'])
            password = values['-PASSWORD-']
            
            if authenticate_user(employee_id, password):
                fuel_type = next(fuel for fuel in get_fuel_types() if values[f'-{fuel.upper()}-'])
                amount = Decimal(values['-AMOUNT-'])
                
                window.hide()
                invoice, error = process_transaction(employee_id, fuel_type, amount)
                if error:
                    sg.popup_error(error)
                else:
                    sg.popup_scrolled(invoice, title='Transaction Complete')
                window.un_hide()
            else:
                sg.popup('Authentication Failed')
        elif event == 'View Reports':
            total_sales, chart_image = generate_reports()
            sg.popup_scrolled(total_sales, image=chart_image.getvalue(), title='Sales Report')
        elif event == 'Update Prices':
            if update_fuel_prices():
                window.close()
                window = create_advanced_ui()
                sg.popup('Fuel prices updated successfully')
            else:
                sg.popup_error('Failed to update fuel prices')
    
    window.close()

if __name__ == "__main__":
    main()
