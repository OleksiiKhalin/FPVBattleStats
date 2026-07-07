# FPVBattle Stats Request

## Goal

Create an analytics platform for FPVBattle results.

The project consists of three independent applications:

1. Scraper
2. Backend API
3. React frontend

The scraper continuously synchronizes race results.
The backend provides analytical APIs.
The frontend visualizes historical performance.

## Scraper Definition

The project idea is to create a scraper that scrapes the history of results and then, on a 30-minute basis, scrapes results for the current day and stores them in the database.

Website: `https://ua-velocidrone.fun/?date=2026-07-02`
The daily results can be scraped by adding a date to the link.

There are two classes: whoop and open class.
Whoop class can be accessed from `https://ua-velocidrone.fun/whoop?date=2026-07-06`

If you do not write a date in the link, it returns the results of the current date.
The day starts at `00:00 UTC`.
The new day tracks and results are uploaded at `00:10 UTC`.
The results for the current day are updated every 10 minutes.
The results of past days are final.

In open class there are four categories in which results are computed: Gold, Silver, Bronze, and Unranked.
The categories are defined above each table of results.
Before that, there were no categories. Consider this when scraping historic data and write `null` for those results and season stats.

The following point distribution is informational only and should not be recalculated:

- 1st: 100 points
- 2nd: 85 points
- 3rd: 75 points
- 4th: 67 points
- 5th: 60 points
- 6th: 54 points
- 7th: 49 points
- 8th: 45 points
- 9th: 41 points
- 10th: 38 points
- 11th: 35 points
- 12th: 33 points
- 13th: 31 points
- 14th: 29 points
- 15th: 27 points
- 16th: 25 points
- 17th: 23 points
- 18th: 22 points
- 19th: 21 points
- 20th: 20 points
- 21st: 1 point
- 22nd: 1 point
- All following places: 1 point each

The points are distributed according to places within each category, or if there are no categories, among all pilots in a class.
Whoop class is similar to historic open class and has no categories.

At the top of the page there is a track specification and sometimes a drone of the day.
If the drone of the day is shown, then places that got a result with any other drone receive 1 point.
The points are usually written on the website, so there is no need to assign them automatically. Just scrape the data.
The scraper must always trust the website and store the displayed points.

There are seasons. A season starts on the first day of the month at `00:00 UTC` and ends when the month ends.
The season information is displayed on the scraping pages.
Season stats are calculated within the scope of the season.
Daily stats like places and points are calculated within the scope of the day.

## Scraper Workflow

On first launch:

- Scrape every historical day. The furthest available date is `2023-11-15`.
- Insert missing data.
- Skip existing days.

Then every 30 minutes:

- `00:05`
- `00:35`
- `01:05`
- and so on

Scrape the current day only.
Historical days are immutable.
Current day may change until `00:10 UTC` of the next day.

The scraper must be idempotent.
Running it multiple times must never create duplicate rows.
Always upsert data according to unique keys in tables.

Allow some logic to manually rerun the historic scraper for missing days from the CLI interface.

## Database Structure

Table `day_spec`

- `id`
- `date`
- `class` (`open` or `whoop`)
- `track`
- `quad_of_the_day`
- `season`
- Unique constraint: (`date`, `class`)

Table `pilots`

- `id`
- `pilot`
- `country`
- Unique constraint: (`pilot`)

Table `results`

- `id`
- `day_spec_ref`
- `category`
- `pilot_ref`
- `quad`
- `time`
- `points`
- `place`
- Unique constraint: (`day_spec_ref`, `pilot_ref`)

Table `season_leaderboard`

- `id`
- `day_spec_ref`
- `category`
- `pilot_ref`
- `points`
- `place`
- Unique constraint: (`day_spec_ref`, `pilot_ref`)

## Visualization Specification

The data will be used in an app that mimics the initial app, but with enhanced analytical and visualization features.

Features on the main page with a daily scoreboard similar to the current app interface:

1. Ability to select which pilot you are at the top of the page in the header to define the angle of the analytics.
2. When hovering over another pilot in statistics, a small chart appears near the mouse showing how consistent that pilot was earlier in the current season, including a bar chart of skipped days and the places that pilot had.
3. Clicking on a pilot name redirects the user to the fourth chart page below on the analytical page.

These statistics are separated by class, so there is a daily scoreboard page for whoop and open class separately.

On the analytical page, again separately for each class:

1. Show the gap to the leader for a certain pilot daily for the days when that pilot flew, with clear indication of gaps where the pilot did not participate in the timeline. The time to leader is calculated as the average time of the top three results and the difference of the pilot on the specific date.
2. Country statistics: how many unique pilots, average season score, average places, and season wins in the form of visually printed gold, silver, and bronze medals as emojis.
3. Pilot stats in the form of a logarithmic chart where maximum 100% is the leader time, minimum is the lowest time of the day, and a line chart which shows the gap to the top leader of the selected pilot.
4. Pilot stats in the form of a line chart where the average top-three leaders time is indicated as a separate line, where hovering over a point shows the difference of the pilot time to that leader average. Also show a line for the average time on that day. Consider adding switches to show or hide certain times. Do not display dates when the pilot did not fly.
5. Day streaks: show information about past day streaks of the pilot in the form of green squares, but each streak is a separate header, then a horizontal line of green cubes which wraps if it falls out of the screen.

Also add a field `streak_threshold` which indicates how many days in a row are considered a streak. Use `3` by default and as the minimum.
Also show the total number of lonely days without streaks from the past: separately one-day occurrences and separately two-day occurrences as statistics on top.

## General Notes

The pilot from whose point of view the statistics are shown shall be selected uniformly across the tool in a header.
Omit pages such as Guide and social media links.
The name of the tool is `FPVBattle Stats`.

Do not implement:

- Authentication
- User accounts
- Admin panel
- Notifications
- Social features

## Goal Context

The GitHub project the website is based on is open source and located here:
`https://github.com/UaVelocidroneBattle/FPVBattle`

It can be referenced for frontend structure and some database specifics.
The intent is to create a separate showcase visualization tool to demonstrate the type of analytics the app can provide.
The preferred stack is Python for backend and scraping, and React with Vite for the frontend.

## Architecture

Use the repository pattern to make the database swappable.
Use the unit-of-work pattern to keep database writing sessions consistent.
Use SQLite for local development testing, then switch to PostgreSQL on Railway deployment.
Do not use Alembic. Rewrite the model if needed because the project is still in development.
Do not install Python libraries into the environment. Instead, list all used libraries and their correct versions in `requirements.txt`.

Create `AGENTS.md` or a similar file to give project context to future AI tools.

`AGENTS.md` must include:

- project overview
- architecture
- folder structure
- naming conventions
- coding standards
- database rules
- scraping workflow
- deployment notes
- roadmap
