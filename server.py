from flask import Flask, render_template, request, redirect,jsonify, url_for, flash, make_response, abort
from flask import session as login_session
app = Flask(__name__)

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Category, CategoryItem

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

from werkzeug.contrib.atom import AtomFeed

from base64 import b64encode
import random, string
import datetime
import time
import os

import recentItem

#Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalogwithusers.db')
Base.metadata.bind = engine
#Create DB session for the imported DB engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/gpluslogout')
def gpluslogout():
	"""This function clears session for the currently logged-in user"""
	credentials = login_session.get('credentials')
	if credentials is None:
		response = make_response(json.dumps('Current user not conected'), 401)
		response.headers['Conten-Type'] = 'application/json'
		return response

	access_token = credentials.access_token
	#revoke the one time access token
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	res = h.request(url, 'GET')[0]
	print res['status']
	if res['status'] == '200':
		#delete user info from session object
		del login_session['credentials']
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']

		response = make_response(json.dumps('User disconnected Successfully'), 200)
		response.headers['Conten-Type'] = 'application/json'
		flash('Logout Successful')
		#Go back to home page
		return redirect(url_for('home'))
	else:
		response = make_response(json.dumps('Failed to revoke user access token'), 400)
		response.headers['Conten-Type'] = 'application/json'
		return response

@app.route('/googlepluslogin', methods=['GET','POST'])
def gpluslogin():
	"""This function helps user login using google+ auth"""
	#verify csrf token
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid State'), 401)
		response.headers['Conten-Type'] = 'application/json'
		return response
	code = request.data	
	try:
		#get code into credential obj
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		#Getting credentials
		credentials = oauth_flow.step2_exchange(code)
		#got credentials printing token
		print credentials.access_token
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade auth code'), 401)
		return response

	#check if the access token is valid
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)	
	h = httplib2.Http()
	#load and verify token
	result = json.loads(h.request(url, 'GET')[1])	
	if result.get('error') is not None:
		print "Error in validating token"
		print result.get('error')
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Conten-Type'] = 'application/json'

	#verify if access token is used for the intended user
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(json.dumps('Token''s user id doesn''t match with given user '), 401)
		response.headers['Conten-Type'] = 'application/json'
		return response

	#Chk if user is already logged in to the system
	stored_credentials = login_session.get('credentials')	
	stored_gplus_id = login_session.get('gplus_id')	
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already logged in'), 200)
		response.headers['Conten-Type'] = 'application/json'

	#store access token for later use
	login_session['credentials'] = credentials
	login_session['gplus_id'] = gplus_id
	#get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt':'json' }

	ans = requests.get(userinfo_url, params=params)	
	data = json.loads(ans.text)
	#read user data into session
	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']
	user_id = getUserID(data['email']) 
	if user_id is None:
		#User does not exist in DB. Create it
		user_id = createUser(login_session)
	login_session['user_id'] = user_id
	output = "<h1> Welcome %s!</h1>" % login_session['username']
	flash("You are now logged in as %s " % login_session['username'])
	print "gconnect function complete"
	return output

@app.route('/itemcatalog')
@app.route('/')
def home():
	'''This is the root function is to render the landing page'''
	ts = time.time()
	#set anti forgery token in the seesion
	login_session['state'] = getCSFRToken()
	#Get all categories
	categories = session.query(Category).order_by(desc(Category.name)).all()	
	#Get most recently updated 5 items	
	recentDBItems = session.query(CategoryItem).order_by(desc(CategoryItem.last_updated)).limit(5).all()
	recentItems = []
	for dbItem in recentDBItems:
		#check if item image is set by user for the recent items
		image = b64encode(dbItem.image) if dbItem.image != None else None		
		item = recentItem.RecentItem(dbItem.id, dbItem.category.id, dbItem.name, dbItem.description, image)		
		recentItems.append(item)

	#create a dic to store all categories and the number of items each of them have.
	#the number will be displayed as a small banner next to the category name
	catedoryDict  = {}
	for c in categories:
		itemsInCategory = getItemsBycategoryId(c.id)		
		catedoryDict[c] = len(itemsInCategory)	

	return render_template('home.html', loggeduser = getLoggedInUser(), categories = catedoryDict, recentItems = recentItems, STATE = login_session['state'])

