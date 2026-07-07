## Daily Pages

The **Open Daily** and **Whoop Daily** pages must display data from the **database**, retrieved through the backend API, rather than scraping or calling the original website. Format these pages to closely match the layout and appearance of the original FPVBattle leaderboard. Consider all the comments and requirements described in the initial prompt.

Instead of separate **Open Analytics** and **Whoop Analytics** pages, create two tabs:

- Pilot Stats
- General Stats

---

# Pilot Stats

Add the following controls:

- Class selector (**Open** / **Whoop**)
- Date range selector (**From** / **To**)
- A selector to switch between different analytical views.

Each analytical view should be displayed separately.

## 1. Leader Gap

Show the selected pilot's daily gap to the leader for every day they participated. The timeline should clearly indicate dates when the pilot did not participate by leaving visible gaps.

The leader reference time is calculated as the **average of the top three finishing times** for each day. The displayed gap is the difference between the selected pilot's time and that average.

## 2. Relative Performance Chart

Display a logarithmic chart where:

- **100%** represents the leader's time.
- The minimum value represents the slowest recorded time of the day.

Also display a line showing the selected pilot's gap to the leader over time.

## 3. Time Comparison Chart

Display a line chart containing:

- The selected pilot's time.
- The average time of the top three finishers.
- The overall average time for that day.

Hovering over a point should display the difference between the selected pilot's time and the average of the top three finishers.

Allow users to toggle the visibility of each line independently.

Do **not** display dates on which the selected pilot did not participate.

## 4. Day Streaks

Display the selected pilot's participation streaks using green squares.

Each streak should have its own heading, followed by a horizontal row of green squares that wraps onto the next line if necessary.

Add a **Streak Threshold** field that defines the minimum number of consecutive participation days required to qualify as a streak. The default value should be **3**, which is also the minimum allowed value.

Above the streak display, show summary statistics for participation periods that do not qualify as streaks:

- Number of single-day participations.
- Number of two-day participation periods.

---

# General Stats

Add the following controls:

- Class selector (**Open** / **Whoop**)
- Date range selector (**From** / **To**)
- A selector to switch between analytical sections.

## 1. Country Statistics

Display:

- Number of unique pilots.
- Average season score.
- Average finishing position.
- Number of medals earned by pilots.
- Number of season championships.

Represent season championships using visually displayed 🥇🥈🥉 medals. A medal set is awarded **once per season**, not per day.

Allow the table to be sorted in ascending or descending order by clicking any column header.

## 2. Quad Statistics

Display:

- Number of entries per category.
- Usage percentage.
- Number of unique pilots using each quad.
- Average finishing position.
- Number of wins.

## 3. Track Rating

For now, use **mock data** to demonstrate this feature.

Display:

- Number of votes.
- Average rating.

Apply a weighted ranking algorithm and present the tracks as a leaderboard.

## 4. Season Statistics

For each season within the selected date range, display:

- Season number.
- Number of unique pilots.
- Number of consistent pilots.
- Largest victory margin.

## 5. Participation Statistics

Display:

- Daily participant count.
- Average number of participants.
- Peak participation day.
- Lowest participation day.
- Participation trend over time.

## 6. Consistency Rankings

Display the selected pilot's consistency score at the top, followed by a global consistency leaderboard based on the distribution of finishing positions.

Also include a leaderboard of the most improved pilots overall.

---

# General Notes

- The **date range selector** affects **statistics only**. It must not affect the Daily pages.
- The **pilot selector** in the header should be a searchable dropdown and should be shared across the entire application.
- Change the application's theme to a **dark** theme with a **compact, dense layout** that closely matches the look and feel of the original FPVBattle website: https://ua-velocidrone.fun/?date=2024-07-30