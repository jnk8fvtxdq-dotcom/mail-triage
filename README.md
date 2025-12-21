# MailTriage

An intelligent email classification system that automatically categorizes incoming emails using Claude AI and saves summaries to Apple Notes.

## Overview

MailTriage monitors your Apple Mail inbox and uses AI to classify emails into three categories:
- **Action**: Emails requiring a response or follow-up
- **Information**: Useful updates worth noting
- **Ignore**: Marketing, spam, or low-priority messages

Classified emails are automatically summarized and saved to Apple Notes for easy reference.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  Apple Mail │────▶│  AppleScript │────▶│   Python    │────▶│ Apple Notes │
│  (trigger)  │     │  (extract)   │     │  (classify) │     │   (save)    │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Claude AI  │
                                        │  (analyze)  │
                                        └─────────────┘
```

## Features

- **Domain-based rules**: Instant classification for known domains (no API call needed)
- **Few-shot learning**: 10 example classifications for improved accuracy
- **Smart content extraction**: Removes quoted replies, focuses on new content
- **Thread deduplication**: Avoids re-processing emails within 24 hours
- **Configurable keywords**: Prioritize emails mentioning specific topics/projects

## Tech Stack

- **Python 3.14** - Core classification engine
- **Anthropic Claude API** (Sonnet 4) - AI-powered email analysis
- **AppleScript** - Mail.app and Notes.app integration
- **macOS Mail Rules** - Automatic triggering on new emails

## Setup

### Prerequisites
- macOS with Apple Mail and Notes apps
- Python 3.10+
- Anthropic API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mailtriage.git
   cd mailtriage
   ```

2. Install dependencies:
   ```bash
   pip install anthropic python-dotenv
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your Anthropic API key
   ```

4. Copy AppleScript to Mail scripts folder:
   ```bash
   cp script_to_copy.txt ~/Library/Application\ Scripts/com.apple.mail/email_triage.scpt
   ```

5. Configure Mail rule:
   - Open Mail → Settings → Rules
   - Create rule: "Every Message" → "Run AppleScript: email_triage"

## Configuration

Edit `projects.txt` to customize:
- **[ACTION_KEYWORDS]**: Terms that trigger action classification
- **[DOMAINS]**: Domain-specific rules (bypass AI analysis)
- **[EXAMPLES]**: Few-shot learning examples for better accuracy

## Project Structure

```
mailtriage/
├── classifier.py       # Main classification engine
├── projects.txt        # Configuration and rules
├── script_to_copy.txt  # AppleScript source
├── .env.example        # Environment template
└── README.md
```

## How It Works

1. New email arrives in Mail.app
2. Mail rule triggers AppleScript
3. AppleScript extracts email data to JSON
4. Python classifier checks domain rules (free, instant)
5. If no match, sends to Claude API for analysis
6. Classification returned: action/information/ignore
7. Summary saved to appropriate Apple Note

## Cost Efficiency

- Domain rules bypass API calls entirely
- Content truncated to 1,000 chars for efficient API usage
- ~$0.003 per email classified via API
- Typical usage: 60% of emails classified by rules (free)

---

*Built to reclaim time spent on email triage.*
