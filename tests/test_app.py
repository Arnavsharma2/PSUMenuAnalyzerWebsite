import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from unittest.mock import Mock

import pytest
import requests
from bs4 import BeautifulSoup

import main
from main import MEALS, AIUnavailable, Cache, MenuAnalyzer


@pytest.fixture
def analyzer():
    return MenuAnalyzer("up-east-findlay", gemini_api_key="test-key")


@pytest.fixture
def menu():
    return {
        "Breakfast": {
            "French Toast Sticks": {
                "url": "https://www.absecom.psu.edu/menus/user-pages/nutrition-label.cfm?mid=1",
                "labels": ["vegan"],
            }
        },
        "Lunch": {
            "Grilled Chicken": {
                "url": "https://www.absecom.psu.edu/menus/user-pages/nutrition-label.cfm?mid=2",
                "labels": [],
            }
        },
        "Dinner": {},
    }


def response(data=None, status=200, content=None):
    result = Mock(status_code=status, content=content)
    result.json.return_value = data
    return result


def test_exact_dates_do_not_silently_select_first_day():
    options = {"sunday, september 06": "9/6/26", "monday, september 07": "9/7/26"}
    assert MenuAnalyzer.select_date(options, date(2026, 9, 7)) == "9/7/26"
    with pytest.raises(main.MenuError, match="No menu is published"):
        MenuAnalyzer.select_date(options, date(2026, 9, 8))


def test_campus_match_requires_all_terms(analyzer):
    assert (
        analyzer.find_campus_value(
            {"east cafeteria": "wrong", "east food district @ findlay": "11"}
        )[0]
        == "11"
    )
    assert analyzer.find_campus_value({"east cafeteria": "wrong"})[0] is None


def test_source_labels_and_official_links(analyzer):
    soup = BeautifulSoup(
        """
      <div class="daily-menu-item"><a href="nutrition-label.cfm?mid=1">French Toast Sticks</a><img alt="Vegan"></div>
      <div class="daily-menu-item"><a href="nutrition-label.cfm?mid=2">Country Sausage</a><img alt="Contains Pork"></div>
      <a href="https://evil.example/nutrition-label.cfm?mid=3">Fake Food</a>
      <a href="javascript:alert(1)">Fake Link</a>
      <a href="nutrition-label.cfm?mid=4">.Toppings vary daily</a>
    """,
        "html.parser",
    )
    items = analyzer.extract_items_from_meal_page(soup)
    assert set(items) == {"French Toast Sticks", "Country Sausage"}
    assert items["French Toast Sticks"]["labels"] == ["vegan"]


def test_vegan_uses_psu_label_not_name_guess():
    analyzer = MenuAnalyzer("up-east-findlay", vegan=True)
    assert analyzer.item_allowed("French Toast Sticks", {"labels": ["vegan"]})
    assert not analyzer.item_allowed("French Toast Sticks", {"labels": []})
    assert not analyzer.item_allowed("Cheese", {"labels": ["meatless"]})


def test_vegetarian_and_plant_based_meat_filter():
    analyzer = MenuAnalyzer("up-east-findlay", vegetarian=True)
    assert analyzer.item_allowed("Eggs", {"labels": ["meatless"]})
    assert not analyzer.item_allowed("Chicken", {"labels": []})
    analyzer = MenuAnalyzer("up-east-findlay", exclude_pork=True)
    assert analyzer.item_allowed("Vegan Sausage", {"labels": ["vegan"]})
    assert not analyzer.item_allowed("Special Dumplings", {"labels": ["contains pork"]})


def test_sqlite_ttl_and_parallel_writes(tmp_path):
    cache = Cache(tmp_path)
    cache.set("expired", {"old": True}, ttl=-1)
    assert cache.get("expired") is None
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: cache.set(str(i), {"i": i}), range(30)))
    assert all(cache.get(str(i)) == {"i": i} for i in range(30))
    cache.clear()
    assert cache.get("5") is None


def test_cache_failure_is_optional(monkeypatch, tmp_path):
    file = tmp_path / "not-a-directory"
    file.write_text("file")
    cache = Cache(file)
    cache.set("key", {})
    assert cache.get("key") is None


