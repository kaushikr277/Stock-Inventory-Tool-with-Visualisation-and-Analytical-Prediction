
import os
import secrets
import io
import matplotlib
matplotlib.use('Agg')  # Use Agg backend to avoid Tkinter issues
import matplotlib.pyplot as plt
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from flask_wtf.csrf import CSRFProtect
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
import data_cleaning_insertion
import sqlite3
from functools import wraps
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField,  SelectField,  SubmitField, FileField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from dateutil.relativedelta import relativedelta





app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
csrf = CSRFProtect(app)

#data_cleaning_insertion.clean_and_insert_data()

def get_db_connection():
    database = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(name, action, related_id = None):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('INSERT INTO logs (Name, action, related_id) VALUES (?, ?, ?)', (name, action, related_id))
    db.commit()
    print(f"Logged action: {action} with ID: {related_id}")  # Debugging statement 

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('type') != role:
                return 'Access Denied', 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Define a form class for login
class LoginForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM UserTable WHERE Name = ?', (name,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['Password'].encode('utf-8')):
            session['logged_in'] = True
            session['name'] = user['Name']
            session['type'] = user['Type']
            log_action(user['Name'], 'login')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


class CreateUserForm(FlaskForm):
    admin_name = StringField('Admin Name', validators=[DataRequired()])
    admin_password = PasswordField('Admin Password', validators=[DataRequired()])
    name = StringField('New User Name', validators=[DataRequired()])
    password = PasswordField('New User Password', validators=[DataRequired()])
    type = SelectField('Role', choices=[('Admin', 'Admin'), ('User', 'User')], validators=[DataRequired()])



@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        admin_name = form.admin_name.data
        admin_password = form.admin_password.data
        name = form.name.data
        password = form.password.data
        user_type = form.type.data

        # Hash the admin password
        hashed_admin_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())

        db = get_db_connection()
        cursor = db.cursor()

        # Verify admin name and password
        cursor.execute('SELECT * FROM UserTable WHERE Name = ? AND Type = "Admin"', (admin_name,))
        admin = cursor.fetchone()
        if admin and bcrypt.checkpw(admin_password.encode('utf-8'), admin['Password'].encode('utf-8')):
            # Hash the new user's password before storing it
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Create new user
            cursor.execute('INSERT INTO UserTable (Name, Password, Type) VALUES (?, ?, ?)', 
                           (name, hashed_password.decode('utf-8'), user_type))
            db.commit()
            log_action(admin_name, f'created new user {name} with role {user_type}')
            flash(f'New user {name} created successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid admin credentials', 'error')
            return redirect(url_for('create_user'))
    return render_template('create_user.html', form=form)

@app.route('/logout')
def logout():
    name = session.get('name')
    session.clear()
    if name:
        log_action(name, 'logout')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))
    

class UploadForm(FlaskForm):
    file = FileField('Upload Excel File', validators=[DataRequired()])
    submit = SubmitField('Upload')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        file.save(file_path)
        
        data_cleaning_insertion.clean_and_insert_data(file_path)
        
        os.remove(file_path)
        
        flash('File uploaded and processed successfully', 'success')
        return redirect(url_for('home'))  # Redirect back to home after successful upload
    
    return render_template('upload.html', form=form)

if not os.path.exists('uploads'):
    os.makedirs('uploads')


def backup_database():
    conn = get_db_connection()

    # SQL query to retrieve inventory data with joins to fetch related details
    inventory_query = '''
        SELECT
            Inventory.InventoryID,
            Inventory."Stock Last Counted",
            Inventory."Qty",
            Inventory."Unit Price",
            Inventory."Inventory Value",
            Inventory."Reorder Level",
            Inventory."Reorder?",
            Inventory."Discontinued?",
            Manufacturer."Manufacturer Number",
            Description."Description",
            Supplier."Supplier Name",
            Orders."Order Code",
            Purchase."Purchase Order No",
            Category.Category
        FROM
            Inventory
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
        LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
        LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        WHERE 1=1
    '''
    inventory_df = pd.read_sql_query(inventory_query, conn)

    # Rename columns for Inventory DataFrame
    inventory_new_column_names = {
        'InventoryID': 'Inventory ID',
        'Reorder?': 'Reorder ?'
    }
    inventory_df.rename(columns=inventory_new_column_names, inplace=True)

    # Generate the first backup file
    inventory_backup_filename = f'database_inventory_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    with pd.ExcelWriter(inventory_backup_filename, engine='openpyxl') as writer:
        worksheet = writer.book.create_sheet('Inventory Data')
        inventory_df.to_excel(writer, index=False, startrow=1, sheet_name='Inventory Data')

    # SQL query to retrieve project data with joins to fetch related details
    project_query = '''
        SELECT 
            Projects.ProjectID, 
            Projects."Project Name", 
            Projects."Start Date", 
            Projects."END Date", 
            Projects."Invoice Number", 
            ProjectInventory.InventoryID,
            ProjectInventory.Description,
            ProjectInventory."OrderCode", 
            ProjectInventory.Qty
        FROM Projects
        LEFT JOIN ProjectInventory ON Projects.ProjectID = ProjectInventory.ProjectID
    '''
    project_df = pd.read_sql_query(project_query, conn)

    # Generate the second backup file
    project_backup_filename = f'database_project_backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx'
    with pd.ExcelWriter(project_backup_filename, engine='openpyxl') as writer:
        worksheet = writer.book.create_sheet('Project Data')
        project_df.to_excel(writer, index=False, startrow=1, sheet_name='Project Data')

    conn.close()

    # Flash messages and redirect if necessary
    if inventory_backup_filename and project_backup_filename:
        flash("Database Backups Completed")
        return redirect(url_for('home'))
    
    return inventory_backup_filename, project_backup_filename

scheduler = BackgroundScheduler()
scheduler.add_job(backup_database, 'interval', days=7)
scheduler.start()

