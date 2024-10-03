### Stock-Inventory-Tool-with-Visualisation-and-Analytical-Prediction
# Overview
- This project is a comprehensive solution for managing inventory, visualising data, and predicting reorders using machine learning models. It combines two main components:

	1. Inventory Stock Management Tool with Visualisation: A Flask-based web application that allows users to upload and clean inventory data, manage stock, and generate reports with data visualisations.

	2. Prediction of Reorder with Machine Learning Models: A machine learning system that analyses inventory data to predict when reorders are necessary based on the available stock features.

# Key Features:
- Database Modelling: SQLite is used to store inventory, project, and user data, with tables designed for optimal query performance and data integrity.

- Data Cleaning and Insertion: Uploaded inventory data is cleaned (e.g., duplicates removed, missing values handled) and inserted into the SQLite database automatically.

- Data Visualisation: Dynamic plots using matplotlib help users visualise inventory data trends.

- Reorder Prediction: The machine learning models predict when items should be reordered, reducing human error and ensuring accurate inventory control.

- Background Tasks: The application includes features like automatic database backups using APScheduler, which can be triggered manually or automatically every 7 days.

- Secure User Management: User authentication with password hashing and CSRF protection.

# Folder Structure
- The project is divided into two main parts, with individual README files included in their respective folders:

	• Inventory Tool with Visualisation: This component manages inventory data and generates reports and visualisations.
		o README.md: Detailed instructions for setting up, installation, routes, and functionality for the Inventory Tool are provided here.
	• Prediction of Reorder with Machine Learning: This component handles the machine learning prediction of inventory reorder needs.
		o README.md: Detailed instructions for installation, running the machine learning models, routes, and functionality for the Prediction Tool are provided here.

# Features
- Inventory Tool with Visualisation
	• User Authentication: Secure login with hashed passwords (bcrypt).
	• Data Upload and Cleaning: Upload Excel files, clean data, and insert it into the SQLite database.
	• Inventory Management: Add, update, view (with filters), and delete inventory items.
	• Data Visualisation: Dynamic data plots using matplotlib to visualise inventory trends.
	• Project Management: Associate projects with inventory items.
	• Reporting: Generate reports for items in stock, not in stock, and not counted for a specific period.
	• Background Jobs: Automatic database backups every 7 days with APScheduler, and manual backups via the UI.
	• Logging and Tracking: Log and view user actions within the system.

- Prediction of Reorder with Machine Learning
	• Reorder Prediction: Predict when inventory needs to be reordered using machine learning models.
	• Data Pre-processing: Clean and prepare inventory data for machine learning.
	• Model Training: Train machine learning models (e.g., Linear Regression, Decision Trees).
	• Model Evaluation: Evaluate models using metrics like Mean Squared Error (MSE).
	• Visualisation: Visualise model performance and predictions.

# Installation Guide
- Detailed installation instructions are provided in the respective folders:
	• Inventory Tool with Visualisation: Refer to the README.md file in Inventory Tool with Visualisation for installation steps.
	• Prediction of Reorder with Machine Learning: Refer to the README.md file in Prediction of Reorder with Machine Learning for setting up and running the machine learning models.


# Dataset
- The dataset used in this project ("Inventory List as at 2022") is private and not included in the repository. To request access, contact kaushik.r277@gmail.com. Alternatively, users can use their own dataset with a similar structure.

# Conclusion
- This project provides a robust solution for managing inventory data with added features for reorder prediction using machine learning. It ensures data security with authentication, visualisation for better insights, and automatic/manual backup capabilities for data protection.

- For more detailed information on each component, refer to the individual README files in their respective folders