def test_gemini_response_rejects_invented_items_and_bad_scores(analyzer, menu):
    parsed = {
        "Breakfast": [
            {"food_name": "Imaginary Food", "score": 100, "reasoning": "Invented"},
            {
                "food_name": "French Toast Sticks",
                "score": True,
                "reasoning": "Bad type",
            },
            {
                "food_name": "French Toast Sticks",
                "score": 72,
                "reasoning": "A listed vegan option.",
            },
            {"food_name": "French Toast Sticks", "score": 90, "reasoning": "Duplicate"},
        ],
        "Lunch": [
            {
                "food_name": "Grilled Chicken",
                "score": 80,
                "reasoning": "A grilled option.",
            }
        ],
        "Dinner": [],
    }
    result = analyzer.parse_recommendations(parsed, menu)
    assert len(result["Breakfast"]) == 1
    assert result["Breakfast"][0][1] == 72
    assert result["Breakfast"][0][3] == menu["Breakfast"]["French Toast Sticks"]["url"]
    parsed["Lunch"] = [
        {"food_name": "Imaginary Food", "score": 90, "reasoning": "Invented"}
    ]
    with pytest.raises(AIUnavailable):
        analyzer.parse_recommendations(parsed, menu)


def test_structured_response_handles_thought_parts_and_keeps_key_out_of_url(
    analyzer, menu, monkeypatch
):
    result = {
        meal: [
            {"food_name": name, "score": 70, "reasoning": "A menu option."}
            for name in items
        ]
        for meal, items in menu.items()
    }
    post = Mock(
        return_value=response(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"thought": True, "text": "not json"},
                                {"text": json.dumps(result)},
                            ]
                        }
                    }
                ]
            }
        )
    )
    monkeypatch.setattr(requests, "post", post)
    analyzer.analyze_menu_with_gemini(menu)
    assert "test-key" not in post.call_args.args[0]
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "test-key"
    assert (
        post.call_args.kwargs["json"]["generationConfig"]["responseMimeType"]
        == "application/json"
    )


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429])
def test_permanent_api_errors_do_not_retry(analyzer, menu, monkeypatch, status):
    post = Mock(return_value=response({"error": {"message": "private-detail"}}, status))
    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(AIUnavailable) as caught:
        analyzer.analyze_menu_with_gemini(menu)
    assert post.call_count == 1
    assert "private-detail" not in str(caught.value)


def test_transient_retry_is_bounded(analyzer, menu, monkeypatch):
    post = Mock(return_value=response({}, 503))
    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    with pytest.raises(AIUnavailable):
        analyzer.analyze_menu_with_gemini(menu)
    assert post.call_count == 2


def test_ai_outage_returns_menu_without_caching_failed_ranking(
    analyzer, menu, monkeypatch
):
    monkeypatch.setattr(analyzer, "fetch_daily_menu", lambda _: (menu, []))
    model = Mock(side_effect=AIUnavailable)
    monkeypatch.setattr(analyzer, "analyze_menu_with_gemini", model)
    result = analyzer.run_analysis(date(2026, 9, 6))
    assert result["_meta"]["analysis"] == "menu"
    assert result["Lunch"][0][0] == "Grilled Chicken"
    assert result["Lunch"][0][1] is None
    analyzer.run_analysis(date(2026, 9, 6))
    assert model.call_count == 2


def test_complete_ranking_is_cached(analyzer, menu, monkeypatch):
    fetch = Mock(return_value=(menu, []))
    model = Mock(
        return_value={
            meal: [
                (name, 70, "An option.", info["url"]) for name, info in items.items()
            ]
            for meal, items in menu.items()
        }
    )
    monkeypatch.setattr(analyzer, "fetch_daily_menu", fetch)
    monkeypatch.setattr(analyzer, "analyze_menu_with_gemini", model)
    first = analyzer.run_analysis(date(2026, 9, 6))
    second = analyzer.run_analysis(date(2026, 9, 6))
    assert not first["_meta"]["cached"] and second["_meta"]["cached"]
    assert fetch.call_count == model.call_count == 1


def test_partial_scrape_and_empty_meals_do_not_call_model_unnecessarily(
    analyzer, menu, monkeypatch
):
    monkeypatch.setattr(
        analyzer, "fetch_daily_menu", lambda _: ({meal: {} for meal in MEALS}, [])
    )
    model = Mock()
    monkeypatch.setattr(analyzer, "analyze_menu_with_gemini", model)
    result = analyzer.run_analysis(date(2026, 9, 6))
    assert result["_meta"]["published_count"] == 0
    model.assert_not_called()


