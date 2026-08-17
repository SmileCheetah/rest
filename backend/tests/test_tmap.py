import unittest

from app.services.tmap import TmapProviderError, parse_pedestrian_route


class TmapResponseTest(unittest.TestCase):
    def test_parse_pedestrian_route(self) -> None:
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [127.0105, 37.5739],
                    },
                    "properties": {"totalDistance": 615, "totalTime": 481},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [127.0105, 37.5739],
                            [127.0109, 37.5742],
                        ],
                    },
                    "properties": {},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [127.0109, 37.5742],
                            [127.01142, 37.57471],
                        ],
                    },
                    "properties": {},
                },
            ],
        }

        route = parse_pedestrian_route(payload)

        self.assertEqual(route.distance_meters, 615)
        self.assertEqual(route.walking_minutes, 9)
        self.assertEqual(len(route.path), 3)
        self.assertEqual(route.path[0].longitude, 127.0105)
        self.assertEqual(route.path[-1].latitude, 37.57471)

    def test_rejects_missing_route_data(self) -> None:
        with self.assertRaises(TmapProviderError):
            parse_pedestrian_route({"features": []})


if __name__ == "__main__":
    unittest.main()
