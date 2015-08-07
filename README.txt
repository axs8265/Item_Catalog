README:
This project contains python code for creating and running an item catalog website. Folders:
Item_Catalog: Primary folder containing python code to create 
	1) A sqlalchemy database
	2) Python code to run a web server using flask framework
	3) JSON file containing google+ web app details
static: Contains all the js, font and css files used by the web site
templates: Contains all the Jinja templates employed by the cataloging website

Feeds:
	Atom:
		List of recent Items:- http://localhost:5000/recentitems/ATOM
		List of all categories:- http://localhost:5000/allcategories/ATOM
	JSON:
		Category details (by category id):- http://localhost:5000/category/<int:category_id>/JSON
		List of all items:- http://localhost:5000/allitems/JSON
		List of all categories:- http://localhost:5000/allcategories/JSON

How to run:
1) Run database_setup.py
Run server.py. Navigate to http://localhost:5000. This will render application's landing page. You can navigate through existing data. However in order to create new data, please first login with the google+ account.

NOTE: 1)You'll be able to modify the data you have created with your login, but not the data created by other logins
		

Change Log:
1) Corrected TypeError: <oauth2client.client.OAuth2Credentials for new version of flask
2) Using SeaSurf to prevent CSRF attacks
3) Using backref and cascading delete in database set-up
4) Users can now login using Facebook credentials
5) Readme file updated for 'How to run' steps

	 