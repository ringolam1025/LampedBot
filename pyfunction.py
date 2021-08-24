import random
import logging
import logging.config

from pycoingecko import CoinGeckoAPI

def setUserName(from_user):
    """ Check sender name """
    # print("setUserName")
    _senderName = ""
    if from_user.username:
        _senderName = from_user.username
    
    else:
        _senderName = from_user.first_name

    return _senderName

def genFriendlyMsg(msgType):
    """ Radom generate friendly message """
    print("genFriendlyMsg")
    _res = ""
    msgTemplate = {
                    'addMsg':['Added: ', '已新增: ', '幫你加左: ', '加ed: '],
                    'delMsg':['Deleted: ', '已刪除: ', '幫你Del左: '],
                    'noBuyMsg':['你冇買: ', '冇買: ', '搵唔到: ']
                    }

    _res = msgTemplate[msgType][random.randrange(0, len(msgTemplate[msgType])-1)]

    return _res

def createNewCoinInDB(chat_id, coinDtl, username, userid, firebase):
    """ Handle add data to Firebase DB """
    print("addNewCoinToDB")
    searchRes = searchCoinByID(coinDtl['id'].lower())  
    toDB = {
        "ReplyTitle":"",
        "ID" : searchRes['id'],
        "Symbol" : searchRes['symbol'],
        "Name" : searchRes['name'],
        "Dapp" : searchRes['link'],
        "Holders" : {userid : username}
        # "Platform" : searchRes['asset_platform_id']
    }
    
    res = firebase.put('/'+chat_id+'/coinsList', searchRes['symbol'].upper(),toDB)
    _msg = ('{}\n${}').format(genFriendlyMsg('addMsg'), searchRes['symbol'].upper())
    return _msg
   
def addMultipleCoin(chat_id, coins, username, firebase):
    """ Handling multiple add coin: igrone DApp, coin_id """
    print("addMultipleCoin")
    _msg = ""

    for coin in coins:
        coin = coin.upper()
        _result = firebase.get('/'+chat_id+'/coinsList/',coin)
        if _result:
            firebase.put('/'+chat_id+'/coinsList/'+coin+'/Holders',username,"true")
        else:
            toDB = {
                        "ReplyTitle":"",
                        "Dapp" : '',
                        "CoinGeckoID" : '',
                        "Holders" : {username : "true",}
                    }
            firebase.put('/'+str(chat_id)+'/coinsList', coin, toDB)

        _msg += (" " if len(_msg) != 0 else "") + "$" + coin

    _msg = ('{}\n{}').format(genFriendlyMsg('addMsg'), _msg)

    return _msg

def coinBuySell(chat_id, coin, username, userid, side, firebase):
    """ Handle user action (Buy/Sell) """
    print("coinBuySell")
    _msg = ""
    coin = coin.upper()

    if side == "buy":
        firebase.put('/'+chat_id+'/coinsList/'+coin+'/Holders', userid, username)

    elif side == "sell":
        firebase.delete('/'+chat_id+'/coinsList/'+coin+'/Holders',userid)

    _msg = ('${}').format(coin)
    return _msg

def buyCoin(chat_id, coin, username, userid, firebase):
    """ Handling single add coin: check DApp, coin_id """
    print("buyCoin")
    _msg = ""

    coin = coin.upper()
    firebase.put('/'+chat_id+'/coinsList/'+coin+'/Holders', userid, username)

    _msg = ('{}\n${}').format(genFriendlyMsg('addMsg'), coin)
    return _msg

def sellCoin(chat_id, coin, username, userid, firebase):
    """ Handling user sold coin(s) """ 
    print("sellCoin")
    _msg = ""

    coin = coin.upper()
    firebase.delete('/'+chat_id+'/coinsList/'+coin+'/Holders',userid)

    _msg = ('{}\n${}').format(genFriendlyMsg('delMsg'), coin)
    return _msg

def searchCoinIDBySymbol(symbol):
    """ Use CoinGecko API to get ID by Symbol """
    print("searchCoinIDBySymbol")
    _res = []
    cg = CoinGeckoAPI()
    coinlist = cg.get_coins_list()   
    for coin_dtl in coinlist:
        if coin_dtl['symbol'] == symbol:
            _res.append(coin_dtl)
    print(_res)       
   # return _res

def TMPsearchCoinIDBySymbol(symbol, coinlist):
   """ Use CoinGecko API to get ID by Symbol """
   print("TMPsearchCoinIDBySymbol: " + symbol)
   _res = []
   for coin_dtl in coinlist:
       if coin_dtl['symbol'] == symbol:
           _res.append(coin_dtl)
   return _res

