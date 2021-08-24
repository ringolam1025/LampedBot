#!/usr/bin/env python
# pylint: disable=W0613
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

import html
import json
import logging
import logging.config
import traceback
import os
import configparser

from firebase import firebase
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, RegexHandler, Filters, ConversationHandler, CallbackQueryHandler, CallbackContext
from pycoingecko import CoinGeckoAPI

from pyfunction import *



config = configparser.ConfigParser()
config.read('config.ini')

# Firebase Database setting
# TOKEN = config['bot_dev']['TOKEN']
# DBLINK = config['bot_dev']['DBLINK']

TOKEN = os.environ["TOKEN"]
DBLINK = os.environ["DBLINK"]
PORT = int(os.environ.get('PORT', 5000))

firebase = firebase.FirebaseApplication(DBLINK, None)
# '[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s','%m-%d %H:%M:%S'

# Enable logging
logging.basicConfig(
    format='[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO, filename='./log/lampBotLog.log', filemode='w', 
)
logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    print("start")
    keyboard = []
    chat_id = str(update.effective_chat.id)
    isDone = False
    _msg = ""
    dbRes = firebase.get('/'+str(chat_id)+'/Setting','')
    
    if dbRes:
        isDone = True

    else:
        isDone = False
        setting = {
            "KIDDING_MODE":True,
            "ICON_DISPLAY":"SQUARE",
            "LANG":"zh",
            "PHOTO1":"https://media.whatscap.com/0dd/34c/0dd34c70b56a7e7097744379a69f06f6674f45b8_b.jpg"
        }
        res = firebase.put('/'+chat_id, "Setting", setting)
    
    _msg = "個bot set 好左喇, 試下用 /help 教你點用啦"
    update.message.reply_text(_msg, parse_mode="HTML", disable_web_page_preview=True)
    
def functionSelect(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data:
        listCoin(update, context)

    query.edit_message_text(text=f"Selected option: {query.data}")

def addCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /addCoin is issued."""
    print("addCoin")
    resStr = ""
    reply_markup = ""
    keyboard = []
    chat_id = str(update.effective_chat.id)
    username = update.message.from_user.first_name
    userid = update.message.from_user.id
    
    context.user_data["triggerUserID"] = userid
    context.user_data["triggerUserName"] = username

    if len(context.args) == 1:
        """ Handling single add coin """
        coin = context.args[0].upper()
        chkCoinExist = firebase.get('/'+chat_id+'/coinsList/',coin)

        if chkCoinExist:
            """ If coin is exist """
            resStr += ('{}\n{}').format(genFriendlyMsg('addMsg'), coinBuySell(chat_id, coin, username, userid, 'buy', firebase))

        else:
            """ If coin is NOT exist """
            searchRes = searchCoinIDBySymbol(coin.lower())
            print(searchRes)
            if len(searchRes) == 1:
                res = createNewCoinInDB(chat_id, searchRes[0], username, userid, firebase)
                resStr += res

            elif len(searchRes) > 1:
                print("B")
                tmp = []
                tmpStr = ""
                for dtl in searchRes:
                    for platform in dtl['platforms']:
                        tmp.append(InlineKeyboardButton(dtl['name'], callback_data='add_'+dtl['id']))                    
                        tmpStr += "<u><b>" + dtl['name'].upper() + "</b></u> (" + platform + ")\n" + dtl['platforms'][platform] + "\n"
                        tmpStr +=  "\n"        

                keyboard.append(tmp)
                reply_markup = InlineKeyboardMarkup(keyboard)

                resStr += ('${} duplicate symbol found! Please select.\n').format(coin.upper())
                resStr += tmpStr
            
            else:
                toDB = {
                    "ReplyTitle":"",
                    "ID" : "",
                    "Symbol" : coin.upper(),
                    "Name" : "",
                    "Dapp" : "",
                    "Holders" : {userid : username}
                    # "Platform" : searchRes['asset_platform_id']
                }
                
                res = firebase.put('/'+chat_id+'/coinsList', coin.upper(),toDB)
                resStr = ('{}\n${}\nBut not listed on CoinGecko, so no price provided').format(genFriendlyMsg('addMsg'), coin.upper())

    elif len(context.args) > 1:
        """ Handling multiple add coin: igrone DApp, coin_id """
        resStr = "Not support multiple buy coin"

    elif len(context.args) == 0:
        """ Wrong format """
        resStr = "Please enter coin name after the command\nExample: /buy mdo"


    if reply_markup:
        update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True, reply_markup=reply_markup)
    else:
        update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def removeCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /removeCoin is issued."""
    print('removeCoin')
    chat_id = str(update.effective_chat.id)
    username = update.message.from_user.first_name
    userid = update.message.from_user.id
    resStr = ""
    success = False
    fail = False

    successStr = ""
    failStr = ""
    
    if len(context.args) != 0:
        for arg in context.args:
            coin = arg.upper()            
            result = firebase.get('/'+chat_id+'/coinsList/'+coin+'/Holders',userid)

            if result:
                # Found in List
                successStr += (", " if len(successStr) != 0 else "") + coinBuySell(chat_id, coin, username, userid, 'sell', firebase)
                success = True

            else:
                failStr += (", " if len(failStr) != 0 else "") + '$' + coin
                fail = True
    else:
        resStr = "Please enter coin name after the command\nExample: /sell mdo"

    if success:
        resStr += genFriendlyMsg('delMsg') + "\n" + successStr + "\n"
    
    if fail:
        resStr += genFriendlyMsg('noBuyMsg') + "\n" + failStr + "\n"

    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def listCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /listCoin is issued."""
    print("listCoin")
    resStr = ""
    reply_markup = ""
    keyboard = []

    dbRes = firebase.get('/'+str(update.effective_chat.id)+'/coinsList','')
    if dbRes:
        resStr += ('呢個大戶Group有{}隻已登記既coin(s):\n').format(str(len(dbRes)))
        listArr = []

        for coin in dbRes:            
            if 'Holders' in dbRes[coin]:
                listArr.append(InlineKeyboardButton('{} [{}]'.format(coin, str(len(dbRes[coin]['Holders']))), callback_data='/sh_{}'.format(coin)))

                if len(listArr) == 3:
                    keyboard.append(listArr)
                    listArr = []
               
        keyboard.append(listArr)
        reply_markup = InlineKeyboardMarkup(keyboard)

    else:
        resStr += '未有coin!\n請用/addcoin [coin name] 新增'

    if reply_markup:
        update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True, reply_markup=reply_markup)
    else:
        update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def showCoinHolder(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /showholder is issued."""
    print("showCoinHolder")
    coinID = (update.message.text.replace('/sh_', '').replace('@lamped_bot', '')).upper()
    chat_id = update.effective_chat.id

    resStr = showCoin(coinID, chat_id, firebase)
    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)
    
