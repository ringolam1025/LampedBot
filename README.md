# LampedBot
LampedBot (This bot) is using python to develop. The purpose of this bot is help user to mark which coins have been bought. And provide price to the user. 

# Main Function
1. /buy COIN_NAME = 加幣入你個portfolio
1. /sell COIN_NAME = 係你個portfolio到Remove隻幣
1. /hold = 睇自己portfolio持有咩幣
1. /coinlist = 睇成group持有咩幣
1. /note COIN_NAME MESSAGE = Message + Tag有呢隻既谷友

# Testing
If would like to run on local machine, active the code in `main.py` as below:
```
TOKEN = config['bot_dev']['TOKEN']
DBLINK = config['bot_dev']['DBLINK']
```

```
updater.start_polling()
```

# Depoly
The bot is now depolyed to Heroku. Before upload to Heroku you need to active below code in `main.py`: 
```
TOKEN = os.environ["TOKEN"]
DBLINK = os.environ["DBLINK"]
```
```
updater.start_webhook(listen="0.0.0.0",
                        port=int(PORT),
                        url_path=TOKEN)
updater.bot.setWebhook('https://lampedbot.herokuapp.com/' + TOKEN)
updater.idle()
```