def test_menu_partial_fetch_not_cached(analyzer, monkeypatch):
    monkeypatch.setattr(
        analyzer,
        "get_initial_form_data",
        lambda: {
            "campus": {"east findlay": "11"},
            "date": {"today": "9/6/26"},
            "meal": {meal.lower(): meal for meal in MEALS},
        },
    )

    def fetch(meal, *args):
        if meal == "Dinner":
            raise main.MenuError("Dinner unavailable")
        return meal, {
            "Rice": {
                "url": "https://www.absecom.psu.edu/menus/user-pages/nutrition-label.cfm?mid=2",
                "labels": ["vegan"],
            }
        }

    monkeypatch.setattr(analyzer, "fetch_single_meal", fetch)
    write = Mock()
    monkeypatch.setattr(analyzer.cache, "set", write)
    menu, warnings = analyzer.fetch_daily_menu(date(2026, 9, 6))
    assert menu["Lunch"] and not menu["Dinner"]
    assert warnings == ["Dinner unavailable"]
    write.assert_not_called()


def test_invalid_request_shapes_are_client_errors():
    with main.app.test_client() as client:
        for data in (
            [],
            None,
            {"campus": []},
            {"campus": "fake"},
            {"vegan": "false"},
            {"vegan": True, "vegetarian": True},
            {"date": "bad"},
            {"date": "2020-01-01"},
        ):
            assert client.post("/api/analyze", json=data).status_code == 400
        assert (
            client.post(
                "/api/analyze", data="bad", content_type="application/json"
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/analyze", data="a" * 5000, content_type="application/json"
            ).status_code
            == 413
        )


def test_api_surfaces_safe_errors_and_valid_dates(monkeypatch):
    monkeypatch.setattr(main, "today_at_psu", lambda: date(2026, 9, 6))

    def run(self, selected_date):
        assert selected_date == date(2026, 9, 7)
        raise main.MenuError("No menu published.", 404)

    monkeypatch.setattr(MenuAnalyzer, "run_analysis", run)
    with main.app.test_client() as client:
        result = client.post(
            "/api/analyze", json={"campus": "up-east-findlay", "date": "2026-09-07"}
        )
        assert (
            result.status_code == 404 and result.json["error"] == "No menu published."
        )


def test_cache_admin_disabled_invalid_and_authorized(monkeypatch):
    with main.app.test_client() as client:
        assert (
            client.post("/api/clear-cache", json={"password": "anything"}).status_code
            == 503
        )
        monkeypatch.setenv("CACHE_ADMIN_PASSWORD", "test-admin")
        for value in (
            None,
            [],
            {"password": None},
            {"password": 1},
            {"password": "bad"},
        ):
            assert client.post("/api/clear-cache", json=value).status_code == 401
        Cache().set("example", {"value": 1})
        assert (
            client.post("/api/clear-cache", json={"password": "test-admin"}).status_code
            == 200
        )
        assert Cache().get("example") is None


def test_public_routes_do_not_expose_source_or_secrets():
    with main.app.test_client() as client:
        for path in ("/main.py", "/.env", "/cache/menus.sqlite3"):
            assert client.get(path).status_code == 404
        assert client.get("/").status_code == 200
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/sw.js").status_code == 200
        assert client.get("/health").json["version"] == "2.0.0"
        assert client.get("/").headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("parts", [[None], [{"text": None}], [], "not-parts"])
def test_malformed_model_parts_fall_back(analyzer, menu, monkeypatch, parts):
    monkeypatch.setattr(
        requests,
        "post",
        Mock(return_value=response({"candidates": [{"content": {"parts": parts}}]})),
    )
    with pytest.raises(AIUnavailable):
        analyzer.analyze_menu_with_gemini(menu)


def test_scraper_rejects_wrong_returned_location(analyzer, monkeypatch):
    page = b'<select name="selCampus"><option selected value="40">Altoona</option></select>'
    monkeypatch.setattr(requests, "post", Mock(return_value=response(content=page)))
    with pytest.raises(main.MenuError, match="different location or date"):
        analyzer.fetch_single_meal("Lunch", "Lunch", "11", "9/6/26")


def test_psu_calendar_uses_eastern_timezone(monkeypatch):
    from datetime import datetime as RealDatetime
    from datetime import timezone

    class Clock:
        @staticmethod
        def now(zone):
            return RealDatetime(2026, 9, 7, 2, tzinfo=timezone.utc).astimezone(zone)

    monkeypatch.setattr(main, "datetime", Clock)
    assert main.today_at_psu() == date(2026, 9, 6)
