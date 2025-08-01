# Issue #15: Simplified Calendar Integration with Meeting Table

## 🎯 **Problem Summary**
The current calendar system is overly complex with multiple tables and extensive metadata. Users want a simple, intuitive meeting scheduler that works like natural conversation: "Schedule a meeting for tomorrow at 9am" should just work and ask for basic details.

## 🔍 **Current System Analysis**
The existing calendar implementation (`modules/calendar/calendar_module.py`) has:

### Overcomplicated Structure:
- Two separate tables (`events` and `reminders`) 
- 13+ fields per event with complex metadata
- Heavy natural language parsing with limited accuracy
- Convoluted event creation workflow
- Complex recurring event logic that isn't needed for basic use

### User Experience Issues:
- Difficult to create simple meetings quickly
- No interactive follow-up for missing details
- Inconsistent date/time parsing
- No clear meeting type categorization
- Missing essential modern meeting fields (video links, etc.)

## 🎯 **Proposed Simplified Solution**

### New Database Schema - Single `meetings` Table:
```sql
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date DATE NOT NULL,           -- Just the date (YYYY-MM-DD)
    time TIME NOT NULL,           -- Just the time (HH:MM)
    meeting_type TEXT DEFAULT 'in_person', -- online, in_person, phone
    location TEXT,                 -- Physical location or video link
    duration INTEGER DEFAULT 60,  -- Duration in minutes
    reminder_minutes INTEGER DEFAULT 15,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Smart Workflow:
1. **Parse User Request**: "Schedule meeting tomorrow at 9am"
2. **Extract Basics**: Date (tomorrow), Time (9am), Title (meeting)  
3. **Ask Follow-ups**: "Is this online or in-person? Any specific location or meeting link?"
4. **Save & Confirm**: "✅ Meeting scheduled for [Date] at [Time]. You'll get a reminder 15 minutes before."

## 🚀 **Enhanced User Experience**

### Natural Language Examples:
- ✅ "Schedule meeting tomorrow at 9am" 
- ✅ "Book appointment Friday 2pm"
- ✅ "Add team standup Monday 10am online"
- ✅ "Create interview Thursday 3pm"

### Interactive Follow-up System:
```
User: "Schedule meeting tomorrow at 9am"
SAGE: "Great! I'll schedule a meeting for [Tomorrow's Date] at 9:00 AM. 
       Is this online or in-person?"
User: "Online"  
SAGE: "Perfect! Do you have a meeting link or should I note it as 'Online meeting'?"
User: "Use Zoom link: https://zoom.us/j/123456"
SAGE: "✅ Meeting scheduled for [Date] at 9:00 AM (Online - Zoom). 
       You'll get a reminder 15 minutes before."
```

## 🛠️ **Implementation Requirements**

### Phase 1: Database Restructuring
- [ ] Create new simplified `meetings` table
- [ ] Migrate existing events to new structure  
- [ ] Remove old `events` and `reminders` tables
- [ ] Add database indexes for performance

### Phase 2: Smart Date/Time Parsing
- [ ] Improve natural language date parsing
- [ ] Add support for relative dates ("tomorrow", "next Monday", "in 3 days")
- [ ] Better time format recognition (12hr/24hr, with/without AM/PM)
- [ ] Handle timezone context

### Phase 3: Interactive Workflow  
- [ ] Implement conversation state tracking
- [ ] Add follow-up question system
- [ ] Create context-aware response generation
- [ ] Add confirmation and editing capabilities

### Phase 4: Meeting Type Intelligence
- [ ] Auto-detect meeting types from keywords
- [ ] Smart default suggestions based on patterns
- [ ] Integration with common video platforms
- [ ] Location auto-complete for frequent venues

## 🧪 **Enhanced Intent Recognition**

### Better Keyword Matching:
```python
SCHEDULE_KEYWORDS = [
    # Direct scheduling
    'schedule', 'book', 'add', 'create', 'set up', 'plan',
    # Meeting types  
    'meeting', 'appointment', 'call', 'interview', 'standup',
    'demo', 'presentation', 'review', 'sync', 'catchup',
    # Time expressions
    'tomorrow', 'today', 'monday', 'tuesday', 'next week',
    'at', 'pm', 'am', 'o\'clock', 'in the morning', 'afternoon'
]

CALENDAR_QUERY_KEYWORDS = [
    # Checking schedule
    'do i have', 'any meetings', 'what\'s on my', 'schedule',
    'meetings today', 'meetings tomorrow', 'free time',
    'busy', 'available', 'calendar', 'agenda'
]
```

### Smarter Pattern Recognition:
- Understand context: "Schedule" vs "Do I have meetings"
- Extract meeting titles from natural speech
- Recognize urgency and priority indicators
- Handle multiple meetings in one request

## 🔧 **Code Structure Changes**

### New Files:
- `modules/calendar/meeting_manager.py` - Core meeting logic
- `modules/calendar/date_parser.py` - Enhanced date/time parsing  
- `modules/calendar/conversation_state.py` - Track follow-up questions
- `modules/calendar/meeting_types.py` - Meeting categorization

### Modified Files:
- `modules/calendar/calendar_module.py` - Simplified main module
- `modules/nlp/nlp_module.py` - Better calendar intent recognition
- `config.yaml` - New calendar configuration options

### Configuration Updates:
```yaml
calendar:
  default_duration: 60          # minutes
  default_reminder: 15          # minutes before  
  auto_follow_up: true          # Ask clarifying questions
  smart_suggestions: true       # Suggest meeting details
  
  meeting_types:
    online:
      default_location: "Online meeting"
      common_platforms: [zoom, teams, meet, webex]
    in_person:
      default_reminder: 30       # More time for travel
      suggest_location: true
      
  date_parsing:
    business_hours: [9, 17]      # 9am-5pm default
    weekend_meetings: false      # Warn about weekend scheduling
    timezone_detection: auto
```

## 📊 **Success Metrics**
- [ ] 90%+ accuracy in date/time parsing from natural language
- [ ] Sub-10 second meeting creation with follow-ups
- [ ] 95% user satisfaction with "just works" simplicity  
- [ ] Support for 20+ common meeting scheduling patterns
- [ ] Zero database corruption from simplified schema

## 🔄 **Migration Strategy**
1. **Backup existing calendar data**
2. **Create new meetings table alongside old tables**  
3. **Migrate existing events to new format**
4. **Test new system extensively**
5. **Switch over and remove old tables**
6. **Update all calendar-related code**

## 📈 **Priority: HIGH**
Calendar/scheduling is a core productivity feature. The current complexity creates user friction and reduces adoption. A simplified, conversational approach will significantly improve user experience.

---
**Labels:** `enhancement`, `calendar`, `user-experience`, `database`, `high-priority`