#!/usr/bin/env python3
"""Email Triage Classifier - Few-shot learning with examples"""

import sys
import json
import os
import re
import logging
from pathlib import Path
from datetime import datetime

# Path detection
SCRIPT_DIR = Path(__file__).parent.resolve()
if not (SCRIPT_DIR / ".env").exists():
    SCRIPT_DIR = Path.home() / "Claude Code" / "MailTriage"

CONFIG_PATH = SCRIPT_DIR / "projects.txt"
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "triage.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    import anthropic
    from dotenv import load_dotenv
except ImportError as e:
    logging.error(f"Missing library: {e}")
    print(json.dumps({"action": "ignore"}, separators=(',', ':')))
    sys.exit(1)

load_dotenv(SCRIPT_DIR / ".env")


def load_config():
    """Load all configuration including examples from projects.txt"""
    config = {
        'action_keywords': [],
        'action': [],
        'information': [],
        'ignore': [],
        'domains': {'ignore': [], 'information': [], 'action': []},
        'examples': [],
        'rules': []
    }

    if not CONFIG_PATH.exists():
        return config

    current_section = None
    current_example = []

    for line in CONFIG_PATH.read_text(encoding='utf-8').splitlines():
        line_stripped = line.strip()

        # Skip empty lines and comments outside sections
        if not line_stripped:
            if current_section == 'examples' and current_example:
                config['examples'].append('\n'.join(current_example))
                current_example = []
            continue
        if line_stripped.startswith('# ==='):
            continue
        if line_stripped.startswith('#') and current_section not in ['examples']:
            continue

        # Detect section headers
        if line_stripped == '[ACTION_KEYWORDS]':
            current_section = 'action_keywords'
            continue
        elif line_stripped == '[ACTION]':
            current_section = 'action'
            continue
        elif line_stripped == '[INFORMATION]':
            current_section = 'information'
            continue
        elif line_stripped == '[IGNORE]':
            current_section = 'ignore'
            continue
        elif line_stripped == '[DOMAINS]':
            current_section = 'domains'
            continue
        elif line_stripped == '[EXAMPLES]':
            current_section = 'examples'
            continue
        elif line_stripped == '[RULES]':
            current_section = 'rules'
            continue

        # Parse content based on section
        if current_section == 'action_keywords':
            config['action_keywords'] = [k.strip().lower() for k in line_stripped.split(',')]
        elif current_section == 'action' and line_stripped.startswith('- '):
            config['action'].append(line_stripped[2:])
        elif current_section == 'information' and line_stripped.startswith('- '):
            config['information'].append(line_stripped[2:])
        elif current_section == 'ignore' and line_stripped.startswith('- '):
            config['ignore'].append(line_stripped[2:])
        elif current_section == 'domains':
            if line_stripped.startswith('IGNORE:'):
                config['domains']['ignore'] = [d.strip() for d in line_stripped[7:].split(',')]
            elif line_stripped.startswith('INFORMATION:'):
                config['domains']['information'] = [d.strip() for d in line_stripped[12:].split(',')]
            elif line_stripped.startswith('ACTION:'):
                config['domains']['action'] = [d.strip() for d in line_stripped[7:].split(',')]
        elif current_section == 'examples':
            if line_stripped.startswith('EXAMPLE_') or line_stripped.startswith('## '):
                if current_example:
                    config['examples'].append('\n'.join(current_example))
                    current_example = []
                if line_stripped.startswith('EXAMPLE_'):
                    current_example = []
            elif line_stripped.startswith('From:') or line_stripped.startswith('Subject:') or \
                 line_stripped.startswith('Classification:') or line_stripped.startswith('Reason:'):
                current_example.append(line_stripped)
        elif current_section == 'rules' and line_stripped.startswith('- '):
            config['rules'].append(line_stripped[2:])

    # Add last example if exists
    if current_example:
        config['examples'].append('\n'.join(current_example))

    logging.info(f"Loaded config: {len(config['action_keywords'])} keywords, {len(config['examples'])} examples")
    return config


