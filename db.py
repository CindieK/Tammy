# Move to DB
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
import logging

engine = sqlalchemy.create_engine("mysql+pymysql://root:secret@127.0.0.1:3306/tammydb")
Base = declarative_base()

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class History(Base):
    __tablename__ = 'history'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer)
    filename = sqlalchemy.Column(sqlalchemy.String(length=100))
    transcript = sqlalchemy.Column(sqlalchemy.String(length=10000))
    date = sqlalchemy.Column(sqlalchemy.DateTime)

class User(Base):
    __tablename__ = 'user'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    email = sqlalchemy.Column(sqlalchemy.String(length=100))
    username = sqlalchemy.Column(sqlalchemy.String(length=100))
    password = sqlalchemy.Column(sqlalchemy.String(length=20))

Base.metadata.create_all(engine)

# Create a session
db_session = sqlalchemy.orm.sessionmaker()
db_session.configure(bind=engine)
db = db_session()