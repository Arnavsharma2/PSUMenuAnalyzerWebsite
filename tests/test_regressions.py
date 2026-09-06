from bs4 import BeautifulSoup

from main import MenuAnalyzer


def test_scraper_keeps_grilled_food_and_rejects_navigation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    analyzer = MenuAnalyzer("up-east-findlay")
    soup = BeautifulSoup(
        """
        <a href="https://pennstateeats.psu.edu/">Penn State Eats</a>
        <a href="nutrition-label.cfm?mid=1">Grilled Chicken</a>
        <a href="nutrition-label.cfm?mid=2">Deli Turkey Sandwich</a>
    """,
        "html.parser",
    )
    assert set(analyzer.extract_items_from_meal_page(soup)) == {
        "Grilled Chicken",
        "Deli Turkey Sandwich",
    }


def test_pork_filter_does_not_match_ham_inside_another_word(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    analyzer = MenuAnalyzer("up-east-findlay", exclude_pork=True)
    items = [("Graham Crackers", 50, "Snack", "#"), ("Ham Sandwich", 60, "Lunch", "#")]
    assert [item[0] for item in analyzer.apply_hard_filters(items)] == [
        "Graham Crackers"
    ]
