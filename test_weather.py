import unittest
from unittest.mock import patch
import requests
from weather import fetch_weather

class WeatherTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": ""})
    @patch("weather.requests.get")
    def test_missing_key(self, get):
        self.assertIn("not configured", fetch_weather("Delhi"))
        get.assert_not_called()

    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "test"})
    @patch("weather.requests.get")
    def test_success(self, get):
        get.return_value.json.return_value = {"cod": 200, "main": {"temp": 25}, "weather": [{"description": "clear sky"}]}
        self.assertEqual(fetch_weather("Delhi"), "Weather in Delhi: clear sky, 25°C")
        self.assertTrue(get.call_args.args[0].startswith("https://"))
        self.assertEqual(get.call_args.kwargs["timeout"], 10)

    @patch.dict("os.environ", {"OPENWEATHER_API_KEY": "test"})
    @patch("weather.requests.get", side_effect=requests.Timeout)
    def test_timeout(self, get):
        self.assertIn("unavailable", fetch_weather("Delhi"))

if __name__ == "__main__":
    unittest.main()
