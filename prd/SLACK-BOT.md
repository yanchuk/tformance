# Tformance Slack Bot Specification

> Part of [PRD Documentation](README.md)

## Bot Identity

- **Name:** Tformance Bot
- **Avatar:** Custom icon (TBD)
- **Presence:** Always online when service healthy

## Features (MVP)

| Feature | Description |
|---------|-------------|
| PR Survey | Ask author about AI assistance, ask reviewer for quality rating + AI guess |
| Reveal | Show if reviewer guessed correctly |
| Weekly Leaderboard | Post AI Detective rankings to channel |

## Commands

None for MVP - bot is notification/survey only, not command-driven.

---

## Message Templates

### PR Survey - Author

Triggered: When PR is merged (via GitHub webhook)

```
Hey {author_name}! 🎉

Your PR was just merged:
*{pr_title}*

Quick question: Was this PR AI-assisted?

[Yes] [No]
```

**Button Actions:**
- `Yes` → Record `author_ai_assisted = true`
- `No` → Record `author_ai_assisted = false`

**After response:**
```
Thanks! Your response has been recorded. 👍
```

---

### PR Survey - Reviewer

Triggered: When PR is merged (sent to all reviewers who approved)

```
Hey {reviewer_name}! 👀

You reviewed this PR that just merged:
*{pr_title}* by {author_name}

How would you rate the code quality?
[Could be better] [OK] [Super]

Bonus: Was this PR AI-assisted?
[Yes, I think so] [No, I don't think so]
```

**Button Actions:**
- Quality: `1` / `2` / `3`
- AI Guess: `true` / `false`

**After response:**
```
Thanks for your feedback!
```

---

### Reveal - Correct Guess

Triggered: After both author and reviewer respond (if reviewer guessed correctly)

```
🎯 Nice detective work, {reviewer_name}!

You guessed correctly - this PR *was* AI-assisted.

Your accuracy: {correct}/{total} ({percentage}%)
```

or

```
🎯 Nice detective work, {reviewer_name}!

You guessed correctly - this PR *wasn't* AI-assisted.

Your accuracy: {correct}/{total} ({percentage}%)
```

---

### Reveal - Wrong Guess

Triggered: After both author and reviewer respond (if reviewer guessed wrong)

```
🤔 Interesting, {reviewer_name}!

This PR was actually *AI-assisted*.

Your accuracy: {correct}/{total} ({percentage}%)

AI is getting sneaky! 🤖
```

or

```
🤔 Interesting, {reviewer_name}!

This PR was actually *not AI-assisted*.

Your accuracy: {correct}/{total} ({percentage}%)

Humans can still surprise you! 👨‍💻
```

---

### Weekly Leaderboard

Triggered: Scheduled (configurable day/time)

Posted to: Configured channel (e.g., #engineering)

```
🏆 *AI Detective Leaderboard* (Week of {date_range})

*Top Guessers:*
1. {name} - {correct}/{total} ({percentage}%)
2. {name} - {correct}/{total} ({percentage}%)
3. {name} - {correct}/{total} ({percentage}%)

📊 *Team Stats This Week:*
• {prs_merged} PRs merged
• {ai_percentage}% were AI-assisted
• Reviewer detection rate: {detection_rate}%
• Average quality rating: {avg_rating}/3

🔥 *Quality Champions:*
• {name} - {super_count} "Super" ratings received
• {name} - Fastest avg review time ({hours} hrs)

Keep up the great work! 💪
```

**Edge cases:**
- If <3 participants with guesses, show all available
- If no PRs merged, post abbreviated version
- If team has <5 members, adjust to avoid identifying individuals

---

## Configuration Options

Set during onboarding, editable in settings.

| Setting | Options | Default |
|---------|---------|---------|
| Survey delivery | DM only | DM |
| Leaderboard channel | Any public channel | #engineering |
| Leaderboard day | Monday-Sunday | Monday |
| Leaderboard time | HH:MM | 09:00 |
| Timezone | Client's timezone | Auto-detect |
| Enable reveals | Yes/No | Yes |
| Enable leaderboard | Yes/No | Yes |

---

## Technical Implementation

### Slack App Manifest (partial)

```yaml
display_information:
  name: Tformance
  description: AI Impact Analytics for Engineering Teams

features:
  bot_user:
    display_name: Tformance Bot
    always_online: true

oauth_config:
  scopes:
    bot:
      - chat:write
      - users:read
      - users:read.email

settings:
  interactivity:
    is_enabled: true
    request_url: https://api.ourservice.com/slack/interactions
```

### Interaction Payload Handling

```
POST /slack/interactions
Content-Type: application/x-www-form-urlencoded

payload={
  "type": "block_actions",
  "user": {"id": "U123"},
  "actions": [{"action_id": "ai_assisted_yes", "value": "true"}],
  "response_url": "https://hooks.slack.com/..."
}
```

### Rate Limits

- Slack allows ~1 message/second per workspace
- For large PRs with many reviewers, queue messages
- Leaderboard is single message, no concern

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| User not in Slack | Skip silently, log for admin |
| Slack API error | Retry 3x with backoff, then log |
| User responds twice | Ignore subsequent responses |
| PR has no reviewers | Only send author survey |
| Author = Reviewer (self-merge) | Send combined survey |
