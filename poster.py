import sqlite3, random, os, git, datetime, logging
import custom_pytumblr as pytumblr
from dotenv import load_dotenv

# this file is run every 30 minutes using windows' Task Scheduler
# you can do something similar on linux with cronjobs

now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
os.makedirs("logs/poster", exist_ok=True)
logging.basicConfig(filename=f"logs/poster/{now}.log", format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s", filemode="w")
log = logging.getLogger("emojibot_poster")
log.setLevel(logging.DEBUG)

log.debug("getting current git branch...")
git_branch = git.Repo(os.getcwd()).active_branch.name
if not git_branch == "main":
    log.warning(f"not on main branch, instead on {git_branch}; not posting ({datetime.now()})")
    with open("warnings.txt", "a", encoding="utf-8") as file:
        file.write(f"not on main branch, instead on {git_branch}; not posting ({datetime.now()})\n")
    exit()
else:
    log.debug("on main branch! continuing")

log.debug("loading environment variables...")
load_dotenv()

log.debug("initializing tumblr client...")
client = pytumblr.TumblrClient(
    os.getenv('CONSUMER_KEY'),
    os.getenv('CONSUMER_SECRET'),
    os.getenv('OAUTH_TOKEN'),
    os.getenv('OAUTH_TOKEN_SECRET')
)

log.debug("connecting to database...")
conn = sqlite3.connect("posts.sqlite3")
cursor = conn.cursor()

log.info("fetching non-reblogged posts...")
cursor.execute("SELECT * FROM posts WHERE reblogged = 0")

results = cursor.fetchall()
result = random.choice(results)

if result:
    log.info(f"successfully fetched {len(results)} posts and chose one!")
    log.info("reblogging...")

    post_id = result[1]
    post_reblog_key = result[2]
    post_tags = eval(result[3])

    # log.debug(f"post ID: {str(post_id)}", f"post reblog key: {str(post_reblog_key)}", f"post tags: {str(post_tags)}")
    
    response = client.reblog("emoji-archive-bot", id=post_id, reblog_key=post_reblog_key, tags=post_tags)

    try:
        http_code = response["meta"]["status"]
        http_message = response["meta"]["msg"]
        if http_code == 201: # if it succeeded
            log.info("reblog successful!")
            cursor.execute(f"UPDATE posts set reblogged = 1 WHERE post_id = '{post_id}'")
            
            conn.commit()
            conn.close()
        else:
            log.error(f"reblog failed with code {http_code}: {http_message}")
            # it failed, probably due to hitting the post limit. don't worry about it and don't update the database
    except:
        log.error("something happened? here's the response:", str(response))
        pass
else:
    log.warning("out of posts! please run the scraper again!")
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