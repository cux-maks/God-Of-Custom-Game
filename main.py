from dotenv import load_dotenv
load_dotenv()

import os
from god_of_custom_game import MyBot

def main():
    bot = MyBot()
    bot.run(os.getenv("BOT_TOKEN"))

if __name__ == "__main__":
    main()