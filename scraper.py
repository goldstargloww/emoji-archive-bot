import sqlite3, time, math, re, os, time, util
from bs4 import BeautifulSoup
import custom_pytumblr as pytumblr
from dotenv import load_dotenv
from alive_progress import alive_bar # for progress bar in terminal

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
cursor.execute("SELECT * FROM blogs")
bloglist: list[list[str]] = []
for item in cursor.fetchall():
    bloglist.append(list(item)) # cast from tuple to list
conn.close()


def remove_duplicates(thing):
    # https://stackoverflow.com/a/9428041
    return [i for n, i in enumerate(thing) if i not in thing[n + 1 :]]


def check_rate_limit(response: dict[str], headers: dict[str]):
    # there's probably a smarter way to do this but hey it works (mostly)
    
    if response["meta"]["status"] == 429: # if the rate limit was hit
        perday_remaining = int(headers["X-Ratelimit-Perday-Remaining"]) # remaining requests per day
        perhour_remaining = int(headers["X-Ratelimit-Perhour-Remaining"]) # remaining requests per hour

        if perday_remaining == 0:
            perday_reset = int(headers["X-Ratelimit-Perday-Reset"])
            try:
                with alive_bar(perday_reset, title="rate limit") as bar:
                    for _ in range(perday_reset):
                        time.sleep(1)
                        bar()
            except:  # can't nest alivebar, so if there's already one going, just wait instead
                print(f"hit rate limit, sleeping for {time.strftime("%Hh %Mm %Ss", time.gmtime(perday_reset))}")
                time.sleep(perday_reset)
            return True

        elif perhour_remaining == 0:
            perhour_reset = int(headers["X-Ratelimit-Perhour-Reset"])
            try:
                with alive_bar(perhour_reset, title="rate limit") as bar:
                    for _ in range(perhour_reset):
                        time.sleep(1)
                        bar()
            except:  # can't nest alivebar, so if there's already one going, just wait instead
                print(f"hit rate limit, sleeping for {time.strftime("%Hh %Mm %Ss", time.gmtime(perhour_reset))}")
                time.sleep(perhour_reset)
            return True

    return False # rate limit wasn't hit, it's fine