@app.route('/manual_backup')
@login_required
@role_required('Admin')
def manual_backup():
    backup_filename = backup_database()
    if backup_filename:
        return redirect(url_for('home')) 
    return send_file(backup_filename, as_attachment=True)

@app.route('/view_projects')
@login_required
def view_projects():


    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch all projects with their associated inventory items
    cursor.execute('''
        SELECT Projects.ProjectID, Projects."Project Name", Projects."Start Date", Projects."END Date", Projects."Invoice Number", 
               ProjectInventory.InventoryID,ProjectInventory.Description,ProjectInventory."OrderCode", ProjectInventory.Qty
        FROM Projects
        LEFT JOIN ProjectInventory ON Projects.ProjectID = ProjectInventory.ProjectID
    ''')
    
    rows = cursor.fetchall()
    conn.close()

    # Organize the data for easier display in the template
    projects = {}
    for row in rows:
        project_id = row['ProjectID']
        if project_id not in projects:
            projects[project_id] = {
                'ProjectID': project_id,  # Ensure ProjectID is included
                'Project Name': row['Project Name'],
                'Start Date': row['Start Date'],
                'END Date': row['END Date'],
                'Invoice Number': row['Invoice Number'],
                'Inventory': []
            }
        if row['InventoryID']:
            projects[project_id]['Inventory'].append({
                'InventoryID': row['InventoryID'],
                'OrderCode': row['OrderCode'],
                'Description': row['Description'],
                'Qty': row['Qty']
            })
    
    return render_template('view_projects.HTML', projects=projects.values())

@app.route('/add_project', methods=['GET', 'POST'])
@login_required
def add_project():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Extract project details from the form
        project_name = request.form['project_name']
        start_date_input = request.form['start_date']
        end_date_input = request.form['end_date']
        invoice_number = request.form['invoice_number']
        
    
        
         # Convert the dates to datetime objects and then to the desired format 'DD.MM.YYYY'
        start_date_obj = datetime.strptime(start_date_input, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date_input, '%Y-%m-%d')
        
        # Convert back to string in the desired format 'DD.MM.YYYY'
        start_date = start_date_obj.strftime('%d.%m.%Y')
        end_date = end_date_obj.strftime('%d.%m.%Y')

        cursor.execute('INSERT INTO projects ("Project Name","Start Date", "End Date", "Invoice Number")  VALUES (?, ?, ?, ?)',
                     (project_name, start_date, end_date, invoice_number))
        project_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        
        # Extract the inventory items and their quantities
        inventory_items = request.form.getlist('inventory[]')
        quantities = request.form.getlist('quantities[]')
        orders = request.form.getlist('ordercode[]')
        descriptions = request.form.getlist('descriptions[]')

        # Insert the selected inventory items into the project_inventory table
        for i in range(len(inventory_items)):
            inv_id = inventory_items[i]
            quantity = quantities[i]
            description = descriptions[i]  # Get the description
            order = orders[i]
            if quantity and int(quantity) > 0:
                conn.execute('INSERT INTO ProjectInventory ("ProjectID", "InventoryID", "OrderCode", "Description", "Qty") VALUES (?, ?, ?, ?, ?)',
                             (project_id, inv_id, order, description, quantity))
                
        conn.commit()
        conn.close()
        flash('Project added successfully!')
        log_action(session['name'], 'add_project', related_id=project_name)
        log_action(session['name'], 'add_project_inventory', related_id=inv_id)
        return redirect(url_for('view_projects'))

    # Fetch inventory items to display in the form
    query ='''SELECT 
                Inventory.StockID, 
                Inventory.InventoryID, 
                Description.Description,
                Orders."Order Code", 
                Manufacturer."Manufacturer Number" 
            FROM 
                Inventory
            LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
            LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
            LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID'''
    cursor.execute(query)
    inventory = cursor.fetchall()
    conn.close()
    return render_template('add_project.html', inventory=inventory)


