import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from backend.monitor import check_endpoint, validate_url


class MonitorTests(unittest.TestCase):
    @patch("backend.monitor.socket.getaddrinfo")
    def test_validate_url_accepts_public_https(self, mock_dns):
        mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 443))]
        self.assertEqual(validate_url("https://example.com"), "https://example.com")

    def test_validate_url_rejects_unsupported_protocol(self):
        with self.assertRaisesRegex(ValueError, "HTTP or HTTPS"):
            validate_url("file:///etc/passwd", resolve_dns=False)

    @patch("backend.monitor.socket.getaddrinfo")
    @patch("backend.monitor.urlopen")
    def test_online_endpoint(self, mock_urlopen, mock_dns):
        mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 443))]
        response = MagicMock()
        response.status = 200
        mock_urlopen.return_value.__enter__.return_value = response
        result = check_endpoint("https://example.com")
        self.assertEqual(result["status"], "online")
        self.assertEqual(result["status_code"], 200)
        self.assertIsNotNone(result["response_time_ms"])

    @patch("backend.monitor.socket.getaddrinfo")
    @patch("backend.monitor.urlopen")
    def test_http_error_is_offline(self, mock_urlopen, mock_dns):
        mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 443))]
        mock_urlopen.side_effect = HTTPError(
            "https://example.com/missing", 503, "Unavailable", {}, None
        )
        result = check_endpoint("https://example.com/missing")
        self.assertEqual(result["status"], "offline")
        self.assertEqual(result["status_code"], 503)

    def test_private_endpoint_is_rejected(self):
        result = check_endpoint("http://127.0.0.1")
        self.assertEqual(result["status"], "offline")
        self.assertIn("public internet", result["error"])


if __name__ == "__main__":
    unittest.main()
