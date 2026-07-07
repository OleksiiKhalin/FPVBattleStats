from datetime import date

from scraper.app.parsers.battle_page import parse_battle_page


def test_parse_open_html_sections_extracts_results_and_season_rows() -> None:
    html = """
    <html><body>
      <h1>Summer Sprint</h1>
      <div class="flex items-center justify-between">
        <h3 class="text-sm uppercase tracking-wider text-emerald-400 font-medium pl-1 flex items-baseline gap-2">
          TODAY'S LEADERBOARD<span>12 pilots</span>
        </h3>
      </div>
      <div class="flex flex-col gap-6">
        <div class="bg-slate-800/50 backdrop-blur-sm border border-slate-700 overflow-hidden">
          <div><span>Gold</span></div>
          <ul>
            <li>
              <div>
                <span>01</span>
                <a href="/statistics/profile/MGescapades">MGescapades</a>
                <p>Twig XL 3</p>
                <span class="fi fi-us text-sm" title="US"></span>
                <div class="text-sm font-semibold text-slate-200 tabular-nums text-right">64.42s</div>
              </div>
            </li>
          </ul>
        </div>
        <div class="bg-slate-800/50 backdrop-blur-sm border border-slate-700 overflow-hidden">
          <div><span>Unranked</span></div>
          <ul>
            <li>
              <div>
                <span>02</span>
                <a href="/statistics/profile/MasuFPV">MasuFPV</a>
                <p>Bahamut</p>
                <span class="fi fi-jp text-sm" title="JP"></span>
                <div class="text-sm font-semibold text-slate-200 tabular-nums text-right">66.58s</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
      <h3>SEASON LEADERBOARD<span>81 pilots</span></h3>
      <div class="flex flex-col gap-6">
        <div class="bg-slate-800/50 backdrop-blur-sm border border-slate-700 overflow-hidden">
          <div><span>Gold</span></div>
          <ul>
            <li>
              <div>
                <span>02</span>
                <a href="/statistics/profile/MGescapades">MGescapades</a>
                <span class="fi fi-us text-sm" title="US"></span>
                <div class="text-sm font-semibold text-slate-200 tabular-nums text-right">490</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </body></html>
    """

    payload = parse_battle_page(html=html, target_date=date(2026, 7, 7), race_class="open")

    assert len(payload.results) == 2
    assert payload.results[0].category == "gold"
    assert payload.results[0].pilot == "MGescapades"
    assert payload.results[0].country == "US"
    assert payload.results[0].quad == "Twig XL 3"
    assert payload.results[0].time == 64.42
    assert payload.results[0].points is None
    assert payload.results[1].category == "unranked"
    assert payload.results[1].country == "JP"
    assert len(payload.season_leaderboard) == 1
    assert payload.season_leaderboard[0].pilot == "MGescapades"
    assert payload.season_leaderboard[0].points == 490


def test_parse_whoop_html_section_extracts_points() -> None:
    html = """
    <html><body>
      <h1>Whoop Arena</h1>
      <div class="flex items-center justify-between">
        <h3>TODAY'S LEADERBOARD<span>13 pilots</span></h3>
      </div>
      <div>
        <div class="bg-slate-800/50 backdrop-blur-sm border border-slate-700 overflow-hidden">
          <ul>
            <li>
              <div>
                <span>01</span>
                <a href="/statistics/profile/Raimon%20Shaigne">Raimon Shaigne</a>
                <p>Tiny Hawk</p>
                <span class="fi fi-fr text-sm" title="FR"></span>
                <div class="text-sm font-semibold text-slate-200 tabular-nums text-right">55.48s</div>
                <div class="text-sm font-semibold text-emerald-400 tabular-nums text-right">100</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </body></html>
    """

    payload = parse_battle_page(html=html, target_date=date(2026, 7, 7), race_class="whoop")

    assert len(payload.results) == 1
    assert payload.results[0].category is None
    assert payload.results[0].pilot == "Raimon Shaigne"
    assert payload.results[0].country == "FR"
    assert payload.results[0].quad == "Tiny Hawk"
    assert payload.results[0].time == 55.48
    assert payload.results[0].points == 100
