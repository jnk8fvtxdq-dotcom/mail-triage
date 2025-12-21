# MailTriage Project - Status Document

## Project Overview
Automated email classification system that:
1. Monitors Apple Mail for new emails
2. Uses Claude API (Sonnet) to classify emails
3. Creates summaries in Apple Notes (Mail folder)

## Current Status: COMPLETE ✅

---

## Categories

| Category | Description | Note Created |
|----------|-------------|--------------|
| **Action** | Emails requiring response (personal, SBP project) | "Action" note |
| **Information** | Status updates, quality news | "Information" note |
| **Ignore** | Everything else (60% of emails) | No note |

---

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Python classifier | `/Users/eaub/Claude Code/MailTriage/classifier.py` | Main classification logic |
| Config (ALL rules) | `/Users/eaub/Claude Code/MailTriage/projects.txt` | Keywords, rules, examples |
| API key | `/Users/eaub/Claude Code/MailTriage/.env` | `ANTHROPIC_API_KEY=sk-ant-...` |
| Logs | `/Users/eaub/Claude Code/MailTriage/logs/triage.log` | Classification history |
| Cache | `/Users/eaub/Claude Code/MailTriage/cache/` | Temp email files |
| AppleScript source | `/Users/eaub/Claude Code/MailTriage/script_to_copy.txt` | Mail rule script |
| Compiled AppleScript | `~/Library/Application Scripts/com.apple.mail/email_triage.scpt` | Active script |

---

## Configuration File Structure (projects.txt)

```
[ACTION_KEYWORDS]
swissport, aspire, lounge, millar, Jagtar, David, fmorier, franbort, sbp, priority pass

[ACTION]
- Personal email from known contact
- Subject contains "Re:" or "RE:"
- Email from @ehl.ch domain
...

[INFORMATION]
- Confirmation of user-initiated action
- Quality news from Reuters, L'Agefi
...

[IGNORE]
- ALL emails from @linkedin.com
- Promotional emails with emojis
- Review/feedback requests
...

[DOMAINS]
IGNORE: linkedin.com, marketing.easyjet.com, operational.easyjet.com
INFORMATION: thomsonreuters.com, agefi.com
ACTION: ehl.ch

[EXAMPLES]
(10 few-shot examples for classification accuracy)

[RULES]
- When in doubt, choose IGNORE
- ALL LinkedIn emails are IGNORE
...
```

---

## How It Works

```
1. Email arrives in Mail.app
       ↓
2. Mail Rule triggers email_triage.scpt
       ↓
3. AppleScript extracts email data → saves to temp JSON
       ↓
4. AppleScript calls: python3 classifier.py temp_file.json
       ↓
5. Python checks domain rules (instant IGNORE for LinkedIn, etc.)
       ↓
6. Python loads config from projects.txt (keywords, criteria, examples)
       ↓
7. Python sends email + few-shot examples to Claude Sonnet API
       ↓
8. Claude responds: "action" or "information" or "ignore"
       ↓
9. AppleScript updates Notes (or ignores)
       ↓
10. Note entry format: "date - sender" + newline + "summary"
```

---

## Key Technical Details

### Python Path
```
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
```

### Required Libraries
```bash
pip3 install anthropic python-dotenv
```

### .env File Format (CRITICAL)
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```
**Must have `ANTHROPIC_API_KEY=` prefix!**

### JSON Output Format (compact, no spaces)
```json
{"action":"action","summary":"Brief summary","date":"07.12.2025","sender":"name@email.com"}
```

---

## Recompile AppleScript (after changes)

1. Open **Script Editor**
2. Open `/Users/eaub/Claude Code/MailTriage/script_to_copy.txt`
3. Select all (Cmd+A) → Copy (Cmd+C)
4. New document → Paste (Cmd+V)
5. Compile: **Cmd+K**
6. Save As (Cmd+Shift+S):
   - Press Cmd+Shift+G
   - Paste: `~/Library/Application Scripts/com.apple.mail/`
   - Name: `email_triage`
   - Format: **Script**
   - Click Replace

---

## Troubleshooting

### Check logs
```bash
tail -20 "/Users/eaub/Claude Code/MailTriage/logs/triage.log"
```

### Test classification manually
```bash
echo '{"subject":"Test","sender":"test@test.com","date":"07.12.2025","content":"Test content"}' > /tmp/test.json
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 "/Users/eaub/Claude Code/MailTriage/classifier.py" /tmp/test.json
```

### Clear cache
```bash
rm -f "/Users/eaub/Claude Code/MailTriage/cache/"*.json
```

### Clear logs
```bash
> "/Users/eaub/Claude Code/MailTriage/logs/triage.log"
```

### Stop running scripts
```bash
killall osascript
```

---

## Classification Analysis (from 30 labeled emails)

### Distribution
- **Ignore**: 60% (LinkedIn, promos, reviews, reminders)
- **Information**: 33% (confirmations, news, refunds)
- **Action**: 7% (personal emails, SBP project)

### Domain Rules (instant, no API call)
- `@linkedin.com` → IGNORE (any subdomain)
- `@marketing.easyjet.com` → IGNORE
- `@operational.easyjet.com` → IGNORE
- `@ehl.ch` → ACTION
- `@thomsonreuters.com` → INFORMATION
- `@agefi.com` → INFORMATION

### Few-shot Examples (10 total)
- 2 ACTION examples
- 4 INFORMATION examples
- 4 IGNORE examples

---

## Cost Estimate
- Model: Claude Sonnet 4
- ~$0.003 per email classification
- Domain rules skip API call (free for LinkedIn, etc.)

---

## Notes App Structure

```
Notes App
└── Mail (folder)
    ├── Action (emails needing response)
    │   └── "07.12.2025 - sender@email.com"
    │       "Summary of the email"
    │
    └── Information (status updates + news)
        └── "07.12.2025 - sender@email.com"
            "Summary of the email"
```

---

## Last Updated
2025-12-07 19:45
