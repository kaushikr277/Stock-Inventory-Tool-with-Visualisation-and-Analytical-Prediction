import os
import pandas as pd
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
import re

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Inventory.db')
#Sample_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Inventory List as at 2022.xlsx')

def clean_and_insert_data(file_path):
    #sample_data = pd.read_csv(Sample_data,encoding='ISO-8859-1')
    sample_data = pd.read_excel(file_path, sheet_name=0, header=1)
    # Ensure all column names are treated as strings
    sample_data.columns = sample_data.columns.astype(str)
    sample_data_cleaned = sample_data.loc[:, ~sample_data.columns.str.contains('^Unnamed')]

    
    # Rename the columns (this should match what you have done in the backup process)
    sample_data_cleaned.rename(columns={
        'InventoryID': 'Inventory ID',
        'Reorder?': 'Reorder ?'
        # Add other renames here as necessary
    }, inplace=True)
    
    
    # Check if 'Inventory ID' exists before dropping NaNs
    if 'Inventory ID' in sample_data_cleaned.columns:
        # Drop rows with missing 'Inventory ID'
        sample_data_cleaned = sample_data_cleaned.dropna(subset=['Inventory ID'])
    else:
        print("Error: 'Inventory ID' column not found after renaming.")
        return  # Exit the function or handle the error as needed
    

    # Remove leading and trailing spaces from column names
    sample_data_cleaned.columns = sample_data_cleaned.columns.str.strip()
    sample_data_cleaned = sample_data_cleaned.dropna(subset=['Inventory ID'])

    # Replace missing values
    sample_data_cleaned = sample_data_cleaned.copy()  # Ensure we're working with a copy
    sample_data_cleaned.fillna('', inplace=True)

    # Replace empty spaces in 'Discontinued' and 'Reorder?' with 'no'
    sample_data_cleaned['Discontinued?'] = sample_data_cleaned['Discontinued?'].replace('', 'No')
    sample_data_cleaned['Reorder ?'] = sample_data_cleaned['Reorder ?'].replace('', 'No')


    sample_data_cleaned['Unit Price'] = sample_data_cleaned['Unit Price'].astype(str)


    # Hardcoded exchange rates (as of a specific date)
    exchange_rates = {
        'USD': 0.75,  # Example rate: 1 USD = 0.75 GBP
        'EUR': 1.20,  # Example rate: 1 EUR = 0.85 GBP
    }

    def convert_to_gbp(price):
        currency_symbols = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
        }

        # Handle empty strings or non-string values
        if not isinstance(price, str) or price.strip() == '':
            return 0.0  # Or any other default value you prefer

        for symbol, code in currency_symbols.items():
            if symbol in price:
                # Extract numeric value, handling potential errors
                try:
                    price_value = float(re.sub(r'[^\d.]', '', price))
                except ValueError:
                    return 0.0  # Or handle the error differently

                if code != 'GBP':
                    rate = exchange_rates[code]
                    return price_value * rate
                else:
                    return price_value

        # Default to GBP if no symbol is found, but handle potential errors
        try:
            return float(re.sub(r'[^\d.]', '', price))
        except ValueError:
            return 0.0  # Or handle the error as needed

    # Convert the Unit Price column
    sample_data_cleaned['Unit Price'] = sample_data_cleaned['Unit Price'].apply(convert_to_gbp)


    # Correct data types where necessary
    # Ensure the column is of string type before applying string operations
    sample_data_cleaned['Qty'] = sample_data_cleaned['Qty'].astype(str)
    sample_data_cleaned['Qty'] = pd.to_numeric(sample_data_cleaned['Qty'].str.replace(',', ''), errors='coerce').fillna(0).astype(int)

    sample_data_cleaned['Unit Price'] = sample_data_cleaned['Unit Price'].astype(str)
    sample_data_cleaned['Unit Price'] = pd.to_numeric(sample_data_cleaned['Unit Price'].str.replace(',', ''), errors='coerce').fillna(0).astype(float)

    sample_data_cleaned['Inventory Value'] = sample_data_cleaned['Inventory Value'].astype(str)
    sample_data_cleaned['Inventory Value'] = pd.to_numeric(sample_data_cleaned['Inventory Value'].str.replace(',', ''), errors='coerce').fillna(0).astype(float)

    sample_data_cleaned['Reorder Level'] = sample_data_cleaned['Reorder Level'].astype(str)
    sample_data_cleaned['Reorder Level'] = pd.to_numeric(sample_data_cleaned['Reorder Level'].str.replace(',', ''), errors='coerce').fillna(1).astype(float)

    # Calculate Inventory Value as Qty * Unit Price
    #sample_data_cleaned['Inventory Value'] = round(sample_data_cleaned['Qty'] * sample_data_cleaned['Unit Price'],2)

    # Extract unique categories
    category_df = sample_data_cleaned[['Category']].drop_duplicates(subset=['Category']).copy()
    # Remove rows where Category is empty
    category_df = category_df[(category_df['Category'] != '')]
    # Generate Unique ID's for Category Name
    category_df['CategoryID'] = range(1, len(category_df) + 1)

    # Check if any existing CategoryID column is present in sample_cleaned_data and drop it. 
    if 'CategoryID' in sample_data_cleaned.columns:
        sample_data_cleaned = sample_data_cleaned.drop('CategoryID', axis=1)
    # Merging the CategoryId to the Sample_data_cleaned dataframe
    sample_data_cleaned = sample_data_cleaned.merge(category_df[['CategoryID','Category']], on='Category', how='left')


    # Extract unique suppliers
    supplier_df = sample_data_cleaned[['Supplier Name']].drop_duplicates(subset=['Supplier Name']).copy()
    # Remove rows where Supplier Name is empty
    supplier_df = supplier_df[(supplier_df['Supplier Name'] != '')]
    # Generate Unique ID's for Supplier Name
    supplier_df['SupplierID'] = range(1, len(supplier_df) + 1)

    # Check if any existing SupplierID column is present in sample_cleaned_data and drop it. 
    if 'SupplierID' in sample_data_cleaned.columns:
        sample_data_cleaned = sample_data_cleaned.drop('SupplierID', axis=1)
    # Merging the SupplierId to the Sample_data_cleaned dataframe
    sample_data_cleaned = sample_data_cleaned.merge(supplier_df[['SupplierID','Supplier Name']], on='Supplier Name', how='left')


    # Create an orders DataFrame with unique Order Code
    orders_df = sample_data_cleaned[['Order Code']].drop_duplicates(subset=['Order Code']).copy()
    # Remove rows where Order Code is empty
    orders_df = orders_df[(orders_df['Order Code'] != '')]
    # Generate unique OrderID's for Order Code
    orders_df['OrderID'] = range(1, len(orders_df) + 1)

    # Drop the existing 'OrderID' column if it exists
    if 'OrderID' in sample_data_cleaned.columns:
        sample_data_cleaned = sample_data_cleaned.drop('OrderID', axis=1)
    # Merging the OrderId to the Sample_data_cleaned dataframe
    sample_data_cleaned = sample_data_cleaned.merge(orders_df[['Order Code', 'OrderID']], on='Order Code', how='left')

    # Create an Purchase DataFrame with unique Purchase Order No
    purchase_df = sample_data_cleaned[['Purchase Order No']].drop_duplicates(subset=['Purchase Order No']).copy()
    # Remove rows where  Purchase Order No  is empty
    purchase_df = purchase_df[(purchase_df['Purchase Order No'] != '')]
    # Generate unique PurchaseID's for Purchase Order No
    purchase_df['PurchaseID'] = range(1, len(purchase_df) + 1)

    # Drop the existing 'PurchaseID' column if it exists
    if 'PurchaseID' in sample_data_cleaned.columns:
        sample_data_cleaned = sample_data_cleaned.drop('PurchaseID', axis=1)
    # Merging the PurchaseId to the Sample_data_cleaned dataframe
    sample_data_cleaned = sample_data_cleaned.merge(purchase_df[['Purchase Order No', 'PurchaseID']], on='Purchase Order No', how='left')

    # Create an Unique description with Description
    unique_description = sample_data_cleaned[['Description']].drop_duplicates(subset=['Description']).copy()
    # Remove rows where Description is empty
    unique_description =  unique_description[unique_description['Description'] != '']
    # Generate unique DescriptionID's
    unique_description['DescriptionID'] = range(1, len(unique_description) + 1)

    # Drop the existing 'DescriptionID' column if it exists
    if 'DescriptionID' in sample_data_cleaned.columns:
        sample_data_cleaned = sample_data_cleaned.drop('DescriptionID', axis=1)
    # Merging the 'DescriptionID' to the Sample_data_cleaned dataframe
    sample_data_cleaned = sample_data_cleaned.merge(unique_description[['DescriptionID','Description']], on='Description', how='left')

    # Create an Unique manufacturers with Manufacturer Number
    unique_manufactures = sample_data_cleaned[['Manufacturer Number', 'SupplierID', 'DescriptionID']].drop_duplicates(subset=['Manufacturer Number']).copy()
    # Remove rows where Manufacture Number is empty
    unique_manufactures = unique_manufactures[unique_manufactures['Manufacturer Number'] != '']
    # Generate unique ManufactureID's
    unique_manufactures['ManufactureID'] = range(1, len(unique_manufactures) + 1)

    # Drop the existing 'ManufacturerID' column if it exists
    if 'ManufactureID' in sample_data_cleaned.columns:
        sample_data_cleaned = sample_data_cleaned.drop('ManufactureID', axis=1)
    # Merging the 'ManufacturerID' to the Sample_data_cleaned dataframe
    sample_data_cleaned = sample_data_cleaned.merge(unique_manufactures[['ManufactureID','Manufacturer Number']], on='Manufacturer Number', how='left')

    

    # Generate unique StockIDs using range (ensuring they are strings for TEXT type)
    sample_data_cleaned['StockID'] = sample_data_cleaned.index + 1
    sample_data_cleaned['StockID'] = sample_data_cleaned['StockID'].astype(str)


    def get_db_connection():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

    def drop_tables():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DROP TABLE IF EXISTS Category;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS Supplier;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS Orders;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS Purchase;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS Manufacturer;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS Description;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS Inventory;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS UserTable;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS logs;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS projects;
        ''')
        cursor.execute('''
            DROP TABLE IF EXISTS ProjectInventory;
        ''')
        conn.commit()
        conn.close()
        print("Tables dropped")

    def create_tables():
        conn = get_db_connection()
        cursor = conn.cursor()  # Create a cursor object
        cursor.execute('''
            CREATE TABLE Category (
                CategoryID INTEGER PRIMARY KEY,
                Category TEXT
            );
        ''')                        
        cursor.execute('''
            CREATE TABLE Supplier (
                SupplierID INTEGER PRIMARY KEY,
                "Supplier Name" TEXT
            );
        ''')
        cursor.execute('''
            CREATE TABLE Orders (
                OrderID INTEGER PRIMARY KEY,
                "Order Code" TEXT
            );
        ''')
        cursor.execute('''
            CREATE TABLE Purchase (
                PurchaseID INTEGER PRIMARY KEY,
                "Purchase Order No" TEXT
            );
        ''') 
        cursor.execute('''
            CREATE TABLE Description (
             "DescriptionID" INTEGER,
             "Description" TEXT,
            PRIMARY KEY("DescriptionID" AUTOINCREMENT)
            );
        ''')
        cursor.execute('''
            CREATE TABLE Manufacturer (
            ManufacturerID INTEGER PRIMARY KEY,
             "Manufacturer Number" TEXT,
            "SupplierID"	INTEGER,
            "DescriptionID" INTEGER,
            FOREIGN KEY("SupplierID") REFERENCES "Supplier"("SupplierID"),
            FOREIGN KEY("DescriptionID") REFERENCES "Description"("DescriptionID")
            );
        ''')
        cursor.execute('''
            CREATE TABLE "Inventory" (
            "StockID"	INTEGER,
	        "InventoryID"	TEXT,
	        "Stock Last Counted"	TEXT,
	        "Qty"	INTEGER,
	        "Inventory Value"	INTEGER,
	        "Unit Price"	INTEGER,
	        "Reorder Level"	NUMERIC,
	        "Reorder?"	TEXT,
            "Discontinued?"	TEXT,
	        "CategoryID"	INTEGER,
	        "SupplierID"	INTEGER,
	        "ManufacturerID"	INTEGER,
	        "OrderID"	INTEGER,
            "PurchaseID"	INTEGER,
            "DescriptionID" INTEGER,
	        PRIMARY KEY("StockID" AUTOINCREMENT),
            FOREIGN KEY("CategoryID") REFERENCES "Category"("CategoryID"),
            FOREIGN KEY("SupplierID") REFERENCES "Supplier"("SupplierID"),
	        FOREIGN KEY("ManufacturerID") REFERENCES "Manufacturer"("ManufacturerID"),
	        FOREIGN KEY("OrderID") REFERENCES "Orders"("OrderID"),
            FOREIGN KEY("PurchaseID") REFERENCES "Purchase"("PurchaseID"),
            FOREIGN KEY("DescriptionID") REFERENCES "Description"("DescriptionID")
            );
        ''')
        cursor.execute('''
            CREATE TABLE "Projects" (
                "ProjectID" INTEGER,
                "Start Date" TEXT,
                "END Date" TEXT, 
                "Invoice Number" INTEGER,
                "Project Name" TEXT,
                PRIMARY KEY("ProjectID" AUTOINCREMENT)
            );
        ''')
        cursor.execute('''
            CREATE TABLE "ProjectInventory" (
            "PI_ID" INTEGER,
            "ProjectID" INTEGER,
            "InventoryID" TEXT,
            "OrderCode" TEXT,
            "Description" TEXT,
            "Qty" INTEGER,
            PRIMARY KEY("PI_ID" AUTOINCREMENT)
            );
        ''')
        cursor.execute('''
            CREATE TABLE "UserTable" (
            "UserID" INTEGER,
            "Name" TEXT, 
            "Type" TEXT,
            "Password" TEXT,
            PRIMARY KEY("UserID" AUTOINCREMENT)
            );
        ''')
        cursor.execute('''
            CREATE TABLE "logs" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "Name" TEXT NOT NULL,
                "action" TEXT NOT NULL,
                "related_id" TEXT,
                "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')    
        conn.commit()
        conn.close()
        print("Tables Created")

    def insert_category(df):
        conn = get_db_connection()
        cursor = conn.cursor()
        # Insert data into the Category table
        for index, row in df.iterrows():
            cursor.execute('''
                INSERT INTO Category (CategoryID, Category)
                VALUES (?, ?)
            ''', (row['CategoryID'], row['Category']))
        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    def insert_supplier(df):
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Supplier table
        for index, row in df.iterrows():
            cursor.execute('''
                INSERT INTO Supplier (SupplierID, "Supplier Name")
                VALUES (?, ?)
            ''', (row['SupplierID'], row['Supplier Name']))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    def insert_orders(df):
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Orders table
        for index, row in df.iterrows():
            cursor.execute('''
                INSERT INTO Orders (OrderID, "Order Code")
                VALUES (?, ?)
            ''', (row['OrderID'], row['Order Code']))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

    def insert_purchase(df):
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Purchase table
        for index, row in df.iterrows():
            cursor.execute('''
                INSERT INTO "Purchase" (PurchaseID, "Purchase Order No")
                VALUES (?, ?)
            ''', (
                row['PurchaseID'],
                row['Purchase Order No']
            ))
        # Commit the changes and close the connection
        conn.commit()
        conn.close()


    def insert_description(df):
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Manufacture table
        for index, row in df.iterrows():
            cursor.execute('''
                INSERT INTO Description (DescriptionID, "Description")
                VALUES (?, ?)
            ''', (
                row['DescriptionID'],
                row['Description']
            ))
        conn.commit()
        conn.close()

    def insert_manufacturer(df):
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Manufacture table
        for index, row in df.iterrows():
            cursor.execute('''
                INSERT INTO Manufacturer (ManufacturerID, "Manufacturer Number", "SupplierID", "DescriptionID")
                VALUES (?, ?, ?, ?)
            ''', (
                row['ManufactureID'],
                row['Manufacturer Number'],
                row['SupplierID'],
                row['DescriptionID']
            ))
        conn.commit()
        conn.close()


    def insert_inventory(df):
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor() 
        # Insert data into the Inventory table
        for index, row in df.iterrows():
            # Handle potential empty strings or NaN in 'CategoryID' and 'SupplierID'
            category_id = int(row['CategoryID']) if pd.notna(row['CategoryID']) and row['CategoryID'] != '' else None
            supplier_id = int(row['SupplierID']) if pd.notna(row['SupplierID']) and row['SupplierID'] != '' else None
            manufacturer_id = int(row['ManufactureID']) if pd.notna(row['ManufactureID']) and row['ManufactureID'] != '' else None
            description_id = int(row['DescriptionID']) if pd.notna(row['DescriptionID']) and row['DescriptionID'] != '' else None
            purchase_id = int(row['PurchaseID']) if pd.notna(row['PurchaseID']) and row['PurchaseID'] != '' else None
            order_id = int(row['OrderID']) if pd.notna(row['OrderID']) and row['OrderID'] != '' else None

            cursor.execute('''
                INSERT INTO Inventory ("StockID", "InventoryID", "Stock Last Counted", "Qty", "Inventory Value", "Unit Price", "Reorder Level", "Reorder?", "Discontinued?", "CategoryID", "SupplierID", "ManufacturerID", "OrderID", "PurchaseID","DescriptionID")
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)
            ''', (
                row['StockID'],
                row['Inventory ID'],
                row['Stock Last Counted'],
                int(row['Qty']) if pd.notna(row['Qty']) else None,
                float(row['Inventory Value']) if pd.notna(row['Inventory Value']) else None,
                float(row['Unit Price']) if pd.notna(row['Unit Price']) else None,
                float(row['Reorder Level']) if pd.notna(row['Reorder Level']) else None,
                row['Reorder ?'],
                row['Discontinued?'],
                category_id,
                supplier_id,
                manufacturer_id,
                order_id,
                purchase_id,
                description_id
            ))

        conn.commit()
        conn.close()

    
    def insert_Usertables():
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()

        # Hash the passwords using bcrypt
        hashed_admin_password = bcrypt.hashpw('Password@1'.encode('utf-8'), bcrypt.gensalt())
        hashed_user_password = bcrypt.hashpw('Password@2'.encode('utf-8'), bcrypt.gensalt())

        # Insert data into the UserTable
        cursor.execute('''
            INSERT INTO UserTable ("Name", "Type", "Password")
            VALUES (?, ?, ?), (?, ?, ?)
        ''', 
        ('AdminUser', 'Admin', hashed_admin_password.decode('utf-8'), 
        'NormalUser', 'User', hashed_user_password.decode('utf-8')))

        conn.commit()
        conn.close()

    def insert_projects():
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Manufacture table
        cursor.execute('''
            INSERT INTO Projects ("ProjectID","Start Date", "End Date", "Invoice Number", "Project Name")
            VALUES ('1','21.05.2023','21.08.2023','12345678','SampleProject1')
        ''', 
        )
        conn.commit()
        conn.close()


    def insert_projectinventories():
        conn = get_db_connection()  # Connect to the database
        cursor = conn.cursor()
        # Insert data into the Manufacture table
        cursor.execute('''
            INSERT INTO ProjectInventory("PI_ID","ProjectID", "InventoryID", "OrderCode", "Description","Qty")
            VALUES ('1','1','None','None','None','0')
        ''', 
        )
        conn.commit()
        conn.close()
   

    drop_tables()
    create_tables() 
    insert_category(category_df)
    insert_supplier(supplier_df)
    insert_orders(orders_df)
    insert_purchase(purchase_df)
    insert_manufacturer(unique_manufactures)
    insert_description(unique_description)
    insert_inventory(sample_data_cleaned)
    insert_Usertables()
    insert_projects()
    insert_projectinventories()
    print("Data inserted successfully!")

