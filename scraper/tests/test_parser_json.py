from datetime import date

from scraper.app.parsers.battle_page import parse_dashboard_json


def test_parse_dashboard_json_extracts_results_and_season_rows() -> None:
    payload = parse_dashboard_json(
        payload={
            "competition": {
                "trackName": "Basement Drift",
                "mapName": "UA Arena",
                "quadOfTheDay": "Meteor75",
            },
            "leaderboard": [
                {
                    "league": "Gold",
                    "results": [
                        {
                            "playerName": "Pilot A",
                            "country": "UA",
                            "modelName": "Meteor75",
                            "trackTime": 31234,
                            "points": 100,
                            "localRank": 1,
                        },
                    ],
                },
            ],
            "seasonLeaderboard": [
                {
                    "league": "Gold",
                    "results": [
                        {
                            "playerName": "Pilot A",
                            "country": "UA",
                            "points": 420,
                            "rank": 1,
                        },
                    ],
                },
            ],
        },
        target_date=date(2026, 7, 2),
        race_class="open",
    )

    assert payload.track == "Basement Drift"
    assert payload.quad_of_the_day == "Meteor75"
    assert len(payload.results) == 1
    assert payload.results[0].pilot == "Pilot A"
    assert payload.results[0].time == 31.234
    assert len(payload.season_leaderboard) == 1
    assert payload.season_leaderboard[0].points == 420