def get_posts_from_blog(
    blog: list[str],
    tag: str,
    filter: bool = True,
    current_posts: list[dict] | None = None,
    repeated_posts_threshold: int = 5,
) -> list[dict]:
    
    blog_name = blog[0]
    blog_uuid = blog[1]

    response, headers = client.posts(blog_uuid, tag=tag)  # get posts
    if check_rate_limit(response, headers):  # check if we hit the rate limit
        response, headers = client.posts(blog_uuid, tag=tag)  # do it again if you hit the rate limit the first time

    if response["meta"]["status"] == 404:  # if the blog doesn't exist
        print("blog not found; skipping blog")
        with open("warnings.txt", "a", encoding="utf-8") as file:
            file.write(f"{blog} not found\n")  # write to warnings file to check later
        return "blog not found"

    data = response["response"]  # get the data from the response
    new_data = []  # list for new format of the data



    if data["total_posts"] > 0:  # make sure there's any posts to begin with
        consecutive_repeated_posts = 0  # log consecutive repeated posts
        offset_range = math.ceil(data["total_posts"] / 20)  # figure out how many pages there are
        
        
        
        blog_name_from_data = data["blog"]["name"]
        if blog_name != blog_name_from_data:  # if the stored blog name is different from the received blog name
            conn = sqlite3.connect("posts.sqlite3")
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM blogs WHERE name = ?", (blog_name,))  # check to see if the old name is still in the blog list
            if cursor.fetchall():  # if it is
                cursor.execute("UPDATE blogs SET name = ? WHERE uuid = ?", (blog_name_from_data, blog_uuid))  # replace it
                print(f"{blog_name} renamed to {blog_name_from_data} ({blog_uuid})")
                with open("warnings.txt", "a", encoding="utf-8") as file:
                    file.write(f"{blog_name} renamed to {blog_name_from_data} ({blog_uuid})\n")
                    # write to warnings to check later
                    # so i can replace already posted things' tags
                    
            cursor.execute("SELECT * FROM posts WHERE blog = ?", (blog_name,))  # check to see if the old name is still in the post database
            if cursor.fetchall():  # if it is
                util.blog_name_change(blog_name, blog_name_from_data)  # change posts in database to reflect new name
            
            conn.commit()
            conn.close()
            
            blog_name = blog_name_from_data
            blog = [blog_name, blog_uuid]



        # progress bar
        with alive_bar(data["total_posts"], title=f"{blog_name} (#{tag})") as bar:

            for i in range(offset_range):  # for every page

                # check if the number of consecutive repeated posts has hit or passed the threshold
                if consecutive_repeated_posts >= repeated_posts_threshold:
                    print("[DEBUG] (PAGE) already have this post; hit the threshold; breaking")
                    for i in range(offset_range - i):
                        bar()  # finish off the progress bar
                    return "already have all posts"

                # get the next page of posts (unless this is the first iteration)
                if i != 0:
                    response, headers = client.posts(blog_uuid, tag=tag, offset=i * 20)  # get the next page
                    if check_rate_limit(response, headers):  # check to see if we hit the rate limit
                        response, headers = client.posts(blog_uuid, tag=tag, offset=i * 20)  # do it again if you hit the rate limit the first time

                    data = response["response"]  # get the data from the response

                for post in data["posts"]:  # for every post in this page

                    # get the html for the post
                    if post["type"] == "answer":  # ask/answer posts
                        soup = BeautifulSoup(post["answer"], "html5lib")
                    elif post["type"] == "photo":  # photo posts
                        soup = BeautifulSoup(post["caption"], "html5lib")
                    else:
                        try:  # other posts
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
                            

                    # make sure the post has any images, if we're doing that
                    if soup.find_all("figure") or not filter:

                        if current_posts:  # if we were given the list of posts already in the database
                            if post in current_posts:  # if this post is already in the database
                                consecutive_repeated_posts += 1  # that's another repeated post

                                if consecutive_repeated_posts >= repeated_posts_threshold:
                                    # if the number of consecutive repeated posts has hit or passed the threshold
                                    print("[DEBUG] (POST) already have this post; hit the threshold; breaking")
                                    return "already have all posts"  # return; we likely already have all posts
                                else:
                                    print(f"[DEBUG] already have this post; count is now {consecutive_repeated_posts}; skipping")
                                    # if this post is already in the database, but the threshold wasn't hit,
                                    # just go on to the next one instead of logging it again
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
                        print("[DEBUG] post doesn't have images; skipping")

                    bar()  # advance progress bar

    else:
        # if there's no posts
        print(f"{blog_name} (#{tag}) | no posts")
        return "no posts"
    
    if new_data == []:
        # if there's no posts with images
        print(f"{blog_name} (#{tag}) | no posts with images")
        return "no posts with images"

    return new_data


def get_posts_from_all_blogs(
    blogs: list[list[str]],  # [[blog_name, blog_uuid]]
    tags_to_search: list,
    skip: int = 0,  # skip the first n blogs in bloglist
    filter: bool = True,
):
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()

    with open("output.py", "r", encoding="utf-8") as file:
        file_text = eval(file.read())

    posts = ""

    for blog_name, blog_uuid in blogs[skip:]:
        print(blog_name)
        for tag in tags_to_search:
            posts = get_posts_from_blog([blog_name, blog_uuid], tag, filter=filter, current_posts=file_text)

            if posts == "blog not found":
                break  # stop going through tags if this blog can't be found

            if posts in ["already have all posts", "no posts", "no posts with images"]:
                print(posts)  # (this just prints whichever of those ^ three messages it was)
                continue

            if not posts:
                print("[DEBUG] no posts?!?!?!")  # pretty sure this is supposed to be impossible and that's why i did this
                print(type(posts))
                print(posts)
                exit()

            for post in posts:
                if any(x in global_tag_block_list for x in post["tags"]):
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
                except sqlite3.IntegrityError:  # if the post is already in there
                    pass  # that's fine, keep going
                    
        print("committing changes")
        conn.commit()


# get_posts_from_all_blogs(bloglist, taglist)
get_posts_from_all_blogs(bloglist, taglist)