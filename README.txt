README:
This project contains python code for creating and running an item catalog website. Folders:
Item_Catalog: Primary folder containing python code to create 
	1) A sqlalchemy database
	2) Python code to run a web server using flask framework
	3) JSON file containing google+ web app details
static: Contains all the js, font and css files used by the web site
templates: Contains all the Jinja templates employed by the cataloging website

How to run:
Run server.py. Navigate to http://localhost:5000. This will render application's landing page. You can navigate through existing data. However in order to create new data, please first login with the google+ account.

NOTE: 1)You'll be able to modify the data you have created with your login, but not the data created by other logins
		2) Login using Facebook account is not yet implemented

	 