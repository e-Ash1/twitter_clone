import os
import unittest
from app import app, db
from models import User
from sqlalchemy.exc import IntegrityError

class UserModelTestCase(unittest.TestCase):
    """Test the User model and related functionality."""

    def setUp(self):
        """Create test client, add sample data."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

        self.u1 = User.signup("test1", "email1@email.com", "password", None)
        db.session.commit()

    def tearDown(self):
        """Clean up after each test."""
        db.session.rollback()
        db.drop_all()

    def test_user_model(self):
        """Does basic model work?"""
        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)

    def test_user_signup(self):
        """Test user signup."""
        u_test = User.signup("testtesttest", "testtest@test.com", "password", None)
        db.session.commit()
        
        self.assertIsNotNone(u_test)
        self.assertEqual(u_test.username, "testtesttest")
        self.assertEqual(u_test.email, "testtest@test.com")
        self.assertNotEqual(u_test.password, "password")
        # Bcrypt strings should start with $2b$
        self.assertTrue(u_test.password.startswith("$2b$"))

    def test_duplicate_username_signup(self):
        """Test duplicate username signup."""
        with self.assertRaises(IntegrityError):
            User.signup("test1", "test@test.com", "password", None)
            db.session.commit()

    def test_duplicate_email_signup(self):
        """Test duplicate email signup."""
        with self.assertRaises(IntegrityError):
            User.signup("test2", "email1@email.com", "password", None)
            db.session.commit()

    def test_authentication(self):
        """Test user authentication."""
        u = User.authenticate("test1", "password")
        self.assertIsNotNone(u)
        self.assertEqual(u.username, "test1")

    def test_invalid_username_authentication(self):
        """Test invalid username authentication."""
        u = User.authenticate("badusername", "password")
        self.assertIsNone(u)

    def test_invalid_password_authentication(self):
        """Test invalid password authentication."""
        u = User.authenticate("test1", "badpassword")
        self.assertIsNone(u)

if __name__ == '__main__':
    unittest.main()
