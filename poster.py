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