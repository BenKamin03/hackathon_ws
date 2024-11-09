import pyrebase
import os
from dotenv import load_dotenv
import json

class FirebaseConnection:
    def __init__(self):
        load_dotenv()
        self.config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": os.getenv("FIREBASE_APP_ID"),
            "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID")
        }

        self.firebase = pyrebase.initialize_app(self.config)
        self.db = self.firebase.database()

    def get_tenants(self):
        users = self.db.child("tenants").get()
        return users.val()
    
    def get_meeting(self, meeting_id):
        users = self.db.child("meetings").child(meeting_id).get()
        return users.val()
    
    def add_meeting_data(self, meeting_id, data):
        self.db.child("meetings").child(meeting_id).set(data)

    def get_meeting_users(self, meeting_id):
        users = self.db.child('meetingUsers').order_by_child("meetingId").equal_to(meeting_id).get()
        user_ids = [user.val()['user_id'] for user in users.each()]
        return user_ids