def handleReply(update: Update, context: CallbackContext) -> None:
    """Send a message when user no need to coin"""
    print("handleReply")
    chat_id = str(update.effective_chat.id)

    query = update.callback_query
    query.answer()
    userReply = query.data.split("_")
    
    action = userReply[0]
    coinID = userReply[1]

    if action == 'add':
        userid = context.user_data["triggerUserID"]
        username = context.user_data["triggerUserName"]

        searchRes = searchCoinByID(coinID.lower())
        if searchRes:                
            res = createNewCoinInDB(chat_id, searchRes, username, userid, firebase)
            query.edit_message_text(res)

    elif action == '/sh':
        resStr = showCoin(coinID, chat_id, firebase)
        query.edit_message_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

    elif query.data == 'N':
        query.edit_message_text("Bye!")

def showSpecificUserList(update: Update, context: CallbackContext) -> None:
    """ handle show speicfic user """
    print("showSpecificUserList")

    coinArr = []
    coinPriceArr = []
    chat_id = str(update.effective_chat.id)
    userid = str(update.message.from_user.id)
    username = update.message.from_user.first_name
        
    update.message.reply_text("Load緊....", parse_mode="HTML", disable_web_page_preview=True)
    resStr = ""
    dbRes = firebase.get('/'+chat_id+'/coinsList','')
    if dbRes:
        resStr += ('<strong>{}持有既coins</strong>\n').format(username)
        for coin in dbRes:
            dbRes2 = firebase.get('/'+chat_id+'/coinsList/'+coin+'/Holders','')            
            if dbRes2:                
                for Holders in dbRes[coin]['Holders']:
                    if Holders == userid:
                        if dbRes[coin]['ID'] != '':
                            coinPriceArr.append(dbRes[coin]['ID'])
                            coinArr.append({"ID":dbRes[coin]['ID'], "Symbol":dbRes[coin]['Symbol'],  "Name":dbRes[coin]['Name'], "Dapp":dbRes[coin]['Dapp']})

                        else:
                            coinArr.append({"ID":"", "Symbol":dbRes[coin]['Symbol'], "Name":"", "Dapp":""})

        resStr += holdGetPrice(coinArr, coinPriceArr, 'hold', chat_id, firebase)
        
    else:
        resStr = '呢條友冇買過coins'

    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def alertCoinHolder(update: Update, context: CallbackContext) -> None:
    """ handle alert coin holder """
    print("alertCoinHolder")
    chat_id = str(update.effective_chat.id)
    username = update.message.from_user.first_name
    userid = update.message.from_user.id
    resStr = ""
    args = context.args
    
    if len(args) == 2:
        coin = args[0].upper()
        coinArr = []
        coinPriceArr = []  
        dbRes = firebase.get('/'+chat_id+'/coinsList',coin)
        if dbRes:
            # Found in List
            if dbRes['ID'] != '':
                coinPriceArr.append(dbRes['ID'])
                coinArr.append({"ID":dbRes['ID'], "Symbol":dbRes['Symbol'],  "Name":dbRes['Name'], "Dapp":dbRes['Dapp']})
            else:
                coinArr.append({"ID":"", "Symbol":dbRes['Symbol'], "Name":"", "Dapp":""})
            
            resStr += holdGetPrice(coinArr, coinPriceArr, '', chat_id, firebase)
            resStr += args[1] + "\n"

            for Holder in dbRes['Holders']:
                resStr += "<a href='tg://user?id={}'>{}</a> ".format(str(Holder), dbRes['Holders'][Holder])
            
        else:
            # Not found in List
            resStr = ('冇人有 ${} 呢隻幣\n').format(coin)
    else:
        resStr = "Wrong command format\nExample: /alert mdo 走鬼喇!"
    
    # 
    if getBotSetting(chat_id, "PHOTO1", firebase):
        update.message.bot.send_photo(chat_id, getBotSetting(chat_id, "PHOTO1", firebase), resStr, parse_mode="HTML")
    else:
        update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def future(update: Update, context: CallbackContext) -> None:
    """Calculate Future"""
    print("future")
    chat_id = str(update.effective_chat.id)
    userid = update.message.from_user.id
    resStr = ""
    
    if len(context.args) == 4:
        side = ""
        p = float(context.args[0])
        loss = float(context.args[1])
        sp = float(context.args[2])
        sl = float(context.args[3])
        amount = (p*(loss/100))/(sp-sl)
        light = {'green':'\U0001F7E2', 'red':'\U0001F534'}

        if amount > 0:
            side = "Long"
            color = light['green']
        else:
            side = "Short"
            color = light['red']

        resStr = ("<u><b><i>{} Position</i></b></u> {}\n計算方式: (本金*可接受損失百份比)/(開倉價-止蝕價)\n\n你個情況: ({}*{})/({}-{})\n建議倉位: <b>{}</b>\n\n Remark:\n<pre>倉位負數 = Short, 倉位正數 = Long</pre>").format(side, color, p, str(loss)+"%", sp, sl, amount)
    else:
        resStr = "Formula:(本金*可接受損失百份比)/(開倉價-止蝕價) \n Format Error \n E.g. /future 1000 2 2250 2240"    

    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)


