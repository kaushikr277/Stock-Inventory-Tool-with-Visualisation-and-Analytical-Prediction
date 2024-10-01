####  Inventory Stock Management Tool with Visualisation

# Overview

- This is a Flask-based web application that integrates an SQLite database to manage inventory and project data. It includes features for uploading and cleaning inventory data, visualising the data using plots, and generating reports. User authentication is handled securely using bcrypt and Flask-WTF, while background tasks such as scheduled database backups are managed by APScheduler.

- The application leverages HTML, CSS, and JavaScript for the front-end and integrates with the back-end using Python Flask, along with data management using pandas, and visualisations using matplotlib.

					________________________________________


# Features

* User Authentication: Secure login and user management using hashed passwords (bcrypt).
* Data Upload: Upload excel files to replicate inventory data.
* Data Cleaning: Clean data and insert the uploaded data into the database.
* Inventory Management: Add, update, view(along with filters) and delete inventory items in the database. 
* Visualisation: Generate dynamic plots from the data using matplotlib and display them on the front-end.
* Project Management:  ability to add project with inventory items in the database and view projects.
* Reports: Generate reports for inventory items in stock, not in stock and not counted for 'X' months.
* Logging and Tracking: Keep track of user actions with a view logs page.
* Database Backup:
	+ Automatic: Backups of the SQLite database are automatically triggered every 7 days using APScheduler.
	+ Manual: Users can manually trigger a backup by clicking a button on the front-end.
- Note: Scheduled Tasks- Other background jobs, such as database cleaning, can be scheduled using APScheduler.

					________________________________________

## Dataset
The dataset used in this project ("Inventory List as at 2022") is **private** and is not included in the repository due to confidentiality reasons.

If you need access to the dataset, please contact kaushik.r277@gmail.com to request access. Alternatively, you can use your own dataset with a similar structure.

					________________________________________

# Requirements

- The following libraries and dependencies are required for the application:

* Flask - Web framework for the application.
* Flask-WTF - CSRF protection and form handling.
* bcrypt - Password hashing for secure user authentication.
* APScheduler - Scheduling background tasks.
* pandas - Data analysis and manipulation (for Excel uploads).
* matplotlib - Data visualisation (for generating plots).
* python-dateutil - Date handling and manipulation.
* sqlite3 - Database management (bundled with Python).

					________________________________________


# Installation Guide

* Step 1: Install SQLite and DB Browser
   • Install SQLite and DB Browser for SQLite to perform manual database operations.
   • Download DB Browser for SQLite

* Step 2: Install Python and Required Libraries
   • Install Python 3.8 or later from the official Python website.
   • Install Flask and the required libraries using pip:
   Navigate to the root directory of your project (My_app folder) and run the following commands in the terminal/command prompt:	

	• pip install Flask
	• pip install Flask-WTF
	• pip install bcrypt
	• pip install APScheduler
	• pip install pandas
	• pip install Werkzeug
	• pip install matplotlib
	• pip install WTForms
	• pip install python-dateutil

    - Note: sqlite3 is bundled with Python, so no separate installation is needed.

* Step 3: Check Package Installation
    - You can verify that all necessary libraries have been installed by running:
	
	• pip freeze

    - Ensure the output includes all the libraries listed above.
	
					________________________________________


# Configuration

* Setting Up Database:
   	• The database (inventory.db) will automatically be created when the a new excel is uploaded and this file is added in the application file provided.
	• Optionally, you can set up the database schema using a schema.sql file if provided.

*Environment Variables:
	• The application requires a secret key to securely sign session cookies and protect against CSRF attacks. You should configure the SECRET_KEY in the environment for security, particularly when running in production
	• It's recommended to set the SECRET_KEY as an environment variable to ensure secure and persistent handling of session data.

		SECRET_KEY=your_random_secret_key
		UPLOAD_FOLDER=uploads/

	- Ensure the SECRET_KEY is stored securely and never hardcoded into your source code.. The UPLOAD_FOLDER is where the uploaded files will be saved.

					________________________________________


