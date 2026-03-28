import sqlite3, time, math, re, os, time, util, datetime, logging, sys
from bs4 import BeautifulSoup
import custom_pytumblr as pytumblr
from dotenv import load_dotenv
from alive_progress import alive_bar # for progress bar in terminal

now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
os.makedirs("logs/scraper", exist_ok=True)
logging.basicConfig(
    handlers=[logging.FileHandler(f"logs/scraper/{now}.log"), logging.StreamHandler(sys.stdout)],
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
)
log = logging.getLogger("emojibot_scraper")
log.setLevel(logging.INFO)

load_dotenv()
client = pytumblr.TumblrClient(
    os.getenv('CONSUMER_KEY'),
    os.getenv('CONSUMER_SECRET'),
    os.getenv('OAUTH_TOKEN'),
    os.getenv('OAUTH_TOKEN_SECRET')
)


taglist = [
    "emoji",
    "emojis",
    "emote",
    "emotes",
    "custom emoji",
    "custom emojis",
    "custom emote",
    "discord emoji",
    "discord emojis",
    "discord emote",
    "discord emotes",
    "custom discord emoji",
    "custom discord emojis",
    "my emojis",
    "emoji blog",
    "ftu emoji",
    "aac emoji",
    "aac emote",
    "aac image",
    "aac symbol",
    "aac emoji",
    "emoji art",
    "emote artist",
    "cute emoji",
    "wordmoji",
    "word emoji",
    # "aac symbols",
    # "custom discord emote",
    # "custom discord emotes",
    # "custom emotes",
    # "cute emojis",
    # "cute emote",
    # "cute emotes",
    # "discord emoji blog",
    # "emoji artist",
    # "emote blog",
    # "f2u emoji",
    # "nonverbal emoji",
    # "nonverbal emojis",
    # "nonverbal emote",
    # "nonverbal emotes",
    # "word emojis",
    # "word emojis",
    # "word moji",
    # "word mojis",
    # "wordmojis",
]
global_tag_ignore_list = taglist + [
    "queued",
    "request",
    "requests",
    "ask",
    "asks",
    "digital art",
    "art",
    "artists on tumblr",
    "aac symbols",
    "custom discord emote",
    "custom discord emotes",
    "custom emotes",
    "cute emojis",
    "cute emote",
    "cute emotes",
    "discord emoji blog",
    "emoji artist",
    "emote blog",
    "f2u emoji",
    "nonverbal emoji",
    "nonverbal emojis",
    "nonverbal emote",
    "nonverbal emotes",
    "word emojis",
    "word emojis",
    "word moji",
    "word mojis",
    "wordmojis",
]
global_tag_block_list = ["nsfw", "not emoji", "not an emoji"]


conn = sqlite3.connect("posts.sqlite3")
cursor = conn.cursor()
cursor.execute("SELECT * FROM blogs WHERE active = 1")
bloglist: list[list[str]] = []
for item in cursor.fetchall():
    bloglist.append(list(item)) # cast from tuple to list
conn.close()


def remove_duplicates(thing):
    # https://stackoverflow.com/a/9428041
    return [i for n, i in enumerate(thing) if i not in thing[n + 1 :]]


def check_rate_limit(response: dict[str], headers: dict[str]):
    # there's probably a smarter way to do this but hey it works (mostly)
    log.debug("checking rate limit...")
    
    if response["meta"]["status"] == 429: # if the rate limit was hit
        perday_remaining = int(headers["X-Ratelimit-Perday-Remaining"]) # remaining requests per day
        perhour_remaining = int(headers["X-Ratelimit-Perhour-Remaining"]) # remaining requests per hour

        if perday_remaining == 0:
            perday_reset = int(headers["X-Ratelimit-Perday-Reset"])
            log.info(f"hit rate limit for the day, sleeping for {time.strftime("%Hh %Mm %Ss", time.gmtime(perday_reset))}")
            try:
                with alive_bar(perday_reset, title="rate limit") as bar:
                    for _ in range(perday_reset):
                        time.sleep(1)
                        bar()
            except:  # can't nest alivebar, so if there's already one going, just wait instead
                time.sleep(perday_reset)
            return True

        elif perhour_remaining == 0:
            perhour_reset = int(headers["X-Ratelimit-Perhour-Reset"])
            log.info(f"hit rate limit for the hour, sleeping for {time.strftime("%Hh %Mm %Ss", time.gmtime(perhour_reset))}")
            try:
                with alive_bar(perhour_reset, title="rate limit") as bar:
                    for _ in range(perhour_reset):
                        time.sleep(1)
                        bar()
            except:  # can't nest alivebar, so if there's already one going, just wait instead
                time.sleep(perhour_reset)
            return True

    log.debug("rate limit wasn't hit, it's fine")
    return False # rate limit wasn't hit, it's fine


