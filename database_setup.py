from sqlalchemy import Column, ForeignKey, Integer, String, BLOB, DATETIME
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()


class User(Base):
  __tablename__ = 'user'
  id = Column(Integer, primary_key=True)
  name = Column(String(250), nullable=False)
  email = Column(String(250), nullable=False)
  picture = Column(String(250), nullable=True)

class Category(Base):
    __tablename__ = 'category'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250))
    last_updated = Column(DATETIME())

    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return serialized format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'desc'         : self.description,
           'updated_on'   : str(self.last_updated)

       }
 
class CategoryItem(Base):
    __tablename__ = 'category_item'


    name =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    #Binary Column to store Item image
    image = Column(BLOB())
    last_updated = Column(DATETIME())
    category_id = Column(Integer,ForeignKey('category.id'))
    category = relationship(Category)

    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
       """Return serialized format"""
       return {
           'item_id'        : self.id,
           'name'           : self.name,
           'description'    : self.description,
           'category_id'    : self.category_id,
           'updated_on'     : str(self.last_updated)
       }



engine = create_engine('sqlite:///itemcatalogwithusers.db')
 

Base.metadata.create_all(engine)
