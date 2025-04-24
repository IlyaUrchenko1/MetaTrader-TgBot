# MetaTrader 5 Python Grid Bot

This project is a Python-based trading bot that interacts with the MetaTrader 5 (MT5) terminal. It implements a grid trading strategy using pending BuyStop and SellStop orders.

## Strategy Overview

The core logic follows these steps:

1.  **Initialization:** Place initial BuyStop and SellStop orders at a defined distance (in pips) from the current market price. The initial lot size can be fixed or calculated as a percentage of the account balance.
2.  **Trigger:** When one of the pending orders (e.g., BuyStop) is triggered and becomes a position:
    *   The opposite pending order (SellStop) is cancelled.
    *   A new opposite pending order (SellStop) is placed at the *original* SellStop price level, but with a lot size multiplied by a defined factor (`LOT_MULTIPLIER`).
3.  **Continuation:** This cycle repeats each time a new position is opened by a pending order triggering. The bot places a new, larger pending order on the opposite side at the original price level.
4.  **Drawdown Protection:** If the account equity drops below a certain percentage (`MAX_DRAWDOWN_PERCENT`) of the initial deposit (recorded when the strategy first initializes), the bot will:
    *   Attempt to close all open positions associated with its magic number.
    *   Attempt to cancel all pending orders associated with its magic number.
    *   Reset its internal state, effectively stopping the current grid cycle.

## Features

*   Connects to a running MetaTrader 5 terminal.
*   Calculates initial lot size based on fixed value or balance percentage.
*   Adjusts order distance based on broker's minimum requirements (`stops_level`).
*   Manages BuyStop/SellStop grid according to the strategy.
*   Increases lot size for subsequent orders using a multiplier.
*   Includes drawdown protection to limit potential losses.
*   Uses a Magic Number to distinguish its orders and positions.
*   Saves and loads its state (`state.json`) to maintain grid parameters across restarts.
*   Implements retry logic for sending orders.
*   Logs activities to both console (INFO level) and a file (`mt5_bot.log`, DEBUG level).

## Prerequisites

*   **MetaTrader 5 Terminal:** Installed and running with a logged-in account.
*   **Python:** Version 3.x recommended.
*   **MetaTrader5 Python Package:** `pip install MetaTrader5`
*   **Allow Algo Trading:** Ensure "Allow Algo Trading" is enabled in the MT5 terminal options AND for the specific chart/expert if running as an EA.

## Configuration

Key parameters are set in `utils/constants.py`:

*   `SYMBOL`: The trading symbol (e.g., "EURUSD").
*   `INITIAL_LOT`: Initial lot size. If 0, uses `BALANCE_PERCENT_FOR_LOT`.
*   `BALANCE_PERCENT_FOR_LOT`: Percentage of balance for initial lot calculation (used if `INITIAL_LOT` is 0).
*   `LOT_MULTIPLIER`: Multiplier for increasing lot size in the grid.
*   `ORDER_DISTANCE_PIPS`: Distance (in pips) from the current price for initial orders.
*   `MAX_DRAWDOWN_PERCENT`: Maximum allowed drawdown percentage before stop-out.
*   `MAGIC_NUMBER`: Unique identifier for the bot's trades.
*   `RETRY_COUNT`: Number of times to retry sending an order on failure.
*   `RETRY_DELAY_SECONDS`: Delay between order send retries.
*   `STATE_FILE`: Name of the file to store the bot's state.
*   `LOG_FILE`: Name of the log file.
*   `LOOP_DELAY_SECONDS`: Pause duration (in seconds) for the main loop.

## How to Run

1.  Ensure your MetaTrader 5 terminal is running and logged in.
2.  Configure the parameters in `utils/constants.py` as needed.
3.  Open a terminal or command prompt in the project's root directory.
4.  Run the main script: `python mt5_script.py`
5.  The bot will connect to MT5, initialize the strategy (if needed), and start monitoring and managing the grid.
6.  To stop the bot gracefully, press `Ctrl+C` in the terminal where it's running.

## State File (`state.json`)

This file stores important information for the bot to resume its state after a restart, including:

*   `initialized`: Whether the grid strategy has been initialized.
*   `initial_deposit`: Account equity recorded at the time of first initialization (used for drawdown calculation).
*   `initial_buy_stop_level` / `initial_sell_stop_level`: The price levels where the *next* BuyStop/SellStop should be placed (these get removed once the corresponding side triggers).
*   `last_placed_buy_lot` / `last_placed_sell_lot`: The volume of the most recently placed Buy/Sell order/position.
*   `next_buy_lot` / `next_sell_lot`: The calculated volume for the *next* Buy/Sell order to be placed.

**Important:** If you manually interfere with trades or want to start fresh, delete or clear the contents of `state.json` (`{}`).

## Disclaimer

Trading involves substantial risk. This bot is provided as-is, without warranty. Use it at your own risk, preferably on a demo account first. The authors are not responsible for any financial losses. 