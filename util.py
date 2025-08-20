import sqlite3, re, os
from alive_progress import alive_bar
import custom_pytumblr as pytumblr
from dotenv import load_dotenv

load_dotenv()
client = pytumblr.TumblrClient(
    os.getenv('CONSUMER_KEY'),
    os.getenv('CONSUMER_SECRET'),
    os.getenv('OAUTH_TOKEN'),
    os.getenv('OAUTH_TOKEN_SECRET')
)


def blog_name_change(prev, new):
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM posts WHERE blog = '{prev}'")

    results = cursor.fetchall()

    with alive_bar(len(results)) as bar:
        for result in results:
            post_tags: str = result[3]  # re.sub(r"(\w)\"(\w)", "\1\'\2", result[3])
            post_tags = post_tags.replace(prev, new)
            post_id = result[1]
            conn.execute(
                f"UPDATE posts SET blog = ? WHERE post_id = ?",
                (new, post_id)
            )
            conn.execute(
                f"UPDATE posts SET tags = ? WHERE post_id = ?",
                (post_tags, post_id)
            )
            bar()

    conn.commit()
    conn.close()

def build_bloglist_from_txt():
    with open("bloglist.txt") as file:
        bloglist = [blog.removesuffix("\n") for blog in file.readlines()]
    bloglist.sort()
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blogs")
    
    with alive_bar(len(bloglist)) as bar:
        for blog in bloglist:
            blog_info = client.blog_info(blog)[0]
            
            if blog_info["meta"]["status"] == 404:
                print(f"{blog} not found")
                with open("warnings.txt", "a", encoding="utf-8") as file:
                    file.write(f"{blog} not found\n")
                bar()
                continue
                    
            uuid = blog_info["response"]["blog"]["uuid"]
            
            try:
                cursor.execute(f"INSERT INTO blogs (name, uuid) VALUES (?, ?)", (blog, uuid))
            except sqlite3.IntegrityError:
                continue
            
            bar()
            
    conn.commit()
    conn.close()

