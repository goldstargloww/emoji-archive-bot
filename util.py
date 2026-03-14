import sqlite3, re, os
from alive_progress import alive_bar
import custom_pytumblr as pytumblr
from dotenv import load_dotenv
import datetime

load_dotenv()
client = pytumblr.TumblrClient(
    os.getenv('CONSUMER_KEY'),
    os.getenv('CONSUMER_SECRET'),
    os.getenv('OAUTH_TOKEN'),
    os.getenv('OAUTH_TOKEN_SECRET')
)


def blog_name_change(prev: str, new: str):
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM posts WHERE blog = '{prev}'")

    results = cursor.fetchall()

    with alive_bar(len(results), title=f"posts: {prev} -> {new}") as bar:
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

def add_to_bloglist_from_txt():
    with open("bloglist.txt") as file:
        bloglist = [blog.removesuffix("\n") for blog in file.readlines()]
    bloglist.sort()
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()
    
    with alive_bar(len(bloglist)) as bar:
        for blog in bloglist:
            blog_info = client.blog_info(blog)[0]
            active = True
            
            if blog_info["meta"]["status"] == 404:
                print(f"{blog} not found")
                with open("warnings.txt", "a", encoding="utf-8") as file:
                    file.write(f"{blog} not found\n")
                active = False
                    
            uuid = blog_info["response"]["blog"]["uuid"]
            
            try:
                cursor.execute(f"INSERT INTO blogs (name, uuid) VALUES (?, ?)", (blog, uuid))
                bar()
            except sqlite3.IntegrityError:
                bar()
                continue
            
            
            
    conn.commit()
    conn.close()
    
def update_bloglist_names_and_status():
    conn = sqlite3.connect("posts.sqlite3")
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM blogs WHERE active = 1")
    bloglist: list[tuple[str, str]] = [(blog[0], blog[1]) for blog in cursor.fetchall()]

    with alive_bar(len(bloglist)) as bar:
        for name, uuid in bloglist:
            blog_info = client.blog_info(uuid)[0]
            
            if blog_info["meta"]["status"] == 404:
                print(f"{name} not found; marking inactive")
                conn.execute(
                    f"UPDATE blogs SET active = 0 WHERE uuid = ?",
                    (uuid,)
                )
            else:
                response_name = blog_info["response"]["blog"]["name"]
                if name != response_name:
                    print(f"{name} seems to now be {response_name}; updating database")
                    cursor.execute(f"SELECT * FROM posts WHERE blog = ?", (name,))
                    results = cursor.fetchall()
                    for result in results:
                        post_tags: str = result[3]
                        post_tags = post_tags.replace(name, response_name)
                        post_id = result[1]
                        conn.execute(
                            f"UPDATE posts SET blog = ? WHERE post_id = ?",
                            (response_name, post_id)
                        )
                        conn.execute(
                            f"UPDATE posts SET tags = ? WHERE post_id = ?",
                            (post_tags, post_id)
                        )
            bar()

    conn.commit()
    conn.close()