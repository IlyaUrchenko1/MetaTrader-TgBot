# MetaTrader 5 Connection
# MT5_TERMINAL_PATH = None # Path to the MetaTrader 5 terminal installation. If None, attempts to find it automatically.
# Add MT5 login credentials if needed, or manage them via the terminal UI / environment variables.
# MT5_LOGIN = 123456
# MT5_PASSWORD = "your_password"
# MT5_SERVER = "YourBroker-Server"

# Trading Parameters from TZ
SYMBOL = "EURUSD"  # Symbol for trading

INITIAL_LOT = 0.0  # Initial lot size. If 0, calculate based on BALANCE_PERCENT_FOR_LOT.
BALANCE_PERCENT_FOR_LOT = 1.0  # Percentage of balance for initial lot calculation (e.g., 1.0 = 1%). Only used if INITIAL_LOT is 0.

LOT_MULTIPLIER = 1.5  # K_Lot: Multiplier for subsequent orders in the grid

ORDER_DISTANCE_PIPS = 20  # Distance from current price for initial BuyStop/SellStop orders (in pips)

# TRAILING_STOP_START_PIPS = 0 # Not used according to refined logic
# TRAILING_STOP_DISTANCE_PIPS = 15 # Not used according to refined logic

MAX_DRAWDOWN_PERCENT = 20.0  # Maximum allowed drawdown percentage from the initial deposit before closing all positions/orders.

MAGIC_NUMBER = 12345  # Magic number to identify EA's orders and positions

# Other Settings
DEFAULT_DEVIATION = 10  # Default slippage/deviation in points for market order execution (not directly used by stop orders, but might be useful later)
RETRY_COUNT = 3         # Number of retries for failed operations (e.g., order placement)
RETRY_DELAY_SECONDS = 2 # Delay between retries in seconds
STATE_FILE = "state.json" # File to store the robot's state
LOG_FILE = "mt5_bot.log" # File for logging (if file logging is enabled in logger.py)
LOOP_DELAY_SECONDS = 5  # Delay in seconds for the main loop cycle