def extract_latest_reply(content):
    """Extract only the latest reply, removing quoted previous messages."""
    if not content:
        return content

    lines = content.split('\n')
    result_lines = []

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Stop at quoted reply indicators
        # Outlook style: "From: ... Sent: ..."
        if line_lower.startswith('from:') and i > 0:
            # Check if next lines have "Sent:" or "Date:" - indicates quoted reply
            next_lines = '\n'.join(lines[i:i+5]).lower()
            if 'sent:' in next_lines or 'date:' in next_lines or 'to:' in next_lines:
                break

        # Gmail/Apple style: "On [date], [person] wrote:"
        if re.match(r'^on .+wrote:?\s*$', line_lower):
            break

        # French style: "Le [date], [person] a écrit :"
        if re.match(r'^le .+a écrit\s*:?\s*$', line_lower):
            break

        # Separator lines
        if re.match(r'^[-_]{5,}\s*$', line.strip()):
            break

        # Quoted lines (but allow some at start for formatting)
        if line.strip().startswith('>') and i > 3:
            break

        result_lines.append(line)

    result = '\n'.join(result_lines).strip()

    # If we got very little content, return original (truncated)
    if len(result) < 50 and len(content) > 50:
        return content[:500]

    return result


def extract_json(text):
    """Extract JSON from response."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r'\{[^{}]*"action"[^{}]*\}', text)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No valid JSON found")


def check_domain_rules(sender, domains):
    """Check if sender matches any domain rules."""
    sender_lower = sender.lower()
    for domain in domains.get('ignore', []):
        if domain in sender_lower:
            return 'ignore'
    for domain in domains.get('action', []):
        if domain in sender_lower:
            return 'action'
    for domain in domains.get('information', []):
        if domain in sender_lower:
            return 'information'
    return None


def classify(email_data, config):
    """Classify email using Claude Sonnet with few-shot examples."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logging.error("ANTHROPIC_API_KEY not set")
        return {"action": "ignore"}

    sender = email_data.get('sender', '')

    message_id = email_data.get('messageId', '')

    # Check domain rules first (hard rules)
    domain_match = check_domain_rules(sender, config['domains'])
    if domain_match == 'ignore':
        logging.info(f"'{email_data.get('subject', '')[:30]}' -> ignore (domain rule)")
        subject = email_data.get('subject', 'No subject')[:50]
        return {"action": "ignore", "summary": subject, "date": email_data.get('date', ''), "sender": sender[:50], "messageId": message_id}

    # Build prompt sections
    action_criteria = '\n'.join(f"   - {item}" for item in config['action'])
    info_criteria = '\n'.join(f"   - {item}" for item in config['information'])
    ignore_criteria = '\n'.join(f"   - {item}" for item in config['ignore'])
    rules = '\n'.join(f"- {rule}" for rule in config['rules'])
    keywords = ', '.join(config['action_keywords'][:10])  # Limit keywords shown

    # Build examples section
    examples_text = ""
    for ex in config['examples'][:8]:  # Use up to 8 examples
        examples_text += f"\n{ex}\n"

    prompt = f"""You are an email classifier. Classify this email into exactly ONE category.

## CATEGORIES

1. **ACTION** - Emails requiring response or attention:
{action_criteria}
   Action keywords: {keywords}

2. **INFORMATION** - Worth noting but no response needed:
{info_criteria}

3. **IGNORE** - Do not save (most emails):
{ignore_criteria}

## CLASSIFICATION EXAMPLES
{examples_text}

## RULES
{rules}

## EMAIL TO CLASSIFY

From: {sender}
Subject: {email_data.get('subject', 'No subject')}
Content: {extract_latest_reply(email_data.get('content', ''))[:1000]}

## RESPONSE

Return ONLY valid JSON (no markdown, no explanation):
{{"action":"action","summary":"Brief 10-word summary"}}
{{"action":"information","summary":"Brief 10-word summary"}}
{{"action":"ignore","summary":"Brief 10-word summary"}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        result = extract_json(response.content[0].text)

        # Validate action
        action = result.get('action', 'ignore')
        if action not in ('action', 'information', 'ignore'):
            action = 'ignore'

        # Add metadata
        result['action'] = action
        result['date'] = email_data.get('date', datetime.now().strftime('%d.%m.%Y'))
        result['sender'] = sender[:50]
        result['messageId'] = message_id

        logging.info(f"'{email_data.get('subject', '')[:30]}' -> {action}")
        return result

    except Exception as e:
        logging.error(f"Classification failed: {e}")
        return {"action": "ignore"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"action": "ignore"}, separators=(',', ':')))
        sys.exit(1)

    try:
        email_data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    except Exception as e:
        logging.error(f"Read error: {e}")
        print(json.dumps({"action": "ignore"}, separators=(',', ':')))
        sys.exit(1)

    config = load_config()
    result = classify(email_data, config)
    print(json.dumps(result, separators=(',', ':')))


if __name__ == "__main__":
    main()
