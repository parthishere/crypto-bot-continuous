import psycopg2, os
from os.path import join
import dotenv
from pathlib import Path
import logging


TYPE = 'AUTO_TRADE' # AUTO_TRADE and DEFAULT_AMOUNT
#AUTO_TRADE will caclulate according to volume24 
# DEFAULT_TRADE will take dfault amount as DEFAULT_TRADE_AMOUNT
DEBUG = True

BASE_DIR = Path(__file__).resolve().parent.parent
print(BASE_DIR)
dotenv_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)
    
# set secret_key and api_key in .env file
SECRET_KEY = os.environ['secret_key']
API_KEY = os.environ['api_key']
ASSETS = os.environ['assets'] or ["CTS/USDT"]

# "BTC", "ETH" etc.
ASSET = "CTS"
# "BTC/USDT", "ETH/USDT" etc 
MARKET = "CTS/USDT"

CONTINUOUS_TRADE = True

VOLUME24 = None     # Default target volume

TIME_DEALY_FOR_CONTINUOUS_TRADE = 10 # In Minites
DEFAULT_TRADE_AMOUNT = 10 # 10 CRYPTO EVERY 10 MINITES (TIME_DELAY_FOR_CONTINUOUS_TRADE) : BUY !!
DEFAULT_TRADE_TIME = 1 # Hours

def get_input_cdata():
    global VOLUME24, DEFAULT_TRADE_TIME
    try:
        conn = psycopg2.connect(database=os.environ['DATABASE_NAME'], user=os.environ['DATABASE_USER'], password=os.environ['DATABASE_PASSWORD'], host=os.environ["DATABASE_HOST"], port="5432")

        cur = conn.cursor()
        cur.execute("SELECT id, continuous_trade, volume24h, default_trade_time FROM app_continuousteademodel ORDER BY id")
        row = cur.fetchall().pop()
        print(row)
        if not (VOLUME24):
            if cur.rowcount == row[0]:
                print("ok ")
                CONTINUOUS_TRADE = row[1]
                VOLUME24 = float(round(row[2], 4))
                DEFAULT_TRADE_TIME = float(round(row[3], 4))
                if (VOLUME24 <= 0) or (not isinstance(VOLUME24, float) or not isinstance(CONTINUOUS_TRADE, bool)):
                    cur.execute("SELECT id, continuous_trade, volume24h, default_trade_time FROM app_continuousteademodel ORDER BY id")
                    row = cur.fetchall().pop(-2)
                    print("not ok")
                    CONTINUOUS_TRADE = float(round(row[1], 4))
                    VOLUME24 = float(round(row[2], 4))
                    DEFAULT_TRADE_TIME = float(round(row[3], 4))
            
            print(CONTINUOUS_TRADE, VOLUME24)
            
    except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    finally:
        if conn is not None:
            conn.close()
            
            
WATCHED_FILES = [join('continuous_trade', 'exchange_interface.py'), join('continuous_trade', 'hotbit.py'), join('continuous_trade', 'ordermanager.py'), join('continuous_trade' ,'settings.py'), 'main.py']

LOG_LEVEL = logging.INFO
ISFEE = 0
OFFSET = 0
LIMIT = 100
INTERVAL = 1

CHECK_POSITION_LIMITS = True
MAX_POSITION = 20000
MIN_POSITION = 0