def get_posts_from_blog(
    blog: list[str],
    tag: str,
    check_for_repeated_posts: bool = True,
    repeated_posts_threshold: int = 1
) -> list[dict]:
    """gets posts from all blogs and all tags

    Args:
        blog ([blog_name: str, blog_uuid: str]): the blog you want to search
        tag (str): the tag you want to search
        check_for_repeated_posts (bool = True): whether or not to check if a post is already in the database
        repeated_posts_threshold (int = 1): if checking for repeated posts, how many posts does it take to decide you have all of them
    Returns:
        out (str | list[dict]): either a message returning a status update ("blog not found", "already have all posts",\
            "no posts", "no posts with images"), or a list of dictionaries each containing a post, in the format {"blog": [blog_name, blog_uuid],\
            "id": post["id"], "tags": post["tags"], "reblog_key": post["reblog_key"]}
    """
    
    blog_name = blog[0]
    blog_uuid = blog[1]

    log.debug(f"getting posts from blog {blog_name}")

    response, headers = client.posts(blog_uuid, tag=tag)  # get posts
    if check_rate_limit(response, headers):  # check if we hit the rate limit
        response, headers = client.posts(blog_uuid, tag=tag)  # do it again if you hit the rate limit the first time

    if response["meta"]["status"] == 404:  # if the blog doesn't exist
        log.info("blog not found; skipping blog")
        with open("warnings.txt", "a", encoding="utf-8") as file:
            file.write(f"{blog} not found\n")  # write to warnings file to check later
        return "blog not found"

    data = response["response"]  # get the data from the response
    new_data = []  # list for new format of the data

    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()

    if data["total_posts"] > 0:  # make sure there's any posts to begin with
        consecutive_repeated_posts = 0  # log consecutive repeated posts
        offset_range = math.ceil(data["total_posts"] / 20)  # figure out how many pages there are
        
        blog_name_from_data = data["blog"]["name"]
        if blog_name != blog_name_from_data:  # if the stored blog name is different from the received blog name
            cursor.execute("SELECT * FROM blogs WHERE name = ?", (blog_name,))  # check to see if the old name is still in the blog list
            if cursor.fetchall():  # if it is
                cursor.execute("UPDATE blogs SET name = ? WHERE uuid = ?", (blog_name_from_data, blog_uuid))  # replace it
                log.info(f"{blog_name} renamed to {blog_name_from_data} ({blog_uuid})")
                with open("warnings.txt", "a", encoding="utf-8") as file:
                    file.write(f"{blog_name} renamed to {blog_name_from_data} ({blog_uuid})\n")
                    # write to warnings to check later
                    # so i can replace already posted things' tags
            
            conn.commit()  # moved this because i kept getting database is locked errors when trying to change the blog name. hopefully this doesn't break anything
                    
            cursor.execute("SELECT * FROM posts WHERE blog = ?", (blog_name,))  # check to see if the old name is still in the post database
            if cursor.fetchall():  # if it is
                util.blog_name_change(blog_name, blog_name_from_data)  # change posts in database to reflect new name
            
            blog_name = blog_name_from_data
            blog = [blog_name, blog_uuid]

        # progress bar
        with alive_bar(data["total_posts"], title=f"{blog_name} (#{tag})") as bar:

            for i in range(offset_range):  # for every page

                log.debug(f"looping through page {i} of posts with tag {tag}")

                # check if the number of consecutive repeated posts has hit or passed the threshold, just in case
                if consecutive_repeated_posts >= repeated_posts_threshold:
                    log.debug("already have this post; hit the threshold; breaking (at start)")
                    for i in range(data["total_posts"] - i*20):
                        bar()  # finish off the progress bar
                    return "already have all posts"

                # get the next page of posts (unless this is the first iteration)
                if i != 0:
                    log.debug("fetching next page...")
                    response, headers = client.posts(blog_uuid, tag=tag, offset=i * 20)  # get the next page
                    if check_rate_limit(response, headers):  # check to see if we hit the rate limit
                        response, headers = client.posts(blog_uuid, tag=tag, offset=i * 20)  # do it again if you hit the rate limit the first time

                    data = response["response"]  # get the data from the response

                for post in data["posts"]:  # for every post in this page
                    log.debug(f"parsing post {data['posts'].index(post)}")

                    # get the html for the post
                    if post["type"] == "answer":  # ask/answer posts
                        log.debug("post is an ask")
                        soup = BeautifulSoup(post["answer"], "html5lib")
                    elif post["type"] == "photo":  # photo posts
                        log.debug("post is a photo")
                        soup = BeautifulSoup(post["caption"], "html5lib")
                    else:
                        try:  # other posts
                            log.debug("post is an other post")
                            soup = BeautifulSoup(post["body"], "html5lib")
                        except KeyError:  # just in case i missed any
                            raise Exception(f"[DEBUG] post type '{post['type']}' has no body")

                    # if there's a read more / keep reading link
                    # i don't think this works, but i'm keeping it in
                    if soup.find_all('button[aria-label="Keep reading"]'):
                        with open("warnings.txt", "a", encoding="utf-8") as file:
                            # write to warnings file to check manually later
                            file.write(f"read more: {blog_name}/{post['id']}\n")
                            # TODO: make a version of this that works
                            # search for [[MORE]] in posts[0]trail[0][content_raw] or posts[0]reblog[comment], i think
                            # alternatively go through things the blog has already posted and search for a.tmblr-truncated-link.read_more


                    if soup.find_all("figure"):  # make sure the post has any images

                        if check_for_repeated_posts:
                            # check to see if the post is already in the database
                            cursor.execute("SELECT * FROM posts WHERE post_id = ?", (post["id"],))
                            if cursor.fetchall():  # if it is
                                consecutive_repeated_posts += 1  # count another repeated post

                                if consecutive_repeated_posts >= repeated_posts_threshold:
                                    # if the number of consecutive repeated posts has hit or passed the threshold
                                    log.debug("already have this post; hit the threshold; breaking (at end)")
                                    for i in range(data["total_posts"] - (i*20 + data["posts"].index(post))):
                                        bar()  # finish off the progress bar
                                    return "already have all posts"  # return; we likely already have all posts
                                else:
                                    log.debug(f"already have this post; count is now {consecutive_repeated_posts}; skipping")
                                    # if this post is already in the database, but the threshold wasn't hit,
                                    # just go on to the next one instead of logging it again
                                    for i in range(data["total_posts"] - (i*20 + data["posts"].index(post))):
                                        bar()  # finish off the progress bar
                                    continue
                                

                        new_data.append(
                            {
                                "blog": [blog_name, blog_uuid],
                                "id": post["id"],
                                "tags": post["tags"],
                                "reblog_key": post["reblog_key"],
                            }
                        )
                    else:
                        log.debug("post doesn't have images; skipping")

                    bar()  # advance progress bar
    else:
        # if there's no posts
        log.debug("blog has no posts in this tag")
        print(f"{blog_name} (#{tag}) | no posts")
        conn.close()
        return "no posts"
    
    if new_data == []:
        # if there's no posts with images
        log.debug("blog has no posts with images in this tag")
        print(f"{blog_name} (#{tag}) | no posts with images")
        conn.close()
        return "no posts with images"
    conn.close()
    return new_data