def searchCoinByID(coin):
    """ Use CoinGecko API to get coin details """
    print("searchCoinByID")
    _msg = ""
    resArr = []
    cg = CoinGeckoAPI()
    apiRes = cg.get_coin_by_id(id=coin, localization='false', tickers='false', market_data='true', community_data='false', developer_data='false', sparkline='false')

    if apiRes:
        resArr = {
            'id' : apiRes['id'],
            'symbol' : apiRes['symbol'],
            'name' : apiRes['name'],
            #'asset_platform_id' : apiRes['asset_platform_id'],
            'link' : apiRes['links']['homepage'][0],            
            'current_price' : apiRes['market_data']['current_price']['usd'],
            'price_change_24h' : apiRes['market_data']['price_change_24h'],
            'price_change_percentage_24h' : apiRes['market_data']['price_change_percentage_24h']
        }

        # if len(apiRes['contract_address']):
        #     resArr['contract_address'] = apiRes['contract_address']

    return resArr

def updateBotSetting(chat_id, setting, var, firebase):
    """ Use Bot setting """
    _setting = ""
    if var == 'ON':
        var = "True"

    elif var == 'OFF':
        var = "False"

    else:
        var = var

    firebase.put('/'+str(chat_id)+'/Setting', setting, var)

    return _setting

def getBotSetting(chat_id, setting, firebase):
    """ Get Bot setting """
    _setting = ""
    dbRes = firebase.get('/'+str(chat_id)+'/Setting',setting.upper())
    if dbRes:
        _setting = dbRes

    return _setting
    
def holdGetPrice(coinArr, coinPriceArr, resType, chat_id, firebase):
    """ Get coins Price, 24hr change """
    print("holdGetPrice")
    cg = CoinGeckoAPI()
    _resAPI = {}
    _resStr = ""

    _setting = getBotSetting(chat_id, "ICON_DISPLAY", firebase)
    if _setting == "CIRCLE":
        light = {'green':'\U0001F7E2', 'red':'\U0001F534'}
    else:
        light = {'green':'\U0001F7E9', 'red':'\U0001F7E5'}

    _resAPI = cg.get_price(ids=coinPriceArr, vs_currencies='usd', include_24hr_change='true')
    
    for i in range(len(coinArr)):
        if coinArr[i]['ID'] != "":
            color = light['green'] if round(_resAPI[coinArr[i]['ID']]['usd_24h_change'],2) > 0 else light['red']
            signal = "+" if round(_resAPI[coinArr[i]['ID']]['usd_24h_change'],2) > 0 else ""
            if resType == 'hold':
                _resStr += "{}. <a href='{}'>{}</a><code> | ${} {}{}% {}</code>\n".format(str(i+1), coinArr[i]['Dapp'], coinArr[i]['Symbol'].upper(), _resAPI[coinArr[i]['ID']]['usd'], signal, round(_resAPI[coinArr[i]['ID']]['usd_24h_change'],2), color)

            else:
                _resStr += "<strong><u><a href='{}'>{}</a></u></strong><code> | ${} {}{}% {}</code>\n".format(coinArr[i]['Dapp'], coinArr[i]['Symbol'].upper(), _resAPI[coinArr[i]['ID']]['usd'], signal, round(_resAPI[coinArr[i]['ID']]['usd_24h_change'],2), color)
        else:
                if resType == 'hold':
                    _resStr += "{}. {}<code> | - </code>\n".format(str(i+1), coinArr[i]['Symbol'].upper())
                else:
                    _resStr += "<strong><u>{}</u></strong><code> |  - </code>\n".format(coinArr[i]['Symbol'].upper())

    return _resStr

def showCoin(coinID, chat_id, firebase):
    resStr = ""
    dbRes = firebase.get('/'+str(chat_id)+'/coinsList',coinID)
    coinArr = []
    coinPriceArr = []

    if dbRes:
        counter = 1

        if dbRes['ID'] != '':
            coinPriceArr.append(dbRes['ID'])
            coinArr.append({"ID":dbRes['ID'], "Symbol":dbRes['Symbol'],  "Name":dbRes['Name'], "Dapp":dbRes['Dapp']})
        else:
            coinArr.append({"ID":"", "Symbol":dbRes['Symbol'], "Name":"", "Dapp":""})

        resStr += holdGetPrice(coinArr, coinPriceArr, '', chat_id, firebase) + "\n"

        for Holder in dbRes['Holders']:
            resStr += ('{}. {}\n').format(str(counter), '<a href="tg://user?id=' + str(Holder) + '">' + dbRes['Holders'][Holder] + '</a>')
            counter = counter + 1

        resStr += "\n"
    else:
        resStr += '未有人買過呢隻coin!\n請用/buy ' + coinID + '新增'

    return resStr