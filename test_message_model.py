import os
import unittest
from app import create_app, db
from models import User, Message, Likes

os.environ['DATABASE_URL'] = "postgresql://postgres:admin@localhost/warbler_test"


class MessageModelTestCase(unittest.TestCase):
    """Test models for messages."""

    def setUp(self):
        """Create and configure the app for testing."""
        self.app = create_app()
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_message_model(self):
        """Test the Message model."""
        user = User.signup("testing", "testing@test.com", "password", None)
        db.session.commit()

        message = Message(text="Test message", user_id=user.id)
        db.session.add(message)
        db.session.commit()

        self.assertEqual(message.text, "Test message")
        self.assertEqual(message.user, user)

if __name__ == '__main__':
    unittest.main()