def get_posts_from_all_blogs(
    blogs: list[list[str]],  # [[blog_name, blog_uuid]]
    tags_to_search: list,
    skip: int = 0,  # skip the first n blogs in bloglist
):
    """gets posts from all blogs and all tags

    Args:
        blogs ([[blog_name: str, blog_uuid: str]]): list of blogs to search 
        tags_to_search (list[str]): list of tags to search
        skip (int = 0): number of blogs to skip. take the rowid of the blog you were in the middle of and subtract 1
    """
    log.info(f"collecting posts from all blogs, starting with blog number {skip}")
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()

    posts = None

    for blog_name, blog_uuid, active, tags in blogs[skip:]:
        log.info(f"searching blog {blog_name}, number {blogs.index([blog_name, blog_uuid, active, tags])}")
        if tags:
            tags = eval(tags)
            if type(tags) == list:
                tags_to_search += tags
        # print(blog_name)
        for tag in tags_to_search:
            log.info(f"searching tag {tag}")
            posts = get_posts_from_blog([blog_name, blog_uuid], tag)

            if posts == "blog not found":
                break  # stop going through tags if this blog can't be found

            if posts in ["already have all posts", "no posts", "no posts with images"]:
                continue

            if not posts:
                log.critical("no posts?!?!?!")
                log.warning(type(posts))
                log.warning(str(posts))
                print("[DEBUG] no posts?!?!?!")  # pretty sure this is supposed to be impossible and that's why i did this
                print(type(posts))
                print(posts)
                exit()

            log.info("adding posts to database...")
            for post in posts:
                if any(x in global_tag_block_list for x in post["tags"]):
                    log.debug("post has blocked tag(s); skipping")
                    continue  # skip if any blocked tags

                try:
                    cursor.execute(
                        f"INSERT INTO posts VALUES (?, ?, ?, ?, 0)",
                        (
                            post["blog"][0],  # blog name
                            post["id"],
                            post["reblog_key"],
                            str([f"blog: {post['blog'][0]}"] + [item for item in post["tags"] if item not in global_tag_ignore_list])
                        )
                    )
                    log.debug("post inserted successfully")
                except sqlite3.IntegrityError:  # if the post is already in there
                    log.debug("post already in database; continuing")
                    pass  # that's fine, keep going
                    
        log.debug("committing changes...")
        conn.commit()


def last_scan():
    response = client.posts("emoji-archive-bot", id="772243895949099008")[0]["response"]
    body = response["posts"][0]["body"]
    pattern = r"(<p><b>last scan:<\/b> )(.+?)(<\/p>)"
    body = re.sub(pattern, r"\g<1>" + datetime.date.today().isoformat() + r"\g<3>", body)
    print(body)
    client.create_text("emoji-archive-bot", state="draft", tags=response["posts"][0]["tags"], format="html", body=body)
    out = client.edit_post("emoji-archive-bot", state="published", type="text", tags=response["posts"][0]["tags"], format="html", body=body, id=772243895949099008)
    print(out)


# get_posts_from_all_blogs(bloglist, taglist)
# get_posts_from_all_blogs(bloglist, taglist, skip=85)
get_posts_from_all_blogs(bloglist, taglist, skip=128)