# TODO  Phase 2 - OTC Reminder
# TODO  Phase 3 - My coin list with Price 
# TODO  Phase 4 - Set timer check wallet 
 
# TODO Option - Setting
def setting(update: Update, context: CallbackContext) -> None:
    """Send a message for kidding."""
    print("setting")
    chat_id = str(update.effective_chat.id)
    userid = update.message.from_user.id
    resStr = ""

    if str(userid) == "622225198":
        if len(context.args) == 2:
            setting = context.args[0].upper()
            var = context.args[1].upper()
            updateBotSetting(chat_id, setting, var, firebase)
            resStr = "Setting Updated."
        else:
            resStr = "Available command. \n - Kidding_mode [on/off] \n - Icon_Display [circle/square] \n - Lang [en/zh]"
        
    else:
        resStr = "唔關你事"

    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def fixCoin(update: Update, context: CallbackContext) -> None:
    print("fixCoin")
    resStr = ""
    chat_id = str(update.effective_chat.id)
    dbRes = firebase.get('/'+str(chat_id)+'/coinsList','')
    username = update.message.from_user.first_name
    userid = update.message.from_user.id
    user = update.message.from_user.username
    count = 0
    fail_list = ""

    if str(userid) == "622225198":
        _res = []
        cg = CoinGeckoAPI()
        coinlist = cg.get_coins_list()
        if dbRes:
            for coin in dbRes:
                # Step 1: Replace username to userid
                try:
                    if dbRes[coin]['Holders']:
                        coinDtl = TMPsearchCoinIDBySymbol(coin.lower(), coinlist)
                        if len(coinDtl) == 1:
                            searchRes = searchCoinByID(coinDtl[0]['id'].lower())
                            
                            firebase.put('/'+chat_id+'/coinsList/'+coin, "ReplyTitle", "")
                            firebase.put('/'+chat_id+'/coinsList/'+coin, "ID", searchRes['id'])
                            firebase.put('/'+chat_id+'/coinsList/'+coin, "Symbol", searchRes['symbol'])
                            firebase.put('/'+chat_id+'/coinsList/'+coin, "Name", searchRes['name'])
                            firebase.put('/'+chat_id+'/coinsList/'+coin, "Dapp", searchRes ['link'])

                            firebase.delete('/'+chat_id+'/coinsList/'+coin, 'id')
                        else:
                            fail_list += (", " if len(fail_list) != 0 else "") + coin

                except:
                    firebase.delete('/'+chat_id+'/coinsList',coin)

        resStr = "Completed, Please manual update the following: "+ fail_list
    
    else:
        resStr = "唔關 你事!"

    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

