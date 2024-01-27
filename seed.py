#Import libraries:
from csv import DictReader
from app import db, create_app, connect_db
from models import User, Message, Follows
import traceback #Added trackback for error handling:

#Creating an instance of Flask and PostgreSQL:
app = create_app()
connect_db(app)

#Starting the database within application context:
with app.app_context():
    db.drop_all()
    db.create_all()

    ##Error handling of seed files:
    # try:
    #     with open('generator/users.csv') as users:
    #         db.session.bulk_insert_mappings(User, DictReader(users))

    #     with open('generator/messages.csv') as messages:
    #         db.session.bulk_insert_mappings(Message, DictReader(messages))

    #     with open('generator/follows.csv') as follows:
    #         db.session.bulk_insert_mappings(Follows, DictReader(follows))

    #     db.session.commit()
    try:
        pass
    except Exception as e:
        print("An error occurred while seeding the database:")
        print(e)
        traceback.print_exc()