# Holiday Gate — KL Public Holiday Check

Before any scrum activity, check if today is a KL public holiday.

## Method: Offline Hijri Calendar Algorithm

Script at `~/.hermes/scripts/scrum/check-holiday.py` uses an offline computation algorithm:

```python
# Uses the Kuwaiti Algorithm (standard Hijri-Gregorian conversion)
# to compute Islamic holidays for any Gregorian year up to 15 years in advance.
# Combined with a known set of fixed-date Malaysian national holidays.
```

```bash
python3 ~/.hermes/scripts/scrum/check-holiday.py
# Returns: "OK" (working day) or "HOLIDAY: Nuzul Al-Quran" (holiday name)
```

## How Cron Jobs Use It

**9am, 11am, 5pm:** The first action in each script/cron prompt is to check the holiday gate:

```python
import subprocess
result = subprocess.run(
    ["python3", os.path.expanduser("~/.hermes/scripts/scrum/check-holiday.py")],
    capture_output=True, text=True, timeout=10
)
if result.returncode == 0 and result.stdout.strip().startswith("HOLIDAY"):
    holiday_name = result.stdout.strip().split(":", 1)[1].strip()
    print(f"HOLIDAY: {holiday_name} — scrum paused")
    sys.exit(0)
# else: proceed with scrum
```

**Midnight gate:** Special job that checks and auto-pauses/resumes the 3 scrum jobs.

## Covered Holidays

The algorithm covers these **national** (not state/regional) Malaysian holidays:

- Hari Raya Aidilfitri (1-2 Syawal)
- Hari Raya Aidiladha (10 Zulhijjah)
- Awal Muharram (1 Muharram)
- Maulidur Rasul (12 Rabiul Awwal)
- Nuzul Al-Quran (17 Ramadhan)
- Hari Merdeka (31 Aug)
- Malaysia Day (16 Sep)
- Labour Day (1 May)
- Agong's Birthday (first Monday of June)
- Deepavali (fixed by AMC)
- Thaipusam (fixed by AMC — KL-specific)
- Wesak Day (fixed by AMC)
- Christmas (25 Dec)
- Chinese New Year (1-2 Muharram-adjusted)

> **Note:** Islamic holidays shift ~10-11 days earlier each Gregorian year. The offline algorithm computes Hijri dates dynamically — no hardcoded dates.

## Edge Cases

- **Friday holiday → jobs resume Monday:** Cron schedule `1-5` naturally handles weekends
- **Multiple consecutive holidays:** Gate fires each day and pauses
- **State holidays (regional):** Only "National Holiday" types pause the scrum. Regional holidays (e.g., Sabah-only) do NOT pause