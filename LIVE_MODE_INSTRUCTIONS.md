# PokerBotV2 Live Mode Instructions

## Quick Start Guide

### 1. Run in Live Mode

To start the bot in live mode (capturing from actual poker table screen):

```bash
py poker_bot_v2.py live
```

### 2. Run in Test Mode (Default)

To run tests using example HTML files:

```bash
py poker_bot_v2.py
```

## Live Mode Requirements

### Before First Use:

1. **Calibrate UI positions** - You need to calibrate the HTML capture point first:

   ```bash
   py poker_bot.py calibrate
   ```

   This will help you set up the screen coordinates for capturing HTML from the poker table.

2. **Ensure poker table is visible** - The bot captures HTML directly from your screen, so the poker table must be visible and accessible.

## How Live Mode Works

When running in live mode (`py poker_bot_v2.py live`), the bot:

1. **🖥️ Captures HTML from screen** - Uses `UIController.get_html_from_screen_with_auto_retry()` to capture the current poker table HTML
2. **🧠 Parses game state** - Uses `PokerPageParser` to extract all relevant information (cards, pot, players, etc.)
3. **⚡ Makes optimal decisions** - Uses GPU-accelerated strategies and real-time CFR solving
4. **🎮 Executes actions** - Automatically clicks the appropriate buttons (fold, call, raise)

## Key Features in Live Mode

- **Real-time screen capture** - No file dependencies, captures live game state
- **GPU-accelerated decisions** - Uses the full strategy database and GPU equity calculator
- **Automatic retry logic** - If HTML capture fails, automatically retries with fallback strategies
- **Comprehensive logging** - All decisions and reasoning are logged to `poker_bot_v2.log`

## Safety Features

- **Press Ctrl+Q** to stop the bot at any time
- **Automatic validation** - Bot validates HTML content before making decisions
- **Error recovery** - If capture fails, bot waits and retries rather than making random decisions

## Verification

The bot is configured to ALWAYS use screen capture in live mode. There are no fallbacks to test files or static data - everything comes from the live poker table screen.

- ✅ Uses `UIController` for screen capture
- ✅ Uses `PokerPageParser` for HTML parsing
- ✅ Uses GPU-accelerated strategy database
- ✅ Uses real-time CFR solver for edge cases
- ✅ Logs all decisions with full context
