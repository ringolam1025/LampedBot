#!/usr/bin/env python
# pylint: disable=W0613
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
0x46024C16d1aEc945d2f6405261e3a19Ae42a96Ac
"""

import html
import json
import logging
import logging.config
import traceback
import os

from firebase import firebase
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, RegexHandler, Filters, ConversationHandler, CallbackQueryHandler, CallbackContext)


# import lib.com_fun as com_fun

# Firebase Database setting
# TOKEN = os.environ["TOKEN"]
TOKEN = "1607787626:AAG99KuPjVyz7KBGk-yEfc1cDlQJVDB1wvM"
dbLink = "https://lampedbot-dfbd4-default-rtdb.firebaseio.com/"
firebase = firebase.FirebaseApplication(dbLink, None)
PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO, filename='./log/lampBotLog.log', filemode='w', 
)

logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""

    username = ""
    if update.message.from_user.username:
        username = '@'+update.message.from_user.username
    else:
        username = update.message.from_user.first_name

    keyboard = [
                    [
                        InlineKeyboardButton("Add coin", callback_data='addcoin'),
                        InlineKeyboardButton("List coin", callback_data='coinlist'),
                    ]
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message.text == '喂':
        update.message.reply_text('喂咩呀! 冇名你叫呀! 想做咩呀?', reply_markup=reply_markup)
    elif update.message.text == '登仔':
        update.message.reply_text(username + '. "燈"呀! 唔係"登"呀! ' + '. \n想做咩呀?', reply_markup=reply_markup)
    else:
        update.message.reply_text('Hello! '+username + '. \n有咩幫到你?', reply_markup=reply_markup)

def functionSelect(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data:
        listCoin(update, context)

    query.edit_message_text(text=f"Selected option: {query.data}")

def addCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /addCoin is issued."""
    print("addCoin")

    username = ""
    if update.message.from_user.username:
        username = update.message.from_user.username
    
    else:
        username = update.message.from_user.first_name

    context.user_data["triggerUser"] = username   

    if len(context.args) != 0:
        for arg in context.args:
            arg = arg.upper()
            result = firebase.get('/'+str(update.effective_chat.id)+'/coinsList/'+arg,'')
            if result:
                # Found in List
                firebase.put('/'+str(update.effective_chat.id)+'/coinsList/'+arg+'/Holders',username,"true")
                update.message.reply_text('Added: $'+arg)
            else:
                # Not found in List
                context.user_data["newCoin"] = arg
                keyboard = [
                    [
                        InlineKeyboardButton("Yes", callback_data='Y'),
                        InlineKeyboardButton("No", callback_data='N'),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("New coin detected! Need to add $"+arg+" in list?", reply_markup=reply_markup)
    else:
        update.message.reply_text(
            "Please enter coin name after the command\n"+
            "Example: /addcoin mdo"
            )

def removeCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /removeCoin is issued."""
    print('removeCoin!')
    username = update.message.from_user.username

    if len(context.args) != 0:
        for arg in context.args:
            arg = arg.upper()            
            result = firebase.get('/'+str(update.effective_chat.id)+'/coinsList',arg)

            if result:
                # Found in List
                firebase.delete('/'+str(update.effective_chat.id)+'/coinsList/'+arg+'/Holders',username)
                update.message.reply_text('Deleted $'+arg)
            else:
                update.message.reply_text('你都冇買 $'+arg+'呢隻幣Remove咩野呀! ')
    else:
        update.message.reply_text(
            "Please enter coin name after the command\n"+
            "Example: /delcoin mdo"
            )

def listCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /listCoin is issued."""
    resStr = ""
    dbRes = firebase.get('/'+str(update.effective_chat.id)+'/coinsList','')
    # print(dbRes)

    if dbRes:
        resStr += '呢個大戶Group有既coin\n'
        for coinlist in dbRes:
            if 'Holders' in dbRes[coinlist]:
                resStr += '[/sh_{}]\n'.format(coinlist)

    else:
        resStr += '未有人add左coin!\n請用/addcoin [coin name] 新增'

    update.message.reply_text(resStr, parse_mode="MARKDOWN")

def showCoinHolder(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /showholder is issued."""
    print("showCoinHolder")
    coin = update.message.text.replace('/sh_', '').replace('@lamped_bot', '')

    resStr = ""
    dbRes = firebase.get('/'+str(update.effective_chat.id)+'/coinsList',coin)
    counter = 1
    resStr += "<strong>" + coin + "</strong>"+' ('+dbRes['Dapp']+')'+"\n"
    # resStr += dbRes[coinDtl]['ReplyTitle']+"\n"
    for Holder in dbRes['Holders']:
        resStr += str(counter)+". "+"@"+Holder+"\n"
        counter+1
    resStr += "\n"

    update.message.reply_text(resStr, parse_mode="HTML")

def handleAddCoin(update: Update, context: CallbackContext) -> None:
    """Send a message when user no need to coin"""
    print("handleAddCoin")    
    newCoin = context.user_data["newCoin"]
    query = update.callback_query
    query.answer()

    # chkDB = firebase.get('/'+str(update.effective_chat.id)+'/coinsList/'+,'')

    if update.callback_query.data == 'Y':
        text = "Please enter Dapp link for " + newCoin
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text)

    elif update.callback_query.data == 'N':
        query.edit_message_text("Bye!")

def askfDApp(update: Update, context: CallbackContext) -> None:
    """ handle add DApp link """
    print("askfDApp")
    DAppLink = update.message.text

    if context.user_data["triggerUser"]:
        triggerUser = context.user_data["triggerUser"]
        askUser = update.message.from_user.username
        newCoin = context.user_data["newCoin"]

        if triggerUser == askUser:
            toDB = {
                    "ReplyTitle":"",
                    "Dapp" : DAppLink,
                    "Holders" : {askUser : "true",}
                }
            res = addCoinToDB('/'+str(update.effective_chat.id)+'/coinsList', newCoin, toDB)
            if res:
                update.message.reply_text('[List updated] $'+newCoin, parse_mode="MARKDOWN")

def addCoinToDB(loc, newCoin, data):
    """ Handle add data to Firebase DB """
    print("addCoinToDB")
    # print(data)
    res = firebase.put(loc, newCoin, data)
    return res   

# TODO  Phase 2 - OTC Reminder
# TODO  Phase 3 - Set timer check wallet

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""    
    update.effective_message.reply_html(        
        #f'Your chat id is <code>{update.effective_chat.id}</code>.'
        '未有!'
    )
   
def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)    

def main():
    """Start the bot."""
    expression = '((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*'
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    ## Call the BOT
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text("lamped") | Filters.text("喂") | Filters.text("燈仔") | Filters.text("登仔"), start))

    dispatcher.add_handler(CallbackQueryHandler(functionSelect))

    ## Handle Add coins
    dispatcher.add_handler(CommandHandler("addcoin", addCoin))
    dispatcher.add_handler(CallbackQueryHandler(handleAddCoin))
    dispatcher.add_handler(MessageHandler(Filters.regex(expression), askfDApp))

    ## Handle Remove coins
    dispatcher.add_handler(CommandHandler("delcoin", removeCoin))

    ## Handle Show coin list
    dispatcher.add_handler(CommandHandler("coinlist", listCoin))
    dispatcher.add_handler(MessageHandler(Filters.regex(r'^(/sh_[a-zA-Z0-9\.\/\?\:@\-_=#]+)$'), showCoinHolder))
    
    ## Others
    dispatcher.add_handler(CommandHandler("help", help_command))
    


    # TODO  Phase 3 - Set timer check wallet


    # log all errors
    dispatcher.add_error_handler(error)
    # Start the Bot
    # updater.start_polling()
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    updater.bot.setWebhook('https://lampedbot.herokuapp.com/' + TOKEN)



    updater.idle()

if __name__ == '__main__':
    main()
