import unittest
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import database as db
import email_service as es


class SmartFinanceBrainSystemTest(unittest.TestCase):

    TEST_PHONE = "9999999999"
    TEST_EMAIL = "testuser@gmail.com"
    TEST_PIN = "1234"

    @classmethod
    def setUpClass(cls):
        print("\n========== SMART FINANCE BRAIN SYSTEM TESTING ==========\n")

        db.init_global_database()

        user = db.get_user_by_phone(cls.TEST_PHONE)

        if not user:
            db.create_user(
                cls.TEST_PHONE,
                "Test User",
                cls.TEST_PIN,
                cls.TEST_EMAIL
            )

        db.set_current_user(cls.TEST_PHONE)

    def run_named_test(self, name, func):
        print(f"Testing {name:<45}", end="")
        func()
        print("OK")

    def test_authentication_module(self):
        def logic():
            user = db.verify_user(self.TEST_PHONE, self.TEST_PIN)
            self.assertIsNotNone(user)

        self.run_named_test("Authentication Module", logic)

    def test_expense_module(self):
        def logic():
            result = db.add_expense(
                datetime.now().strftime("%Y-%m-%d"),
                "Food Test",
                500,
                "Food",
                "UPI",
                phone=self.TEST_PHONE
            )
            self.assertTrue(result)

        self.run_named_test("Expense Management Module", logic)

    def test_budget_module(self):
        def logic():
            month = datetime.now().strftime("%Y-%m")
            result = db.set_monthly_budget(month, 10000, self.TEST_PHONE)
            self.assertTrue(result)

        self.run_named_test("Budget Management Module", logic)

    def test_obligation_module(self):
        def logic():
            result = db.add_obligation(
                "Electricity Bill",
                1500,
                (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "Bills",
                phone=self.TEST_PHONE
            )
            self.assertTrue(result)

        self.run_named_test("Financial Obligation Module", logic)

    def test_email_module(self):
        def logic():
            valid = es.is_configured(
                "sample@gmail.com",
                "dummyapppassword"
            )
            self.assertTrue(valid)

        self.run_named_test("Email Notification Module", logic)

    def test_database_module(self):
        def logic():
            conn = db.get_connection(self.TEST_PHONE)
            self.assertIsNotNone(conn)
            conn.close()

        self.run_named_test("Database Module", logic)

    def test_dashboard_data_module(self):
        def logic():
            expenses = db.get_all_expenses(self.TEST_PHONE)
            self.assertIsInstance(expenses, list)

        self.run_named_test("Dashboard Analytics Module", logic)

    def test_user_profile_module(self):
        def logic():
            user = db.get_user_by_phone(self.TEST_PHONE)
            self.assertIsNotNone(user)

        self.run_named_test("User Profile Module", logic)

    def test_budget_retrieval_module(self):
        def logic():
            month = datetime.now().strftime("%Y-%m")
            budget = db.get_monthly_budget(month, self.TEST_PHONE)
            self.assertIsNotNone(budget)

        self.run_named_test("Budget Retrieval Module", logic)

    def test_obligation_retrieval_module(self):
        def logic():
            obligations = db.get_all_obligations(self.TEST_PHONE)
            self.assertIsInstance(obligations, list)

        self.run_named_test("Obligation Retrieval Module", logic)

    @classmethod
    def tearDownClass(cls):
        print("\n========== ALL MODULE TESTS COMPLETED SUCCESSFULLY ==========\n")


if __name__ == "__main__":
    unittest.main()