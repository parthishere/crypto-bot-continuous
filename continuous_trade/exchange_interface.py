from genericpath import exists
import sys, os
from continuous_trade import settings
from continuous_trade import hotbit
import logging

logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')


class ExchangeInterface():
    def __init__(self):
        if len(sys.argv) > 1:
            self.symbol = sys.argv[1]
        else:
            self.symbol = settings.ASSET
            
        self.hotbit = hotbit.Hotbit(api_key=settings.API_KEY, secret_key=settings.SECRET_KEY, symbol=settings.ASSETS)
    
    def get_position(self, symbol=None):
        if symbol is None:
            symbol = self.symbol
        return self.hotbit.get_balance_query()['result']
    
    def get_delta(self, symbol=None):
        if symbol is None:
            symbol = self.symbol
        
        return float(self.get_position().get(symbol).get('available'))


    def get_recent_order_bids(self):
        return self.hotbit.get_recent_order_bids()
    
    def get_recent_order_sells(self):
        return self.hotbit.get_recent_order_sells()
    
    
    # def get_highest_buy(self):
    #     buys = [o for o in self.get_recent_order_bids()['result']['orders']]  #2 for buy
    #     if not len(buys):
    #         return -2**32
    #     highest_buy = float(max(buys or [], key=lambda o: float(o['price']))['price'])
    #     return highest_buy if highest_buy else -2**32

    # def get_lowest_sell(self):
    #     sells = [o for o in self.get_recent_order_sells()['result']['orders']]    #1 for sell
    #     if not len(sells):
    #         return 2**32
    #     lowest_sell = float(min(sells or [], key=lambda o: float(o['price']))['price'])
    #     return lowest_sell if lowest_sell else 2**32  # ought to be enough for anyone

    def get_margin(self):
        return self.hotbit.get_balance_query()

    def get_ticker(self, symbol=None):
        """ real time data of symbol  """
        if symbol is None:
            symbol = self.symbol
        return self.hotbit.market_summery(symbol)
        
    def create_bulk_orders(self, orders):
        o_ids = []
        for order in orders:
            if order['side'] == 1:  # 1-Seller???2-buyer
                # for seller
                o = self.hotbit.sell(amount=order['amount'], price=order['price'])
                o_ids.append(o['result'])
            else:  # 1-Seller???2-buyer
                # for buyer
                o = self.hotbit.buy(amount=order['amount'], price=order['price'])
                o_ids.append(o['result'])
        print("Placed Order Details"+str(o_ids))
        return o_ids
        
    
    def get_pending_orders(self):
        return self.hotbit.pending_orders()
    
    def cancel_order(self, order):
        pending_orders = self.get_pending_orders().get('result').get(self.symbol).get('records')
        to_cancel = None
        if pending_orders != None: 
            to_cancel = [o for o in pending_orders if o['id'] == order['id']]
            if to_cancel:
                logging.warning("Canceling:%d %s %d @ %.*f" % (order['id'], order['side'], order['amount'], order['price']))
                return self.hotbit.order_cancel(order['id'])
        else:
            logging.warning("order does not exists in pending orders with id = %d" % order['id'])
    
    def cancel_all_orders(self):
        logging.warning("Resetting current position. Canceling all existing orders.")
        try:
            orders = self.get_pending_orders().get('result').get("CTSUSDT").get('records')
        except ValueError:
            print("CTSUSDT not found")
        to_cancel = []
        if orders:
            try:
                return self.hotbit.bulk_cancel([order['id'] for order in orders])
            except Exception as e:
                print(e)
                return e
        else:
            logging.warning("No order to cancel")
    
    def cancel_bulk_orders(self, orders):
        for order in orders:
            logging.warning("Canceling: %s %s %d @ %.*f" % (order['id'], order['side'], order['amount'], order['price']))
        return self.hotbit.bulk_cancel([order['id'] for order in orders])


    def get_crypto_price(self):
        return self.hotbit.get_crypto_price()
    
    def get_market_status_today(self, market=None):
        return self.hotbit.market_status_24h()
    
    def get_24h_volume(self):
        return float(self.get_market_status_today()['result']['volume'])
        