@app.route('/viewCategory/')
@app.route('/viewCategory/<int:category_id>/')
def viewCategory(category_id):
	'''This function is to render details of user selected category'''	
	#Get list of all categories. This will allow user to select a different category without navigating back to homepage
	allCategories = session.query(Category).all()
	#fetch selected category	
	selectedCategory = session.query(Category).filter_by(id = category_id).one()	
	items = getItemsBycategoryId(category_id)	
	return render_template('viewcategory.html', loggeduser = getLoggedInUser(), categories = allCategories, selectedCategory = selectedCategory, items = items)

@app.route('/category/new', methods=['GET','POST'])
def addCategory():
	'''This function is to add new category to DB created by user'''
	#get current logged user
	loggeduser = getLoggedInUser()
	#get user id. this should never be none since the UI won't allow adding new category if the user has not signed in
	userId = loggeduser.id if loggeduser is not None else -1	
	if request.method == 'GET':
		#add csrf token to session and use the same value to pass along to the UI
		login_session['csfrtoken'] = getCSFRToken()
		#since it's HTTP GET then simply render the edit page w/o any category
		return render_template('editcategory.html', category = None, loggeduser = loggeduser, token = login_session['csfrtoken'])
	elif request.method == 'POST':
		#HTTP POST. User is trying to submit values, verify the csrf token first
		if request.form['csrftoken'] != login_session['csfrtoken']:
			abort(400)
		#verify values and add new cagetory
		if (request.form['name'] != None and request.form['name'] != '') and \
		 (request.form['description'] != None and request.form['description'] != ''):					
			newcategory = Category(name = request.form['name'], description = request.form['description'], \
				last_updated=datetime.datetime.now(), user_id = userId, user = loggeduser)
			session.add(newcategory)
			session.commit()
			flash('New category %s Successfully Created' % (newcategory.name))			
		return redirect(url_for('home'))


@app.route('/category/<int:category_id>/edit', methods=['GET','POST'])
def editCategory(category_id):
	'''This function is to edit an existing category'''
	category= session.query(Category).filter_by(id = category_id).one()
	if request.method == 'GET':
		#add csrf token to session and use the same value to pass along to the UI
		login_session['csfrtoken'] = getCSFRToken()
		loggeduser = getLoggedInUser()
		#since it's HTTP GET then simply render the edit page with selected category
		return render_template('editcategory.html', category = category, loggeduser = loggeduser, token = login_session['csfrtoken'])
	elif request.method == 'POST':
		#HTTP POST. User is trying to submit values, verify the csrf token first
		if request.form['csrftoken'] != login_session['csfrtoken']:
			abort(400)
		#verify values and add save user edits
		if request.form['btn']=='save' and request.form['name'] != None and request.form['description'] != None:
			category.name = request.form['name']
			category.description = request.form['description']
			category.last_updated = datetime.datetime.now()
			session.add(category)
			session.commit()
			flash('Edited category %s Successfully' % (category.name))

		return redirect(url_for('viewCategory', category_id = category_id))

@app.route('/category/<int:category_id>/delete', methods = ['POST','GET'])
def deleteCategory(category_id):
	'''This function is to delete an existing category'''
	categoryToDelete = session.query(Category).filter_by(id = category_id).one()	
	if request.method == 'POST':
		#validate csrf token
		if request.form['csrftoken'] != login_session['csfrtoken']:
			abort(400)
		#Has user clicked delete or cancel button
		if request.form['btn']=='delete':			
			items = getItemsBycategoryId(category_id)

			#Delete all items associated with this category
			for i in items:
				session.delete(i)
				session.commit()
				
			session.delete(categoryToDelete)
			session.commit()
			flash('%s Successfully Deleted' % categoryToDelete.name)
			return redirect(url_for('home'))
		else:
			#User cancelled delete
			return redirect(url_for('viewCategory', category_id = category_id))
	else:
		#add csrf token to session and use the same value to pass along to the UI
		login_session['csfrtoken'] = getCSFRToken()
		return render_template('deleteCategory.html',category = categoryToDelete, loggeduser = getLoggedInUser(), token = login_session['csfrtoken'])

