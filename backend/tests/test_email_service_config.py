import os
import unittest
from unittest.mock import patch

from flask import Flask

from services import email_service


class TestEmailServiceConfig(unittest.TestCase):
    def test_placeholder_sender_falls_back_to_username(self):
        app = Flask(__name__)

        with patch.dict(
            os.environ,
            {
                "MAIL_SERVER": "smtp.gmail.com",
                "MAIL_PORT": "587",
                "MAIL_USE_TLS": "True",
                "MAIL_USE_SSL": "False",
                "MAIL_USERNAME": "sender@example.com",
                "MAIL_PASSWORD": "app-password",
                "MAIL_DEFAULT_SENDER": "SATYA <yourgmail@gmail.com>",
                "MAIL_BACKEND": "smtp",
            },
            clear=True,
        ):
            email_service.init_mail(app)

        self.assertEqual(app.config["MAIL_USERNAME"], "sender@example.com")
        self.assertEqual(app.config["MAIL_DEFAULT_SENDER"], "sender@example.com")
        self.assertEqual(app.config["MAIL_SERVER"], "smtp.gmail.com")
        self.assertEqual(app.config["MAIL_PORT"], 587)


if __name__ == "__main__":
    unittest.main()
