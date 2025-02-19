import sqlite3
import csv
from datetime import datetime, timedelta
from sendEmail import send_email

# Get user inputs for adding a new medication
def get_medication():
    name = input("\nEnter product name: ")
    ndc = input("Enter product NDC: ")
    while True:
        med_type = input("Enter product type (OTC/Prescription): ")
        if med_type not in ['OTC', 'Prescription']:
            print("Invalid medication type. Please enter 'OTC' or 'Prescription'.")
        else:
            break
    
    while True:
        expiry_date = input("Enter expiry date (YYYY-MM-DD): ")
        if get_valid_date(expiry_date) == False:
            print("Invalid date format. Please enter the date in YYYY-MM-DD format.")
        else:
            break
    add_medications(name, ndc, med_type, expiry_date)
    print(f"Medication {name} with NDC, {ndc}, successfully added!")

# Helper function to check if date is in valid format
def get_valid_date(expiry_date):
    try: 
        date_obj = datetime.strptime(expiry_date, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Adds a new medication to the 'medications' table in the database.
def add_medications(name, ndc, med_type, expiry_date):
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()

    cursor.execute("INSERT INTO medications (name, ndc, med_type, expiry_date) VALUES (?, ?, ?, ?)", 
                (name, ndc, med_type, expiry_date))
    connection.commit()
    connection.close()

# Checks for medications nearing their expiration dates and sends notifications.
def check_expirations():
    print("\nChecking for expiration . . .")
    today = datetime.now().date()
    notifications = {'30_days': [], '60_days': [], '90_days': [], 'sale': []}
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()
    cursor.execute('SELECT name, ndc, med_type, expiry_date FROM medications')
    products = cursor.fetchall()

    for name, ndc, med_type, expiry_date in products:
        expiry_date_copy = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        days_left = (expiry_date_copy - today).days

        if days_left <= 30:
            notifications['30_days'].append((name, ndc, med_type, expiry_date))
            if med_type == 'Prescription':
                move_to_expiry_bin(name, ndc, med_type, expiry_date)
        elif days_left <= 60:
            notifications['60_days'].append((name, ndc, med_type, expiry_date))
        elif days_left <= 90 and med_type == 'OTC':
            notifications['sale'].append((name, ndc, med_type, expiry_date))
        elif days_left <= 90:
            notifications['90_days'].append((name, ndc, med_type, expiry_date))
            move_to_sales(name, ndc, med_type, expiry_date)
    
    email_body = "Products expiring soon:\n\n"
    for period, items in notifications.items():
        if items:
            email_body += f"\nProducts expiring within {period.replace('_', ' ')}:\n"
            for item in items:
                name, ndc, med_type, expiry_date = item
                email_body += (f"Name: {name}\n"
                               f"NDC: {ndc}\n"
                               f"Type: {med_type}\n"
                               f"Expiry Date: {expiry_date}\n"
                               f"Days Left: {(datetime.strptime(expiry_date, '%Y-%m-%d').date() - today).days} days\n\n")

    email_body += """Notes:\n\nPrescription products expiring within 30 days have been moved to the expiry bin. 
                    Please follow the pharmacy’s protocol for returning or disposing of expired medications.\n\n 
                    The listed sales products have been moved to the sales bin.
                    Please mark these products as discounted."""
    if not any(notifications.values()):
        email_body += "No medications are nearing expiration."
    send_email('MediMonitor Expiration Notifications', email_body)
    
    connection.commit()
    connection.close()

# Moves expired items into expired medication table
def move_to_expiry_bin(name, ndc, med_type, expiry_date):
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()

    print(f"Moving to expiry bin:")
    print(f"\nName: '{name}'")
    print(f"\nNDC: '{ndc}'")
    print(f"\nMedication Type: '{med_type}'")
    print(f"\nExpiry Date: '{expiry_date}'")
    
    cursor.execute("""
        INSERT INTO expired_medications (name, ndc, med_type, expiry_date)
        VALUES (?, ?, ?, ?)
        """, (name, ndc, med_type, expiry_date))
    cursor.execute("""
        DELETE FROM medications WHERE ndc = ?
        """, (ndc,))
    connection.commit()
    connection.close()

# Move OTC sale items into OTC sales table
def move_to_sales(name, ndc, med_type, expiry_date):
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()

    print(f"Moving to sales bin:")
    print(f"\nName: '{name}'")
    print(f"\nNDC: '{ndc}'")
    print(f"\nMedication Type: '{med_type}'")
    print(f"\nExpiry Date: '{expiry_date}'")

    cursor.execute("""
        INSERT INTO otc_sales (name, ndc, med_type, expiry_date)
        VALUES (?, ?, ?, ?)
    """, (name, ndc, med_type, expiry_date))
    cursor.execute("""
        DELETE FROM medications
        WHERE ndc = ?
    """, (ndc,))
    connection.commit()
    connection.close()

# Displays expired items in the expired medications table
def manage_expiry_bin():
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM expired_medications")
    expired_items = cursor.fetchall()
    print("\nExpiry Bin Contents:")
    for item in expired_items:
        print(item)
    connection.close()

# Displays sales items in OTC sales table
def manage_sale_bin():
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM otc_sales")
    sale_items = cursor.fetchall()
    print("\nSale Bin Contents:")
    for item in sale_items:
        print(item)
    connection.close()

# Displays OTC + Prescription products
def display_inventory():
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()
    cursor.execute("SELECT name, ndc, med_type, expiry_date FROM medications WHERE med_type = 'OTC'")
    otc_products = cursor.fetchall()
    print("\nGenerating a list of all OTC products: ")
    for product in otc_products:
        print(product)
    cursor.execute("SELECT name, ndc, med_type, expiry_date FROM medications WHERE med_type = 'Prescription'")
    pres_products = cursor.fetchall()
    print("\nGenerating a list of all Prescription products: ")
    for product in pres_products:
        print(product)
    connection.commit()

# Prompt user input for product NDC for deletion
def delete_medication():
    ndc = input("Enter the NDC of the product to delete: ")
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM medications WHERE ndc = ?", (ndc,))
    product = cursor.fetchone()

    if product is None:
        print("No product found with the given NDC.")
    else:
        cursor.execute("DELETE FROM medications WHERE ndc = ?", (ndc,))
        connection.commit()
        print(f"Product with NDC {ndc} has been deleted from the inventory.")

    connection.close()

# Imports medications from a CSV file
def import_medications_from_csv(file_path):
    connection = sqlite3.connect('pharmacy_inventory.db')
    cursor = connection.cursor()

    try:
        with open(file_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                name = row.get('name')
                ndc = row.get('ndc')
                med_type = row.get('med_type')
                expiry_date = row.get('expiry_date')

                # Validate CSV content
                if not name or not ndc or not med_type or not expiry_date:
                    print(f"Missing data in row: {row}. Skipping entry.")
                    continue
                
                if not get_valid_date(expiry_date):
                    print(f"Invalid date format for {name}. Skipping entry.")
                    continue

                # Check for existing medication
                cursor.execute("SELECT COUNT(*) FROM medications WHERE ndc = ?", (ndc,))
                if cursor.fetchone()[0] > 0:
                    print(f"Medication with NDC {ndc} already exists. Skipping entry.")
                    continue

                # Insert data into the database
                cursor.execute("""
                    INSERT INTO medications (name, ndc, med_type, expiry_date)
                    VALUES (?, ?, ?, ?)
                """, (name, ndc, med_type, expiry_date))

        connection.commit()
        print("Medications imported successfully!")
    except Exception as e:
        print(f"Error importing medications: {e}")
    finally:
        connection.close()
