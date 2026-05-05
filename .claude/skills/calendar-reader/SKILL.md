---
name: calendar-reader
description: Formats Google Calendar event data into natural, conversational language. Use when converting raw calendar API responses into human-friendly summaries for voice or text output.
---

When formatting calendar data:

1. Use natural time references:
   - "Today at 3:00 PM" not "2026-05-05T15:00:00"
   - "Tomorrow morning" for next-day AM events
   - "This Friday" for events within the week

2. Format event summaries like this:
   "Here's your schedule for today, [weekday] [date]:
   • [time]: [event title] ([location if present])
   • [time]: [event title]
   Free blocks: [mention gaps over 1 hour]"

3. If no events: "Your calendar is clear for [period]."

4. For week views, group by day.

5. Always mention conflicts if creating a new event overlaps existing ones.

Keep tone friendly and conversational, as if spoken aloud.