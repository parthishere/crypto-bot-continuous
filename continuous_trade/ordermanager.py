import datetime, sys, math, random
from continuous_trade import settings
from .exchange_interface import ExchangeInterface
    
from os.path import getmtime
import logging
from time import sleep


import os
watched_files_mtimes = [(f, getmtime(f)) for f in settings.WATCHED_FILES]

logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

class OrderManager:
    def __init__(self):
        self.exchange = ExchangeInterface()
        # Once exchange is created, register exit handler that will always cancel orders
        # on any error.
        settings.get_input_cdata()
        logging.info("Using symbol %s." % self.exchange.symbol)

        logging.info("Order Manager initializing, connecting to BitMEX. Live run: executing real trades.")
        if settings.DEBUG:
            logging.info("Initializing dry run. Orders printed below represent what would be posted to Hotbit.")
        else:
            logging.info("Order Manager initializing, connecting to Hotbit. Live run: executing real trades.")

        self.starting_qty = float(self.exchange.get_delta())
        self.running_qty = float(self.starting_qty)
        
        self.get_lowest_sell = self.exchange.get_lowest_sell()
        self.get_highest_buy = self.exchange.get_highest_buy()

        self.volume24 = settings.VOLUME24
        self.first = True
        self.reset()

    def reset(self):
        self.exchange.cancel_all_orders()
        self.print_status()

        # Create orders and converge.
        self.place_orders()

    def print_status(self):
        """Print the current MM status."""

        self.running_qty = float(self.exchange.get_delta())
        logging.info("current 24h Volume: %f", self.exchange.get_24h_volume())
        logging.info("Targeted 24h Volume: %f" % settings.VOLUME24)

        logging.info("Delta : %s" % str(self.exchange.get_delta()))
        logging.info("Position in CTS: %s" % str(self.exchange.get_position()))
       
        logging.info("Contracts Traded This Run: %d" % (self.running_qty - self.starting_qty))
        # hard coded
        logging.info("Pending orders : %s" % str(self.exchange.get_pending_orders().get('result').get("CTSUSDT").get('records')))
        
        logging.info("Current Crypto Price: %f" %self.exchange.get_crypto_price())
        
        

    def get_price_offset(self, index, order_pairs):
        """Given an index (1, -1, 2, -2, etc.) return the price for that side of the book.
           Negative is a buy, positive is a sell."""
        # Maintain existing spreads for max profit
        ############### CHECK THIS OUT ###############
        prices = []
        
        if index == 1:
            pass
        else:
            # buy
            for i in range(0, order_pairs):
                prices.append(self.recent_price)

        print(prices)
        return prices

    ###
    # Orders
    ###

    def place_orders(self):
        """Create order items for use in convergence."""
        
        buy_orders = []

        self.recent_price = recent_value = self.exchange.get_crypto_price()
        
        recent_buy_orders = self.exchange.get_recent_order_bids()['result']['orders']
        recent_sell_orders = self.exchange.get_recent_order_sells()['result']['orders']
        bid_amount = 0
        sell_amount = 0
        buy_orders = None
                 
        for result in recent_buy_orders:
            if result['side'] == 2:    # 2 for buy
                bid_amount += float(result['amount'])
        for result in recent_sell_orders:
            if result['side'] == 1:
                sell_amount += float(result['amount'])

        logging.info("bid amount = %d , sell amount = %d",bid_amount ,sell_amount)
        current_volume_24h = float(self.exchange.get_24h_volume())
        if settings.VOLUME24 >= current_volume_24h or settings.TYPE == 'DEFAULT_AMOUNT':
            print("Current volume is less than target volume..")
            if settings.CONTINUOUS_TRADE and not settings.TYPE == 'DEFAULT_AMOUNT':
                # it will buy little bit amount of crypto as time goes
                h = datetime.datetime.utcnow().hour
                m = datetime.datetime.utcnow().minute 
                s = datetime.datetime.utcnow().second
                remaining_time = (24.00 - (h + m/60 + s/3600)) # in hour
                
                DEFAULT_TRADE_AMOUNT = ((settings.VOLUME24-current_volume_24h)*settings.TIME_DEALY_FOR_CONTINUOUS_TRADE) / (remaining_time * 60) # volume per time_delay_for_continuous_trade mins
                
                index = 2 # 2 for buying
                buy_orders =  self.prepare_continuous_order(index, amount=DEFAULT_TRADE_AMOUNT)
                logging.info("Placing orders with amount %f per %f minutes" % (DEFAULT_TRADE_AMOUNT, settings.TIME_DEALY_FOR_CONTINUOUS_TRADE))
                if self.first == True:
                    logging.info("Total liquidity will necessesary(nearly): %f" % ((settings.VOLUME24 - current_volume_24h)*self.recent_price))
                    var = input("Input *Yes* to continue: ")
                    if var == "Yes":
                        self.first = False
                        return self.converge_orders(buy_orders, None)  

                else:
                    return self.converge_orders(buy_orders, None)
            else:
                index = 2
            
                buy_orders =  self.prepare_continuous_order(index, amount=settings.DEFAULT_TRADE_AMOUNT)
                logging.info("Placing orders with amount %f per %f minutes" % (settings.DEFAULT_TRADE_AMOUNT, settings.TIME_DEALY_FOR_CONTINUOUS_TRADE))
                if self.first == True:
                    logging.info("Total liquidity will necessesary(nearly): %f" % ((settings.VOLUME24 - current_volume_24h)*self.recent_price))
                    var = input("Input *Yes* to continue: ")
                    if var == "Yes":
                        self.first = False
                        return self.converge_orders(buy_orders, None)  

                else:
                    return self.converge_orders(buy_orders, None)



    def prepare_continuous_order(self, index, amount):
        orderQty = amount
        prices = self.get_price_offset(index, 1)
        orders = []
        position = prices[0] * orderQty   
        
        for i in range(0, 1):
            orders.append({'price': str(prices[i]), 'amount': str(abs(orderQty)), 'side': index})
            
        if index is 1:
            logging.info("\nContract that will be traded in this run : %s USDT, Current position: %s " % (str(position), str(self.exchange.get_position())))
            logging.info("\nCTS that will be sold this trade: %s" % str(orderQty))
        else:
            logging.info("\nContract that will be traded in this run : %s USDT, Current position: %s " % (str(position), str(self.exchange.get_position())))
            logging.info("\nCTS that will be bought this trade: %s" % str(orderQty))
            if self.check_usdt(position):
                logging.error("Not enough Balance, Resetting bot")
                # self.reset()
        print(orders)
        return orders 



    def converge_orders(self, buy_orders, sell_orders):
        """Converge the orders we currently have in the book with what we want to be in the book.
           This involves amending any open orders and creating new ones if any have filled completely.
           We start from the closest orders outward."""

        # tickLog = self.exchange.get_instrument()['tickLog']
        to_amend = []
        to_create = []
        to_cancel = []
        buys_matched = 0
        sells_matched = 0
        existing_user_orders = []
        try:
            existing_user_orders = self.exchange.get_pending_orders().get('result').get(self.exchange.symbol).get('records')
        except:
            pass
        


        # Check all existing orders and match them up with what we want to place.
        # If there's an open one, we might be able to amend it to fit what we want.
        if existing_user_orders:
            desired_order = None
            for order in existing_user_orders:
                
                
                if order['side'] == 1:   # 1-Seller，2-buyer
                    # for seller
                    if sell_orders:
                        desired_order = sell_orders[sells_matched]
                        sells_matched +=1
                    else:
                        logging.info("previously sell orders were placed now buy orders are being placed")
                        
                else:   # 1-Seller，2-buyer
                    # for buyer
                    if buy_orders:
                        desired_order = buy_orders[sells_matched]
                        buys_matched +=1
                    else:
                        logging.info("previously sell orders were placed now buy orders are being placed")
                        
                if desired_order['amount'] != order['left'] or (abs((float(desired_order['price']) / float(order['price'])) - 1) > settings.RELIST_INTERVAL):
                    to_amend.append({'id': order['id'], 'amount': str(order['left'] + desired_order['amount']),
                                        'price': str(desired_order['price']), 'side': order['side']})
                    
                    to_cancel.append(order)
                    logging.info("Amending the value of previous order")
        
        if buy_orders:
            while buys_matched < len(buy_orders):
                to_create.append(buy_orders[buys_matched])
                buys_matched += 1
        else:
            while sells_matched < len(sell_orders):
                to_create.append(sell_orders[sells_matched])
                sells_matched += 1

        print("to:create="+str(to_create))
        if to_create:
            logging.info("Creating %d orders:" % (len(to_create)))
            for order in reversed(to_create):
                logging.info("side = %d , amount =%s @ %s$" % (order['side'], order['amount'], order['price']))
            if settings.DEBUG:
                var = str(input("input 'Yes' for further process :"))
                if var == "Yes":
                    self.exchange.create_bulk_orders(to_create)
                else:
                    logging.info("cancelling order side = %s, amount = %s @ %s$" % (order['side'], order['amount'], order['price']))
            else:
                self.exchange.create_bulk_orders(to_create)
                

        # Could happen if we exceed a delta limit
        if len(to_cancel) > 0:
            logging.info("Canceling %d orders:" % (len(to_cancel)))
            for order in reversed(to_cancel):
                logging.info("id = %d side = %d amount = %s @ %s$" % (order['id'], order['side'], order['amount'], order['price']))
            if settings.DEBUG:
                var = str(input("input 'Yes' for further process :"))
                if var == "Yes":
                        response = self.exchange.cancel_bulk_orders(to_cancel)
                else:
                    logging.info("cancelling cancel order side = %s amount = %s @ %s$" % (order['side'], order['amount'], order['price']))
            else:
                self.exchange.cancel_bulk_orders(to_cancel)


    ###
    # Position Limits
    ###

    def short_position_limit_exceeded(self):
        """Returns True if the short position limit is exceeded"""
        if not settings.CHECK_POSITION_LIMITS:
            return False
        position = float(self.exchange.get_delta())
        return position <= settings.MIN_POSITION

    def long_position_limit_exceeded(self):
        """Returns True if the long position limit is exceeded"""
        if not settings.CHECK_POSITION_LIMITS:
            return False
        position = float(self.exchange.get_delta())
        return position >= settings.MAX_POSITION
    
    def check_usdt(self, price):
        position = float(self.exchange.get_position()['USDT']['available'])
        if price > position:
            return True
        return False
    
    def check_day_is_changed(self):
        initial_time = self

    ###
    # Sanity
    ##

    def perform_check(self):
        """Perform checks before placing orders."""


        if self.long_position_limit_exceeded():
            logging.warning("Long delta limit exceeded")
            logging.warning("Current Position: %.f, Maximum Position: %.f" %
                        (self.exchange.get_delta(), settings.MAX_POSITION))
            self.exit()

        if self.short_position_limit_exceeded():
            logging.warning("Short delta limit exceeded")
            logging.warning("Current Position: %.f, Minimum Position: %.f" %
                        (self.exchange.get_delta(), settings.MIN_POSITION))
            self.exit()
        
        if self.exchange.get_pending_orders().get('result').get('CTSUSDT').get('records') is not None:
            if len(self.exchange.get_pending_orders().get('result').get('CTSUSDT').get('records')) > settings.MAX_PENDING_ORDERS:
                logging.warning("Pending Order limit exceeded")

    ###########
    # Running #
    ###########

    def check_file_change(self):
        """Restart if any files we're watching have changed."""
        for f, mtime in watched_files_mtimes:
            if getmtime(f) > mtime:
                self.restart()


    def exit(self):
        logging.info("Shutting down. All open orders will be cancelled.")
        try:
            self.exchange.cancel_all_orders()
            # self.exchange.hotbit.exit()
        except AuthenticationError as e:
            logging.info("Was not authenticated; could not cancel orders.")
        except Exception as e:
            logging.info("Unable to cancel orders: %s" % e)

        sys.exit()

    def run_loop(self):
        while True:
            sys.stdout.write("-----\n")
            sys.stdout.flush()
            settings.get_input_cdata()
            self.check_file_change()
            
            # sleep for LOOP INTERVAL seconds
            sleep(settings.TIME_DEALY_FOR_CONTINUOUS_TRADE)

            # This will restart on very short downtime, but if it's longer,
            # the MM will crash entirely as it is unable to connect to the WS on boot.
            if not self.check_connection():
                logging.error("Realtime data connection unexpectedly closed, restarting.")
                self.restart()

            self.perform_check()  # Ensures health of mm - several cut-out points here
            self.print_status()  # Print delta, etc
            self.place_orders()  # Creates desired orders and converges to existing orders

    def restart(self):
        logging.info("Restarting the market maker...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        
    def check_connection(self):
        return True if self.exchange.get_delta() else False




def run():
    logging.info('HotBit Market Maker')

    ordermanager = OrderManager()
    # Try/except just keeps ctrl-c from printing an ugly stacktrace
    try:
        ordermanager.run_loop()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
        
        
class AuthenticationError(Exception):
        pass

class MarketClosedError(Exception):
    pass

class MarketEmptyError(Exception):
    pass