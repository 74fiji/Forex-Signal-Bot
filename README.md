# Forex Signal Bot (signals only)

A starter rules-based Forex alert bot for EUR/USD, GBP/USD and USD/JPY. It scans during weekdays 7:00 AM–5:00 PM America/New_York, using closed 15-minute candles for EMA 9/21 crossover + RSI confirmation and a closed 1-hour EMA trend filter. It sends Telegram alerts only; it cannot place trades.

## Free services
- Twelve Data Basic API key
- Telegram bot from @BotFather
- GitHub Actions (public repository standard hosted runners)

## GitHub setup
1. Create a GitHub repository and upload all files in this folder, including `.github/workflows/scan.yml`.
2. In the repository, open Settings → Secrets and variables → Actions → New repository secret.
3. Add `TWELVE_DATA_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`.
4. Open Actions and enable workflows if prompted. Run “Forex signal scan” manually once to test.
5. Scheduled scans run every 15 minutes on weekdays. GitHub scheduled runs can be delayed; this is not a guaranteed real-time service.

## Telegram setup
1. Message @BotFather, send `/newbot`, and save the token privately.
2. Open your new bot and press Start.
3. Visit `https://api.telegram.org/botYOUR_TOKEN/getUpdates` in your browser and find `message.chat.id` in the response. Replace YOUR_TOKEN locally; never share the URL or token. If getUpdates is empty, send another message to your bot and refresh.
4. Store that numeric ID as `TELEGRAM_CHAT_ID` in GitHub Secrets.

## Test
Use the GitHub Actions “Run workflow” button. The test scan runs the strategy. To send a connection test, temporarily change the workflow run command to `python main.py --test`, run it once, then change it back to `python main.py`.

## Strategy and risk notes
This is a transparent technical-rule strategy, not machine-learning AI and not a proven profitable system. EMA crossovers lag and can produce false signals. ATR stop/target levels are estimates; spreads, slippage, gaps, news and broker execution can change outcomes. It does not size positions. Paper-trade and backtest before risking money. Do not treat alerts as financial advice.

## Data limits
The Twelve Data Basic plan currently lists 800 API credits/day. This workflow requests two time-series endpoints per pair (six calls) per active scan, but usage can vary with provider credit weights. Monitor the provider dashboard and stop the workflow if you approach the quota.