- Running the Application

1. Navigate to the Project Directory:
	cd path_to_my_app

2. Install Dependencies: Install all required libraries using pip

3. Set Environment Variables: Ensure the SECRET_KEY is set as an environment variable for security, especially in production environments.

4. Run the Application:
	Start the application by running:
		Python app.py
	The application will be accessible at:
		http://127.0.0.1:5000/

5. Access the Web Application:
	- You can log in, upload files, manage inventory, and view reports through the web interface. Here are some important routes:
	o Home: /
	o Login: /login
	o Create User: /create_user
	o Add Inventory: /add_inventory
	o Update Inventory: /update_inventory
	o Upload Excel File: /upload
	o Visualisation: /visualisation
	o Add project: /add_project
	o View Projects: /view_projects
	o Reports: /reports
	o View Logs: /view_logs
	o Backup Database: /backup (for manually triggering the database backup)

					________________________________________

# Default users and Passwords:

- Upon setting up the application, the following default users are available for authentication:
* Admin User: 	
	Name - AdminUser
	Password - Password@1
* Normal Users:
	Name - NormalUser
	Password -Password@2
* Deleting Inventory or signing out parts from the project with a password:
	Password - Confirm1
- These default credentials allow for basic access and administrative functions like deleting inventory items or removing parts from a project.

					________________________________________


# Application Structure

-Here is an overview of the project structure:

My_app/
│
├── app.py                      # Main Flask application
├── data_cleaning_insertion.py   # Script for data cleaning and insertion
├── templates/                   # HTML templates for the Flask app
│   ├── Login.html
│   ├── Home.html
│   ├── Create_user.html
│   ├── add_inventory.html
│   ├── update_inventory.html
│   ├── reports.html
│   ├── visualisation.html
│   ├── upload.html
│   ├── view_logs.html
│   └── add_project.html
│
├── static/                      # Static files (CSS, JS, images)
│   ├── CSS/
│   │   └── style.css
│   ├── JS/
│   │   └── scripts.js
│   ├── Plots/                   # Folder for storing generated plots
│   │   └── visuals/
│
├── inventory.db                 # SQLite database


# Key Components:

* HTML Templates: Stored in the templates folder, they define the structure of the web pages such as login, homepage, inventory management, and reports.
* Static Files: The static folder contains CSS for styling and JavaScript for front-end interactivity.
* Data Cleaning and Insertion: The data_cleaning_insertion.py file handles the cleaning of uploaded data (e.g., removing duplicates, handling missing values) and its insertion into the SQLite database.
* SQLite Database: The inventory.db file is used to store all inventory, project, and user information.
* Automatic Backups: APScheduler automatically triggers database backups every 7 days, with the option for users to initiate a manual backup via a button on the front-end.

					________________________________________


# Background Tasks and Backup Functionality
- The application uses APScheduler to manage background tasks such as automatic database backups:
	1. Automatic Backups: The database is automatically backed up every 7 days. The backup process saves the database state to ensure that data can be restored in case of system failure or data corruption.

	2. Manual Backup: Users can trigger a manual backup of the database by clicking the "Backup" button on the front-end. This feature provides flexibility for the administrator to back up the database as needed.
					________________________________________

# Security
	1. Password Hashing: User passwords are hashed using bcrypt before storing them in the database.
	2. CSRF Protection: Flask-WTF provides built-in protection against CSRF attacks.
	3. Session Security: Flask manages user sessions securely with the help of a secret key.
					________________________________________

# Additional Information
	• Database Operations: You can use DB Browser for SQLite to manually inspect and modify the database (inventory.db).
	• Error Handling: The application is designed to handle common errors like file format issues during uploads and invalid logins. Users receive clear feedback when errors occur.


					________________________________________

# Conclusion

This application provides a powerful yet simple solution for managing inventory data and projects, with features like secure user authentication, data cleaning, reporting, and visualisation. By following the above steps, you can install, configure, and run the application smoothly. The automatic and manual database backup options provide robust data protection, ensuring the integrity of the stored information.