@app.route('/fetch_inventory', methods=['GET'])
@login_required
def fetch_inventory():
    inventory_id = request.args.get('inventory_id', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query to find matching inventory and its details
    cursor.execute('''
        SELECT 
            Inventory.InventoryID,
            Description.Description,
            Manufacturer."Manufacturer Number",
            Supplier."Supplier Name"
        FROM Inventory
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        WHERE Inventory.InventoryID = ?
        LIMIT 1
    ''', (inventory_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return jsonify({
            'exists': True,
            'inventory': {
                'InventoryID': result['InventoryID'],
                'Description': result['Description'],
                'ManufacturerNumber': result['Manufacturer Number'],
                'SupplierName': result['Supplier Name']
            }
        })
    else:
        return jsonify({'exists': False})



@app.route('/search_inventory')
@login_required
def search_inventory():
    query = request.args.get('query', '')
    conn = get_db_connection()
    inventory = conn.execute('''SELECT 
                Inventory.StockID, 
                Inventory.InventoryID, 
                Description.Description, 
                Manufacturer."Manufacturer Number",
                Supplier."Supplier Name",
                Purchase."Purchase Order No",
                Orders."Order Code"
            FROM 
                Inventory
            LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
            LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
            LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
            LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
            LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
            WHERE Inventory.InventoryID LIKE ? OR Description.Description LIKE ? OR Manufacturer."Manufacturer Number" LIKE ?
    ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    conn.close()

    # # Return the results as JSON
    # return jsonify([dict(item) for item in inventory])
    # Return the results as JSON, including the ManufacturerNumber
    # Return the results as JSON, including the Manufacturer Number
    return jsonify([{
        'StockID': item['StockID'],
        'InventoryID': item['InventoryID'],
        'Description': item['Description'],
        'ManufacturerNumber': item['Manufacturer Number'],  # Handle space in the key
        'SupplierName': item['Supplier Name'],
        'PurchaseOrderNo': item['Purchase Order No'],
        'OrderCode': item['Order Code']
    } for item in inventory])

# Hash the hard-coded password once, ideally store it securely
SIGNOUT_PASSWORD_HASH = bcrypt.hashpw("Confirm1".encode('utf-8'), bcrypt.gensalt())

@app.route('/signout_inventory/<int:project_id>/<string:inventory_id>', methods=['POST'])
@login_required
def signout_inventory(project_id, inventory_id):
    password = request.form['password']
    
    # Check the password using bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), SIGNOUT_PASSWORD_HASH):
        flash("Incorrect password. Sign out not allowed.")
        return redirect(url_for('view_projects'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the Inventory ID before signing out (optional step to log the action)
    cursor.execute('SELECT InventoryID FROM ProjectInventory WHERE ProjectID = ? AND InventoryID = ?', (project_id, inventory_id))
    inventory_item = cursor.fetchone()
    if inventory_item:
        inventory_id = inventory_item['InventoryID']
    else:
        inventory_id = None

    # Example logic for signing out (removing) inventory from a project
    cursor.execute('DELETE FROM ProjectInventory WHERE ProjectID = ? AND InventoryID = ?', (project_id, inventory_id))

    conn.commit()
    conn.close()
    
    # Log the action if needed
    log_action(session['name'], 'signout_inventory', related_id=inventory_id)
    flash('Inventory signed out successfully!')
    return redirect(url_for('view_projects'))


# Route to add new inventory to an existing project
@app.route('/add_inventory_to_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def add_inventory_to_project(project_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        # Extract the inventory items and their quantities
        inventory_items = request.form.getlist('inventory[]')
        quantities = request.form.getlist('quantities[]')
        descriptions = request.form.getlist('descriptions[]')
        orders = request.form.getlist('ordercode[]')

        # Insert the selected inventory items into the project_inventory table
        for i in range(len(inventory_items)):
            inv_id = inventory_items[i]
            quantity = quantities[i]
            description = descriptions[i]
            order = orders[i]
            if quantity and int(quantity) > 0:
                # Check if the inventory already exists for the project
                existing_inventory = cursor.execute(
                    'SELECT Qty FROM ProjectInventory WHERE ProjectID = ? AND InventoryID = ?',
                    (project_id, inv_id)
                ).fetchone()

                if existing_inventory:
                    # Update the quantity if the inventory already exists
                    new_quantity = existing_inventory['Qty'] + int(quantity)
                    cursor.execute(
                        'UPDATE ProjectInventory SET Qty = ?, Description = ? OrderCode = ? WHERE ProjectID = ? AND InventoryID = ?',
                        (new_quantity, description, order, project_id, inv_id)
                    )
                else:
                    # Insert new inventory item
                    cursor.execute(
                        'INSERT INTO ProjectInventory ("ProjectID", "InventoryID","OrderCode", "Description", "Qty") VALUES (?, ?, ?, ?, ?)',
                        (project_id, inv_id, order, description, quantity)
                    )

        conn.commit()
        conn.close()
        log_action(session['name'], 'add_project', related_id=inv_id)
        flash('Inventory added to project successfully!')
        return redirect(url_for('view_projects'))

    # Fetch inventory items to display in the form
    query = '''SELECT 
                    Inventory.StockID, 
                    Inventory.InventoryID, 
                    Description.Description, 
                    orders."Order Code",
                    Manufacturer."Manufacturer Number"
                FROM 
                    Inventory
                LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
                LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
                LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID'''
    cursor.execute(query)
    inventory = cursor.fetchall()
    conn.close()
    return render_template('add_inventory_to_project.html', project_id=project_id, inventory=inventory)


@app.route('/reports')
@login_required
@role_required('Admin')
def reports_page():
    return render_template('reports.html')


@app.route('/report/parts_in_stock')
@login_required
@role_required('Admin')
def parts_in_stock():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT
            Inventory.StockID,
            Inventory.InventoryID,
            Inventory."Stock Last Counted",
            Inventory."Qty",
            Inventory."Unit Price",
            Inventory."Inventory Value",
            Inventory."Reorder Level",
            Inventory."Reorder?",
            Inventory."Discontinued?",
            Manufacturer."Manufacturer Number",
            Description."Description",
            Supplier."Supplier Name",
            Orders."Order Code",
            Purchase."Purchase Order No",
            Category.Category
        FROM
            Inventory
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
        LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
        LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        WHERE Inventory."Qty" > 0
    '''
    
    cursor.execute(query)
    parts = cursor.fetchall()
    conn.close()

    return render_template('reports.html', title="Parts in Stock", parts=parts)

@app.route('/report/parts_no_stock')
@login_required
@role_required('Admin')
def parts_no_stock():
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT
            Inventory.StockID,
            Inventory.InventoryID,
            Inventory."Stock Last Counted",
            Inventory."Qty",
            Inventory."Unit Price",
            Inventory."Inventory Value",
            Inventory."Reorder Level",
            Inventory."Reorder?",
            Inventory."Discontinued?",
            Manufacturer."Manufacturer Number",
            Description."Description",
            Supplier."Supplier Name",
            Orders."Order Code",
            Purchase."Purchase Order No",
            Category.Category
        FROM
            Inventory
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
        LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
        LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        WHERE Inventory."Qty" = 0
    '''
    
    cursor.execute(query)
    parts = cursor.fetchall()
    conn.close()

    return render_template('reports.html', title="Parts with No Stock", parts=parts)


@app.route('/report/parts_no_activity_3_months')
@login_required
@role_required('Admin')
def parts_no_activity_3_months():
    months = request.args.get('months', type=int)

    if months:
        # Calculate the cutoff date
        cutoff_date = datetime.now() - relativedelta(months=months)
        #cutoff_date_str = cutoff_date.strftime('%d.%m.%Y')  # Format as 'DD.MM.YYYY'

        # Generate report based on the calculated cutoff date
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the data and convert date strings for comparison
        query = '''
            SELECT
                Inventory.InventoryID,
                Inventory."Stock Last Counted",
                Inventory."Qty",
                Inventory."Unit Price",
                Inventory."Inventory Value",
                Inventory."Reorder Level",
                Inventory."Reorder?",
                Inventory."Discontinued?",
                Manufacturer."Manufacturer Number",
                Description."Description",
                Supplier."Supplier Name",
                Orders."Order Code",
                Purchase."Purchase Order No",
                Category.Category
            FROM
                Inventory
            LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
            LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
            LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
            LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
            LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
            LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        '''

        cursor.execute(query)
        parts = cursor.fetchall()
        conn.close()

        # Filter parts where "Stock Last Counted" is either NULL or earlier than the cutoff date
        filtered_parts = []
        for part in parts:
            stock_last_counted = part['Stock Last Counted']
            if stock_last_counted:
                # Strip whitespace and ensure the string is in the correct format
                stock_last_counted = stock_last_counted.strip()
                if len(stock_last_counted) == 10 and '.' in stock_last_counted:
                    stock_last_counted_date = datetime.strptime(stock_last_counted, '%d.%m.%Y')
                    # Compare with the cutoff date
                    if stock_last_counted_date < cutoff_date:
                        filtered_parts.append(part)
            else:
                # If 'Stock Last Counted' is NULL, include the part
                filtered_parts.append(part)

        return render_template('reports.html', title=f"Parts Not Counted for {months} Months", parts=filtered_parts, months=months)

    # If no months are provided, just render the page with the input field
    return render_template('reports.html', title="Parts Not Counted for X Months")


@app.route('/export/<report_type>')
@login_required
@role_required('Admin')
def export_report(report_type):
    conn = get_db_connection()
    cursor = conn.cursor()

    if report_type == 'parts_in_stock':
        query = '''
            SELECT
                Inventory.InventoryID,
                Inventory."Stock Last Counted",
                Inventory."Qty",
                Inventory."Unit Price",
                Inventory."Inventory Value",
                Inventory."Reorder Level",
                Inventory."Reorder?",
                Inventory."Discontinued?",
                Manufacturer."Manufacturer Number",
                Description."Description",
                Supplier."Supplier Name",
                Orders."Order Code",
                Purchase."Purchase Order No",
                Category.Category
            FROM
                Inventory
            LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
            LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
            LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
            LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
            LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
            LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
            WHERE Inventory."Qty" > 0
        '''
        title = "Parts in Stock"

    elif report_type == 'parts_no_stock':
        query = '''
            SELECT
                Inventory.InventoryID,
                Inventory."Stock Last Counted",
                Inventory."Qty",
                Inventory."Unit Price",
                Inventory."Inventory Value",
                Inventory."Reorder Level",
                Inventory."Reorder?",
                Inventory."Discontinued?",
                Manufacturer."Manufacturer Number",
                Description."Description",
                Supplier."Supplier Name",
                Orders."Order Code",
                Purchase."Purchase Order No",
                Category.Category
            FROM
                Inventory
            LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
            LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
            LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
            LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
            LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
            LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
            WHERE Inventory."Qty" = 0
        '''
        title = "Parts with No Stock"

    elif report_type == 'parts_no_activity_3_months':
        months = request.args.get('months', type=int)
        if months:
            # Calculate the cutoff date
            cutoff_date = datetime.now() - relativedelta(months=months)
            #cutoff_date_str = cutoff_date.strftime('%d.%m.%Y')  # Format as 'DD.MM.YYYY'

        # Fetch the data and convert date strings for comparison
        query = '''
            SELECT
                Inventory.InventoryID,
                Inventory."Stock Last Counted",
                Inventory."Qty",
                Inventory."Unit Price",
                Inventory."Inventory Value",
                Inventory."Reorder Level",
                Inventory."Reorder?",
                Inventory."Discontinued?",
                Manufacturer."Manufacturer Number",
                Description."Description",
                Supplier."Supplier Name",
                Orders."Order Code",
                Purchase."Purchase Order No",
                Category.Category
            FROM
                Inventory
            LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
            LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
            LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
            LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
            LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
            LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        '''

        cursor.execute(query)
        parts = cursor.fetchall()

        # Filter parts where "Stock Last Counted" is either NULL or earlier than the cutoff date
        filtered_parts = []
        for part in parts:
            stock_last_counted = part['Stock Last Counted']
            if stock_last_counted:
                # Strip whitespace and ensure the string is in the correct format
                stock_last_counted = stock_last_counted.strip()
                if len(stock_last_counted) == 10 and '.' in stock_last_counted:
                    stock_last_counted_date = datetime.strptime(stock_last_counted, '%d.%m.%Y')
                    # Compare with the cutoff date
                    if stock_last_counted_date < cutoff_date:
                        filtered_parts.append(part)
            else:
                # If 'Stock Last Counted' is NULL, include the part
                filtered_parts.append(part)

        #return render_template('reports.html', title=f"Parts Not Counted for {months} Months", parts=filtered_parts, months=months)

        title = f"Parts Not Counted for {months} Months"

    else:
        flash("Invalid report type")
        return redirect(url_for('reports_page'))

    cursor.execute(query)
    parts = cursor.fetchall()
    conn.close()

    # Convert the result to a DataFrame
    df = pd.DataFrame(parts, columns=[desc[0] for desc in cursor.description])

    # Create an Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=title)
    
    output.seek(0)

    # Send the file to the user
    return send_file(output, as_attachment=True, download_name=f"{title}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# Function to retrieve data from the database
def get_data_from_db():
    conn = get_db_connection()
    query = '''
        SELECT
            Inventory.StockID,
            Inventory.InventoryID,
            Inventory."Stock Last Counted",
            Inventory."Qty",
            Inventory."Unit Price",
            Inventory."Inventory Value",
            Inventory."Reorder Level",
            Inventory."Reorder?",
            Inventory."Discontinued?",
            Manufacturer."Manufacturer Number",
            Description."Description",
            Supplier."Supplier Name",
            Orders."Order Code",
            Purchase."Purchase Order No",
            Category.Category
        FROM
            Inventory
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
        LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
        LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        WHERE 1=1
    '''
    # Read data into a DataFrame
    sample_data_cleaned = pd.read_sql_query(query, conn)
    
    # Close the connection
    conn.close()
    
    return sample_data_cleaned

# Directory to save plots
plot_dir = 'static/plots'
if not os.path.exists(plot_dir):
    os.makedirs(plot_dir)

def create_plots(sample_data_cleaned):
    # Sort the data by 'Unit Price' and select the top 10 items
    top_10_items = sample_data_cleaned.sort_values(by='Unit Price', ascending=False).head(10)
    # Sort the data by 'Inventory Value' and select the top 10 items
    top_10_items_1 = sample_data_cleaned.sort_values(by='Inventory Value', ascending=False).head(10)
    # Sort the data by 'Inventory Value' and select the top 10 items
    top_10_items_2 = sample_data_cleaned.sort_values(by='Qty', ascending=False).head(10)
    # Create subplots with 1 row and 3 columns
    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(18, 6))

    # Plotting the top 10 items by Unit Price
    axes[0].barh(top_10_items['InventoryID'], top_10_items['Unit Price'], color='skyblue')
    axes[0].set_xlabel('Unit Price')
    axes[0].set_ylabel('Inventory ID')
    axes[0].set_title('Top 10 Items by Unit Price')
    axes[0].invert_yaxis()  # To display the highest value at the top

    # Plotting the top 10 items by Inventory Value
    axes[1].barh(top_10_items_1['InventoryID'], top_10_items_1['Inventory Value'], color='skyblue')
    axes[1].set_xlabel('Inventory Value (GBP)')
    axes[1].set_ylabel('Inventory ID')
    axes[1].set_title('Top 10 Items by Inventory Value')
    axes[1].invert_yaxis()  # To display the highest value at the top

    # Plotting the top 10 items by Qty
    axes[2].barh(top_10_items_2['InventoryID'], top_10_items_2['Qty'], color='skyblue')
    axes[2].set_xlabel('Qty')
    axes[2].set_ylabel('Inventory ID')
    axes[2].set_title('Top 10 Items by Qty')
    axes[2].invert_yaxis()  # To display the highest value at the top

    # Adjust layout to prevent overlap
    plt.tight_layout()
    # Save the plot as a PNG image
    plot_path = os.path.join(plot_dir, 'inventory_plots.png')
    plt.savefig(plot_path, format='png')

    plt.close(fig)  # Close the figure to free memory

    return plot_path

def plot_top_10_suppliers(sample_data_cleaned):
    # Create subplots with 1 row and 3 columns
    fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(18, 6))
    # Define colors for the supplier plots
    colors = plt.cm.Paired.colors[:10]  # Use the first 10 colors from the Paired colormap

    # Plot 1: Top 10 Suppliers by Count
    top_suppliers = sample_data_cleaned.groupby('Supplier Name')['Qty'].sum().sort_values(ascending=False).head(10)
    top_suppliers.plot(kind='bar', color=colors, ax=axes[0])
    axes[0].set_title('Top 10 Suppliers by Qty')
    axes[0].set_xlabel('Supplier Name')
    axes[0].set_ylabel('Qty')
    axes[0].tick_params(axis='x', rotation=90)

    # Plot 2: Top 10 Suppliers by Total Unit Price
    top_suppliers_by_price = sample_data_cleaned.groupby('Supplier Name')['Unit Price'].sum().sort_values(ascending=False).head(10)
    top_suppliers_by_price.plot(kind='bar', color=colors, ax=axes[1])
    axes[1].set_title('Top 10 Suppliers by Total Unit Price')
    axes[1].set_xlabel('Supplier Name')
    axes[1].set_ylabel('Total Unit Price (GBP)')
    axes[1].tick_params(axis='x', rotation=90)

    # Plot 3: Top 10 Suppliers by Inventory Value
    supplier_value = sample_data_cleaned.groupby('Supplier Name')['Inventory Value'].sum().sort_values(ascending=False)
    top_10_supplier_value = supplier_value.nlargest(10)
    top_10_supplier_value.plot(kind='bar', color=plt.cm.Paired.colors[:10], ax=axes[2])
    axes[2].set_title('Top 10 Suppliers by Inventory Value')
    axes[2].set_xlabel('Supplier Name')
    axes[2].set_ylabel('Inventory Value (GBP)')
    axes[2].tick_params(axis='x', rotation=90)

    # Adjust layout to prevent overlap
    plt.tight_layout()

    # Save the plot as a PNG image
    plot_path = os.path.join(plot_dir, 'top_10_suppliers.png')
    plt.savefig(plot_path, format='png')

    plt.close(fig)  # Close the figure to free memory

    return plot_path


@app.route('/Visualisation')
def show_visualisations():
    # Retrieve data from the database
    sample_data_cleaned = get_data_from_db()
    
    # Generate the plots
    plot_items_path = create_plots(sample_data_cleaned)
    plot_suppliers_path = plot_top_10_suppliers(sample_data_cleaned)
    
    # Render the HTML template and pass the plot paths
    return render_template(
        'Visualisation.html',
        plot_items_path='inventory_plots.png',
        plot_suppliers_path='top_10_suppliers.png'
    )

@app.route('/home')
@login_required
def home():
    log_action(session['name'], 'view_home')
    search = request.args.get('search')
    filters = {
        'inventory_id': request.args.get('inventory_id'),
        'stock_last_counted': request.args.get('stock_last_counted'),
        'manufacturer_number': request.args.get('manufacturer_number'),
        'description': request.args.get('description'),
        'supplier': request.args.get('supplier'),
        'purchase_order_no': request.args.get('purchase_order_no'),
        'qty': request.args.get('qty'),
        'unit_price': request.args.get('unit_price'),
        'inventory_value': request.args.get('inventory_value'),
        'order_code': request.args.get('order_code'),
        'category': request.args.get('category'),
        'reorder_level': request.args.get('reorder_level'),
        'reorder': request.args.get('reorder'),
        'discontinued': request.args.get('discontinued')
    }
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # SQL query to retrieve inventory data with joins to fetch related details
    query = '''
        SELECT
            Inventory.StockID,
            Inventory.InventoryID,
            Inventory."Stock Last Counted",
            Inventory."Qty",
            Inventory."Unit Price",
            Inventory."Inventory Value",
            Inventory."Reorder Level",
            Inventory."Reorder?",
            Inventory."Discontinued?",
            Manufacturer."Manufacturer Number",
            Description."Description",
            Supplier."Supplier Name",
            Orders."Order Code",
            Purchase."Purchase Order No",
            Category.Category
        FROM
            Inventory
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
        LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
        LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        WHERE 1=1
    '''
    
    params = []

    if search:
        query += ' AND (Inventory.InventoryID LIKE ? OR Description.Description LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param])

    if filters['inventory_id']:
        query += ' AND Inventory.InventoryID LIKE ?'
        params.append(f'%{filters["inventory_id"]}%')
    if filters['stock_last_counted']:
        query += ' AND Inventory."Stock Last Counted" LIKE ?'
        params.append(f'%{filters["stock_last_counted"]}%')
    if filters['manufacturer_number']:
        query += ' AND Manufacturer."Manufacturer Number" LIKE ?'
        params.append(f'%{filters["manufacturer_number"]}%')
    if filters['description']:
        query += ' AND Description.Description LIKE ?'
        params.append(f'%{filters["description"]}%')
    if filters['supplier']:
        query += ' AND Supplier."Supplier Name" LIKE ?'
        params.append(f'%{filters["supplier"]}%')
    if filters['purchase_order_no']:
        query += ' AND Purchase."Purchase Order No" LIKE ?'
        params.append(f'%{filters["purchase_order_no"]}%')
    if filters['qty']:
        query += ' AND Inventory."Qty" = ?'
        params.append(filters['qty'])
    if filters['unit_price']:
        query += ' AND Inventory."Unit Price" = ?'
        params.append(filters['unit_price'])
    if filters['inventory_value']:
        query += ' AND Inventory."Inventory Value" = ?'
        params.append(filters['inventory_value'])
    if filters['order_code']:
        query += ' AND Orders."Order Code" LIKE ?'
        params.append(f'%{filters["order_code"]}%')
    if filters['category']:
        query += ' AND Category.Category LIKE ?'
        params.append(f'%{filters["category"]}%')
    if filters['reorder_level']:
        query += ' AND Inventory."Reorder Level" = ?'
        params.append(filters['reorder_level'])
    if filters['reorder']:
        query += ' AND Inventory."Reorder?" LIKE ?'
        params.append(filters['reorder'])
    if filters['discontinued']:
        query += ' AND Inventory."Discontinued?" LIKE ?'
        params.append(filters['discontinued'])

    cursor.execute(query, params)
    inventory = cursor.fetchall()
    conn.close()

    
    return render_template('home.html', inventory=inventory)


@app.route('/fetch_suppliers', methods=['GET'])
def fetch_suppliers():
    query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "Supplier Name" FROM Supplier WHERE "Supplier Name" LIKE ?', ('%' + query + '%',))
    suppliers = [row['Supplier Name'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(suppliers=suppliers)

@app.route('/fetch_manufacturers', methods=['GET'])
def fetch_manufacturers():
    query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "Manufacturer Number" FROM Manufacturer WHERE "Manufacturer Number" LIKE ?', ('%' + query + '%',))
    manufacturers = [row['Manufacturer Number'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(manufacturers=manufacturers)

@app.route('/fetch_descriptions', methods=['GET'])
def fetch_descriptions():
    query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "Description" FROM Description WHERE "Description" LIKE ?', ('%' + query + '%',))
    descriptions = [row['Description'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(descriptions=descriptions)

@app.route('/fetch_purchase_orders', methods=['GET'])
def fetch_purchase_orders():
    query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT "Purchase Order No" FROM Purchase WHERE "Purchase Order No" LIKE ?', ('%' + query + '%',))
    purchaseOrders = [row['Purchase Order No'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(purchaseOrders=purchaseOrders)

@app.route('/fetch_order_codes')
def fetch_order_codes():
    query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT \"Order Code\" FROM Orders WHERE \"Order Code\" LIKE ?", ('%' + query + '%',))
    orderCodes = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(orderCodes=orderCodes)

@app.route('/fetch_categories')
def fetch_categories():
    query = request.args.get('query')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Category FROM Category WHERE Category LIKE ?", ('%' + query + '%',))
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories=categories)


@app.route('/add_inventory', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def add_inventory():

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        
        # Collect form data
        inventory_id = request.form['inventoryId']
        stock_last_counted_input = request.form['stockLastCounted']
        unit_price = float(request.form['unitPrice'])
        stock_quantity = int(request.form['stockQuantity'])
        reorder_level = float(request.form['reorderLevel'])
        reorder = 'Yes' if request.form.get('reorder') else 'No'
        discontinued = 'Yes' if request.form.get('discontinued') else 'No'
        manufacturer_number = request.form['manufacturerNumber']
        description = request.form.get('descriptionField')
        supplier_name = request.form['supplierName']
        purchase_order_no = request.form['purchaseOrderNo']
        order_code = request.form['orderCode']
        category = request.form['category']
        currency_type = request.form['currencyType']
        conversion_rate = float(request.form['conversionRate'])

        stock_last_counted_obj = datetime.strptime(stock_last_counted_input, '%Y-%m-%d').date()
        stock_last_counted = stock_last_counted_obj.strftime('%d.%m.%Y')

        # Calculate inventory value
        if currency_type != 'GBP':
            unit_price = unit_price * conversion_rate
        inventory_value = round(unit_price * stock_quantity,2)

        # Check if Category exists
        cursor.execute('SELECT CategoryID FROM Category WHERE Category = ?', (category,))
        category_row = cursor.fetchone()
        if category_row:
            category_id = category_row['CategoryID']
        else:
            cursor.execute('INSERT INTO Category (Category) VALUES (?)', (category,))
            category_id = cursor.lastrowid

        # Check if Supplier exists
        cursor.execute('SELECT SupplierID FROM Supplier WHERE "Supplier Name" = ?', (supplier_name,))
        supplier_row = cursor.fetchone()
        if supplier_row:
            supplier_id = supplier_row['SupplierID']
        else:
            cursor.execute('INSERT INTO Supplier ("Supplier Name") VALUES (?)', (supplier_name,))
            supplier_id = cursor.lastrowid

        # Check if Description exists
        cursor.execute('SELECT DescriptionID FROM Description WHERE "Description" = ?', (description,))
        description_row = cursor.fetchone()
        if description_row:
            description_id = description_row['DescriptionID']
        else:
            cursor.execute('INSERT INTO Description ("Description") VALUES (?)',(description,))
            description_id = cursor.lastrowid

        # Check if Manufacturer exists
        cursor.execute('SELECT ManufacturerID FROM Manufacturer WHERE "Manufacturer Number" = ?', (manufacturer_number,))
        manufacturer_row = cursor.fetchone()
        if manufacturer_row:
            manufacturer_id = manufacturer_row['ManufacturerID']
        else:
            cursor.execute('INSERT INTO Manufacturer ("Manufacturer Number", "SupplierID", "DescriptionID") VALUES (?, ?, ?)',
                           (manufacturer_number, supplier_id, description_id))
            manufacturer_id = cursor.lastrowid


        # Check if Order exists
        cursor.execute('SELECT OrderID FROM Orders WHERE "Order Code" = ?', (order_code,))
        order_row = cursor.fetchone()
        if order_row:
            order_id = order_row['OrderID']
        else:
            cursor.execute('INSERT INTO Orders ("Order Code") VALUES (?)', (order_code,))
            order_id = cursor.lastrowid

        # Check if Purchase exists
        cursor.execute('SELECT PurchaseID FROM Purchase WHERE "Purchase Order No" = ?', (purchase_order_no,))
        purchase_row = cursor.fetchone()
        if purchase_row:
            purchase_id = purchase_row['PurchaseID']
        else:
            cursor.execute('INSERT INTO Purchase ("Purchase Order No") VALUES (?)', (purchase_order_no,))
            purchase_id = cursor.lastrowid

        # Insert into Inventory
        cursor.execute('''
            INSERT INTO Inventory ("InventoryID", "Stock Last Counted", "Qty", "Inventory Value", "Unit Price", "Reorder Level", "Reorder?", "Discontinued?", "CategoryID", "SupplierID", "ManufacturerID", "OrderID", "PurchaseID","DescriptionID")
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (inventory_id, stock_last_counted, stock_quantity, inventory_value, unit_price, reorder_level, reorder, discontinued, category_id, supplier_id, manufacturer_id, order_id, purchase_id, description_id))

        conn.commit()
        conn.close()
        last_id = cursor.lastrowid
        print(f"Added inventory with ID: {last_id}")
        log_action(session['name'], 'add_inventory', related_id = inventory_id)
        flash("Data Inserted Successfully")
        return redirect(url_for('home'))

    cursor.execute('SELECT "Manufacturer Number" FROM Manufacturer')
    manufacturerNumbers = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT "Description" FROM Description')
    descriptions = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT "Description" FROM Manufacturer')
    descriptions = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT "Supplier Name" FROM Supplier')
    suppliers = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT "Order Code" FROM Orders')
    orderCodes = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT "Purchase Order No" FROM Purchase')
    purchaseOrders = [row[0] for row in cursor.fetchall()]
    cursor.execute('SELECT Category FROM Category')
    categories = [row[0] for row in cursor.fetchall()]

    conn.close()

    return render_template('add_inventory.html', manufacturerNumbers=manufacturerNumbers, descriptions=descriptions, suppliers=suppliers, orderCodes=orderCodes, purchaseOrders=purchaseOrders, categories=categories)


@app.route('/update_inventory/<int:stock_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def update_inventory(stock_id):
    
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Collect form data
        inventory_id = request.form['inventoryId']
        stock_last_counted = request.form['stockLastCounted']
        unit_price = float(request.form['unitPrice'])
        stock_quantity = int(request.form['stockQuantity'])
        reorder_level = float(request.form['reorderLevel'])
        reorder = 'Yes' if request.form.get('reorder') else 'No'
        discontinued = 'Yes' if request.form.get('discontinued') else 'No'
        manufacturer_number = request.form['manufacturerNumber']
        description = request.form.get('descriptionField')
        supplier_name = request.form['supplierName']
        purchase_order_no = request.form['purchaseOrderNo']
        order_code = request.form['orderCode']
        category = request.form['category']
        currency_type = request.form['currencyType']
        conversion_rate = float(request.form['conversionRate'])

        #stock_last_counted_obj = datetime.strptime(stock_last_counted_input, '%Y-%m-%d').date()
        #stock_last_counted = stock_last_counted_obj.strftime('%d.%m.%Y')

        # Calculate inventory value
        if currency_type != 'GBP':
            unit_price = unit_price * conversion_rate
        inventory_value = round(unit_price * stock_quantity,2)

        # Check if Category exists
        cursor.execute('SELECT CategoryID FROM Category WHERE Category = ?', (category,))
        category_row = cursor.fetchone()
        if category_row:
            category_id = category_row['CategoryID']
        else:
            cursor.execute('INSERT INTO Category (Category) VALUES (?)', (category,))
            category_id = cursor.lastrowid

        # Check if Supplier exists
        cursor.execute('SELECT SupplierID FROM Supplier WHERE "Supplier Name" = ?', (supplier_name,))
        supplier_row = cursor.fetchone()
        if supplier_row:
            supplier_id = supplier_row['SupplierID']
        else:
            cursor.execute('INSERT INTO Supplier ("Supplier Name") VALUES (?)', (supplier_name,))
            supplier_id = cursor.lastrowid

        # Check if Description exists
        cursor.execute('SELECT DescriptionID FROM Description WHERE "Description" = ?', (description,))
        description_row = cursor.fetchone()
        if description_row:
            description_id = description_row['DescriptionID']
        else:
            cursor.execute('INSERT INTO Description ("Description") VALUES (?)', (description,))
            description_id = cursor.lastrowid

        # Check if Manufacturer exists
        cursor.execute('SELECT ManufacturerID FROM Manufacturer WHERE "Manufacturer Number" = ?', (manufacturer_number,))
        manufacturer_row = cursor.fetchone()
        if manufacturer_row:
            manufacturer_id = manufacturer_row['ManufacturerID']
        else:
            cursor.execute('INSERT INTO Manufacturer ("Manufacturer Number", "SupplierID", "DescriptionID") VALUES (?,?,?)',
                           (manufacturer_number, supplier_id, description_id))
            manufacturer_id = cursor.lastrowid

            

        # Check if Order exists
        cursor.execute('SELECT OrderID FROM Orders WHERE "Order Code" = ?', (order_code,))
        order_row = cursor.fetchone()
        if order_row:
            order_id = order_row['OrderID']
        else:
            cursor.execute('INSERT INTO Orders ("Order Code") VALUES (?)', (order_code,))
            order_id = cursor.lastrowid

        # Check if Purchase exists
        cursor.execute('SELECT PurchaseID FROM Purchase WHERE "Purchase Order No" = ?', (purchase_order_no,))
        purchase_row = cursor.fetchone()
        if purchase_row:
            purchase_id = purchase_row['PurchaseID']
        else:
            cursor.execute('INSERT INTO Purchase ("Purchase Order No") VALUES (?)', (purchase_order_no,))
            purchase_id = cursor.lastrowid

        # Update Inventory
        cursor.execute('''
            UPDATE Inventory
            SET "InventoryID" = ?, "Stock Last Counted" = ?, "Qty" = ?, "Inventory Value" = ?, "Unit Price" = ?, "Reorder Level" = ?, "Reorder?" = ?, "Discontinued?" = ?, "CategoryID" = ?, "SupplierID" = ?, "ManufacturerID" = ?, "OrderID" = ?, "PurchaseID" = ?, "DescriptionID" = ? 
            WHERE "StockID" = ?
        ''', (inventory_id, stock_last_counted, stock_quantity, inventory_value, unit_price, reorder_level, reorder, discontinued, category_id, supplier_id, manufacturer_id, order_id, purchase_id, description_id, stock_id))

        conn.commit()
        conn.close()
        print(f"Updated inventory with StockID: {stock_id} and InventoryID: {inventory_id}")
        log_action(session['name'], 'update_inventory', related_id = inventory_id)  # Log the Inventory ID
        flash("Data Updated Successfully")

        return redirect(url_for('home'))

    # Fetch existing data
    cursor.execute('''
        SELECT
            Inventory.StockID,
            Inventory.InventoryID,
            Inventory."Stock Last Counted",
            Inventory."Qty",
            Inventory."Unit Price",
            Inventory."Reorder Level",
            Inventory."Reorder?",
            Inventory."Discontinued?",
            Manufacturer."Manufacturer Number",
            Description."Description",
            Supplier."Supplier Name",
            Orders."Order Code",
            Purchase."Purchase Order No",
            Category.Category
        FROM
            Inventory
        LEFT JOIN Manufacturer ON Inventory.ManufacturerID = Manufacturer.ManufacturerID
        LEFT JOIN Description ON Inventory.DescriptionID = Description.DescriptionID
        LEFT JOIN Supplier ON Inventory.SupplierID = Supplier.SupplierID
        LEFT JOIN Orders ON Inventory.OrderID = Orders.OrderID
        LEFT JOIN Purchase ON Inventory.PurchaseID = Purchase.PurchaseID
        LEFT JOIN Category ON Inventory.CategoryID = Category.CategoryID
        WHERE Inventory.StockID = ?
    ''', (stock_id,))
    item = cursor.fetchone()
    conn.close()

    return render_template('update_inventory.html', item=item)

# Hash the hard-coded password once, ideally store it securely
DELETE_PASSWORD_HASH = bcrypt.hashpw("Confirm1".encode('utf-8'), bcrypt.gensalt())

@app.route('/delete_inventory/<int:stock_id>', methods=['POST'])    
def delete_inventory(stock_id):
    password = request.form['password']
    
    # Check the password using bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), DELETE_PASSWORD_HASH):
        flash("Incorrect password. Deletion not allowed.")
        return redirect(url_for('home'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch the Inventory ID before deleting
    cursor.execute('SELECT InventoryID FROM Inventory WHERE StockID = ?', (stock_id,))
    inventory_item = cursor.fetchone()
    if inventory_item:
        inventory_id = inventory_item['InventoryID']
    else:
        inventory_id = None

    cursor.execute('DELETE FROM Inventory WHERE StockID = ?', (stock_id,))
    conn.commit()
    conn.close()

    # Log the action
    log_action(session['name'], 'delete_inventory', related_id=inventory_id)
    flash("Inventory item deleted successfully.")
    return redirect(url_for('home'))



@app.route('/view_logs')
@login_required
@role_required('Admin')
def view_logs():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM logs')
    logs = cursor.fetchall()
    return render_template('view_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)