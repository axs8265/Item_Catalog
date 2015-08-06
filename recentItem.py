class RecentItem:
	'''Class representing basic information on Category Items'''

	#Constructor
	def __init__(self, item_id, category_id, item_name, item_desc, image):
		self.id = item_id
		self.categoryId = category_id
		self.title = item_name
		self.desc = item_desc
		self.itemImage = image