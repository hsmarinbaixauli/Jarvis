---
name: intent-parser
description: Parses natural language voice commands into structured intents. Use when interpreting what the user wants from phrases like "what do I have today?", "cancel my meeting", "add a reminder", or any voice command directed at Jarvis.
---

When parsing user intent:

1. Identify the action type:
   - QUERY_CALENDAR → asking about events ("what do I have", "my schedule", "appointments")
   - CREATE_EVENT → creating something ("add", "schedule", "set a meeting", "remind me")
   - DELETE_EVENT → removing something ("cancel", "delete", "remove")
   - QUERY_TIME → asking about time or date ("what time", "what day")
   - UNKNOWN → anything else

2. Extract relevant entities:
   - Date/time references ("today", "tomorrow", "at 3pm", "next Monday")
   - Event titles or descriptions
   - Duration ("for 30 minutes", "one hour")
   - People mentioned

3. Return a structured summary:
   - Action: [type]
   - Entities: [extracted info]
   - Confidence: [high/medium/low]
   - Original phrase: [what the user said]

Keep responses concise and structured. If confidence is low, flag it clearly.