@app.route('/category/<int:category_id>/item/new/', methods=['GET','POST'])
def addItem(category_id):
	'''This function is to add an item for a category'''
	loggeduser = getLoggedInUser()
	userId = loggeduser.id if loggeduser is not None else -1
	if request.method == 'GET':
		#add csrf token to session and use the same value to pass along to the UI
		login_session['csfrtoken'] = getCSFRToken()
		category= session.query(Category).filter_by(id = category_id).one()
		#since it's HTTP GET then simply render the edit page w/o any item
		return render_template('editItem.html', itemimage = None, item = None, category = category, loggeduser = loggeduser, token = login_session['csfrtoken'])
	if request.method == 'POST':
		if request.form['btn']=='cancel':
			#user clicked cancel button instead of save. go back to category page
			return redirect(url_for('viewCategory', category_id = category_id))
		#validate csrf token
		if request.form['csrftoken'] != login_session['csfrtoken']:			
			abort(400)
		#verify and add new item
		if request.form['btn']=='save' and request.form['name'] != None and request.form['description'] != None:			
			#verify image file is not none
			if request.files['img_upload'] is not None:
				imgFile = request.files['img_upload']
				#read the image file object
				itemImg = imgFile.read()
				if len(itemImg) == 0:
					#if the image length is 0, then user has not uploaded any image
					itemImg = None
			else:
				itemImg = None			
			newItem = CategoryItem(name = request.form['name'], description = request.form['description'],\
				category_id = category_id, last_updated = datetime.datetime.now(), image = itemImg, user = loggeduser,\
				user_id = userId)			
			session.add(newItem)
			session.commit()
			
			flash('New Item ''%s'' Successfully Created' % (newItem.name))
			return redirect(url_for('viewCategory', category_id = category_id, itemimage = None))

@app.route('/category/<int:category_id>/item/<int:item_id>/edit', methods=['GET','POST'])
def editItem(category_id, item_id):
	'''This function is to edit an existing item'''
	#get the item associated data from database
	category= session.query(Category).filter_by(id = category_id).one()
	selectedItem = session.query(CategoryItem).filter_by(id = item_id).one()
	itemImage = b64encode(selectedItem.image) if (selectedItem is not None and selectedItem.image is not None) else None

	loggeduser = getLoggedInUser()
	userId = loggeduser.id if loggeduser is not None else -1

	if request.method == 'GET':
		#set csrf token
		login_session['csfrtoken'] = getCSFRToken()
		#render edit template with selected category and item
		return render_template('editItem.html', loggeduser = loggeduser, item = selectedItem, \
			category = category, itemimage = itemImage, token = login_session['csfrtoken'])

	if request.method == 'POST':		
		if request.form['btn']=='cancel':
			#user clicked cancel button. go back to view category
			return redirect(url_for('viewCategory', category_id = category_id))
		#validate csrf token
		if request.form['csrftoken'] != login_session['csfrtoken']:			
			abort(400)

		#verify and save user edits
		if request.form['btn']=='save' and request.form['name'] != None and request.form['description'] != None:

			if request.files['img_upload'] != None:
				imgFile = request.files['img_upload']
				itemImg = imgFile.read()
				#make sure user did upload some data
				if len(itemImg) == 0:
					itemImg = None
			else:
				itemImg = None

			selectedItem.name = request.form['name']
			selectedItem.description = request.form['description']
			selectedItem.last_updated = datetime.datetime.now()			
			selectedItem.image = itemImg
			session.add(selectedItem)
			session.commit()
			flash('Item %s Successfully Edited' % (selectedItem.name))
			return redirect(url_for('viewCategory', category_id = category_id))


@app.route('/category/<int:category_id>/item/<string:item_id>/')
def viewItem(category_id, item_id):
	'''This function is to view an existing item.
		Since the user is allowed to select a different category from the view item page, there is no pre-selected 
		item in this case. When this happens the UI passes the itemId as 'noval'. This indicates that no item has been
		selected yet and the server select the first item in the selected category's item list.
		Hence a the data type of item id is allowed string and not int.'''	
	#Reset selected items
	selectedCategory = None	
	#itemImage = None
	allCategories = []
	allItemsForThisCategory = []

	#Get all categories for user to select any avaliable category
	allCategories = session.query(Category).all()
	
	#Get selected category and it's items
	selectedCategory = session.query(Category).filter_by(id = category_id).one()
	allItemsForThisCategory = getItemsBycategoryId(selectedCategory.id)
	try:
		#try converting the item id to integer
		intItemId = int(item_id)
		selectedItem = session.query(CategoryItem).filter_by(id = intItemId).one()		
	except ValueError:
		#no valid item id receieved. Need to select the first item from the category list.
		#if there are no items in that category and make selecting item as none
		selectedItem = allItemsForThisCategory[0] if len(allItemsForThisCategory) > 0 else None
	
	itemImage = None if (selectedItem is None or selectedItem.image is None)\
	else b64encode(selectedItem.image)

	return render_template('viewitem.html', loggeduser = getLoggedInUser(), selectedCategory =  selectedCategory, selectedItem = selectedItem,\
		categories = allCategories, items = allItemsForThisCategory, itemimage = itemImage)

