# tests/test_integrations/google/mail/operations/test_attachments.py
"""
Tests for Gmail attachment operations.
"""

import base64
import logging
from unittest.mock import MagicMock, patch

from quackcore.integrations.google.mail.operations import attachments
from tests.test_integrations.google.mail.mocks import create_mock_gmail_service


class TestGmailAttachmentOperations:
    """Test cases for Gmail attachment operations."""

    def test_process_message_parts(self, tmp_path) -> None:
        """Test processing message parts."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg123"
        storage_path = str(tmp_path)

        # Test with HTML content and attachments
        parts = [
            {
                "mimeType": "text/html",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        b"<html><body>Test</body></html>"
                    ).decode()
                },
            },
            {
                "filename": "test.pdf",
                "mimeType": "application/pdf",
                "body": {"attachmentId": "att123"},
            },
        ]

        # Mock the handle_attachment function to avoid actual file operations
        with patch(
                "quackcore.integrations.google.mail.operations.attachments.handle_attachment"
        ) as mock_handle:
            mock_handle.return_value = str(tmp_path / "test.pdf")

            html_content, attachment_paths = attachments.process_message_parts(
                gmail_service, "me", parts, msg_id, storage_path, logger
            )

            assert html_content == "<html><body>Test</body></html>"
            assert len(attachment_paths) == 1
            assert attachment_paths[0] == str(tmp_path / "test.pdf")
            mock_handle.assert_called_once()

    def test_handle_attachment(self) -> None:
        """Test handling an attachment."""
        # Get mock Gmail service
        gmail_service = create_mock_gmail_service()

        logger = logging.getLogger("test_gmail")
        msg_id = "msg1"
        storage_path = "/path/to/storage"

        # Set up attachment data
        attachment_data = base64.urlsafe_b64encode(b"PDF content").decode()

        # Test with inline data
        part = {
            "filename": "test.pdf",
            "mimeType": "application/pdf",
            "body": {"data": attachment_data, "size": 11},
        }

        # Use MagicMock for the file to properly handle method assertions
        mock_file = MagicMock()
        mock_open_func = MagicMock(return_value=mock_file)

        # Patch the clean_filename function to return unchanged filename
        with patch(
                "quackcore.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
        ):
            with patch("builtins.open", mock_open_func):
                with patch("os.path.exists", return_value=False):
                    path = attachments.handle_attachment(
                        gmail_service,
                        "me",
                        part,
                        msg_id,
                        storage_path,
                        logger,
                    )

                    assert path == "/path/to/storage/test.pdf"
                    mock_open_func.assert_called_once_with(
                        "/path/to/storage/test.pdf", "wb"
                    )
                    mock_file.__enter__().write.assert_called_once_with(b"PDF content")

        # Test with attachment ID
        part = {
            "filename": "test2.pdf",
            "mimeType": "application/pdf",
            "body": {"attachmentId": "att123", "size": 11},
        }

        mock_file = MagicMock()
        mock_open_func = MagicMock(return_value=mock_file)

        # Patch the clean_filename function to return unchanged filename
        with patch(
                "quackcore.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
        ):
            with patch("builtins.open", mock_open_func):
                with patch("os.path.exists", return_value=False):
                    path = attachments.handle_attachment(
                        gmail_service,
                        "me",
                        part,
                        msg_id,
                        storage_path,
                        logger,
                    )

                    assert path == "/path/to/storage/test2.pdf"
                    mock_open_func.assert_called_once_with(
                        "/path/to/storage/test2.pdf", "wb"
                    )
                    mock_file.__enter__().write.assert_called_once_with(
                        b"attachment content"
                    )

        # Test with filename collision
        mock_file = MagicMock()
        mock_open_func = MagicMock(return_value=mock_file)

        # Patch the clean_filename function to return unchanged filename
        with patch(
                "quackcore.integrations.google.mail.operations.attachments.clean_filename",
                side_effect=lambda x: x,
        ):
            with patch("builtins.open", mock_open_func):
                # First check exists, then doesn't for the incremented filename
                with patch("os.path.exists", side_effect=[True, False]):
                    path = attachments.handle_attachment(
                        gmail_service,
                        "me",
                        part,
                        msg_id,
                        storage_path,
                        logger,
                    )

                    assert path == "/path/to/storage/test2-1.pdf"

        # Test error handling
        with patch("base64.urlsafe_b64decode", side_effect=Exception("Decode error")):
            with patch(
                    "quackcore.integrations.google.mail.operations.attachments.clean_filename",
                    side_effect=lambda x: x,
            ):
                path = attachments.handle_attachment(
                    gmail_service, "me", part, msg_id, storage_path, logger
                )

                assert path is None