def fix(update: Update, context: CallbackContext) -> None:
    """Send a message for kidding."""
    print("fix")
    resStr = ""
    chat_id = str(update.effective_chat.id)
    dbRes = firebase.get('/'+str(chat_id)+'/coinsList','')
    username = update.message.from_user.first_name
    userid = update.message.from_user.id
    user = update.message.from_user.username

    _res = []
    cg = CoinGeckoAPI()
    coinlist = cg.get_coins_list()
    # print(coinlist)

    if dbRes:
        for coin in dbRes:
            # Step 1: Replace username to userid
            try:
                for Holders in dbRes[coin]['Holders']:
                    if Holders == user:
                        resStr += coinBuySell(chat_id, coin, user, user, 'sell', firebase)
                        resStr += coinBuySell(chat_id, coin, user, userid, 'buy', firebase)

            except:
                firebase.delete('/'+chat_id+'/coinsList',coin)

    update.message.reply_text("[Update] UserID Completed", parse_mode="HTML", disable_web_page_preview=True)

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""    
    update.effective_message.reply_html(        
        f'/buy COIN_NAME = 加幣入你個portfolio\n'
        f'/sell COIN_NAME = 係你個portfolio到Remove隻幣\n'
        f'/hold = 睇自己portfolio持有咩幣\n'
        f'/coinlist = 睇成group持有咩幣\n'
        f'/note COIN_NAME MESSAGE = Message + Tag有呢隻既谷友\n\n'
        f'<u><strong>Remark:</strong></u>\n'
        f'1. /sell 可以支援同時幾隻幣\n'
        f'2. 使用 /buy 加幣果陣, 如果係CoinGecko 搵唔到呢隻幣, 會照加入去你個portfolio到, 但用 /hold 果陣就唔會show幣價\n'
    )

def kidding(update: Update, context: CallbackContext) -> None:
    """Send a message for kidding."""
    print("kidding")
    update.message.reply_text("dnlm", parse_mode="HTML", disable_web_page_preview=True)   
   
def error(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    resStr = "Something wrong. <a href='tg://user?id={}'>{}</a>\n#Error".format(622225198, 'Ringo (Lampgo)')
    update.message.reply_text(resStr, parse_mode="HTML", disable_web_page_preview=True)

    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Start the bot."""
    expression = '((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*'
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    ## Call the BOT
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text("dnlm"), kidding))

    ## Handle Add coins
    dispatcher.add_handler(CommandHandler("buy", addCoin))
    dispatcher.add_handler(CallbackQueryHandler(handleReply))

    ## Handle Remove coins
    dispatcher.add_handler(CommandHandler("sell", removeCoin))

    ## Handle Show coin list
    dispatcher.add_handler(CommandHandler("coinlist", listCoin))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^(/sh_[a-zA-Z0-9\.\/\?\:@\-_=#]+)$'), showCoinHolder))
    dispatcher.add_handler(CommandHandler("hold", showSpecificUserList))
    dispatcher.add_handler(CommandHandler("hodl", showSpecificUserList))
    dispatcher.add_handler(CommandHandler("note", alertCoinHolder))

    ## Others
    dispatcher.add_handler(CommandHandler("set", setting))
    dispatcher.add_handler(CommandHandler("future", future))
    dispatcher.add_handler(CommandHandler("help", help_command))

    dispatcher.add_handler(CommandHandler("fix", fix))
    dispatcher.add_handler(CommandHandler("fixCoin", fixCoin))
    
    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    # Testing
    # updater.start_polling()
    
    # Production
    updater.start_webhook(listen="0.0.0.0",
                        port=int(PORT),
                        url_path=TOKEN)
    updater.bot.setWebhook('https://lampedbot.herokuapp.com/' + TOKEN)
    updater.idle()

if __name__ == '__main__':
    main()
