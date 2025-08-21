import sqlite3, random, os
import custom_pytumblr as pytumblr
from dotenv import load_dotenv

# this file is run every 30 minutes using windows' Task Scheduler
# you can do something similar on linux with cronjobs

load_dotenv()
client = pytumblr.TumblrClient(
    os.getenv('CONSUMER_KEY'),
    os.getenv('CONSUMER_SECRET'),
    os.getenv('OAUTH_TOKEN'),
    os.getenv('OAUTH_TOKEN_SECRET')
)

conn = sqlite3.connect("posts.sqlite3")
cursor = conn.cursor()

cursor.execute("SELECT * FROM posts WHERE reblogged = 0")

results = random.choice(cursor.fetchall())

if results:
    post_id = results[1]
    post_reblog_key = results[2]
    post_tags = eval(results[3])
    
    client.reblog("emoji-archive-bot", id=post_id, reblog_key=post_reblog_key, tags=post_tags)
    
    cursor.execute(f"UPDATE posts set reblogged = 1 WHERE post_id = '{post_id}'")
    
    conn.commit()
    conn.close()
else:
    with open("warnings.txt", "r", encoding="utf-8") as file:
        warnings = file.readlines()
    if "out of posts" in warnings:
        pass
    else:
        with open("warnings.txt", "a", encoding="utf-8") as file:
            file.write("out of posts\n")
        client.create_text(
            "emoji-archive-bot", 
            body="[automated] hey @goldstargloww i've run out of posts help me", 
            tags=[
                "don't worry i just need to run the scraper again and this is a reminder to make me do that",
                "bot post",
                "not an emoji"
                ]
            )