#Delete an item
@app.route('/category/<int:category_id>/item/<int:item_id>/delete', methods = ['GET','POST'])
def deleteCategoryItem(category_id,item_id):
	'''This function is to delete an existing item.'''
	itemToDelete = session.query(CategoryItem).filter_by(id = item_id).one()
	if request.method == 'POST':
		if request.form['csrftoken'] != login_session['csfrtoken']:
			abort(400)
    	
    	if request.form['btn'] == 'delete':
    		#user has confimed the delete of the item
    		session.delete(itemToDelete)
    		session.commit()
    		flash('Item %s Successfully Deleted' %itemToDelete.name)

		return redirect(url_for('viewCategory', category_id = category_id))
	else:
		login_session['csfrtoken'] = getCSFRToken()
		return render_template('deleteItem.html', loggeduser = getLoggedInUser(), token = login_session['csfrtoken'], item = itemToDelete, category_id = category_id)


#Helper Functions
def getItemsBycategoryId(category_id):
	res = session.query(CategoryItem).filter_by(category_id = category_id).order_by(desc(CategoryItem.last_updated)).all()	
	return res

def getCategoryById(category_id):
	res = session.query(Category).filter_by(id = category_id).one()	
	return res

def getAllCategories():	
	res = session.query(Category).all()	
	return res

def getCSFRToken():
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))

def createUser(login_session):
	'''This function creates a new user in the application's database'''
	newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email = login_session['email']).one()
	return user.id

def getUserInfo(user_id):
	'''This function returns user object by id'''
	user = session.query(User).filter_by(id = user_id).one()
	return user

def getUserID(email):
	'''This function returns a user object by email id'''
	try:
		user = session.query(User).filter_by(email = email).one()
		return user.id
	except:
		return None

def getLoggedInUser():
	'''This function returns a user object if a user is current logged in otherwise None'''
	if 'username' not in login_session:
		return None
	else:
		return getUserInfo(login_session['user_id'])

#Endpoint functions
#JSON APIs to view a category Information by id
@app.route('/category/<int:category_id>/JSON')
def categoryAndItemsJSON(category_id):
    category = getCategoryById(category_id) #session.query(Category).filter_by(id = category_id).one()
    items = getItemsBycategoryId(category_id) #session.query(CategoryItem).filter_by(category_id = category_id).all()
    return jsonify(category=category.serialize, categoryItems=[i.serialize for i in items])

#JSON APIs to view all items in the database
@app.route('/allitems/JSON')
def categoryItemJSON():
    category_items = session.query(CategoryItem).all()
    return jsonify(categoryItems = [i.serialize for i in category_items])

#JSON APIs to view all categories in the database
@app.route('/allcategories/JSON')
def categoryJSON():
    categories = getAllCategories()
    return jsonify(categories= [c.serialize for c in categories])

#Atom API to view all items in the database
@app.route('/recentitems/ATOM')
def recentitemsAtom():	
	feed = AtomFeed('All Items', feed_url=request.url, url=request.url_root)
	category_items = session.query(CategoryItem).order_by(desc(CategoryItem.last_updated)).limit(10).all()

	for item in category_items:
		feed.add(title=item.name, summary=item.description, id=item.id,\
                 content_type='text',\
                 author= item.user.name if item.user is not None else "N/A",\
                 updated=item.last_updated)

	return feed.get_response()

#Atom API to view all items in the database
@app.route('/allcategories/ATOM')
def allcategoriesAtom():
	feed = AtomFeed('All Categories', feed_url=request.url, url=request.url_root)
	categories = session.query(Category).order_by(desc(Category.last_updated)).all()

	for category in categories:
		feed.add(title=category.name, summary=category.description, id=category.id,\
                 content_type='text',\
                 author= category.user.name if category.user is not None else "N/A",\
                 updated=category.last_updated)

	return feed.get_response()

if __name__ == '__main__':
  app.secret_key = '97912A8D-DA85-4FAB-AD47-6830003689B1'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
