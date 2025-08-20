taglist = [
    "emoji",
    "emojis",
    "emote",
    "emotes",
    "custom emoji",
    "custom emojis",
    "custom emote",
    "custom emotes",
    "discord emoji",
    "discord emojis",
    "discord emote",
    "discord emotes",
    "custom discord emoji",
    "custom discord emojis",
    "custom discord emote",
    "custom discord emotes",
    "my emojis",
    "nonverbal emote",
    "nonverbal emotes",
    "nonverbal emoji",
    "nonverbal emojis",
    "emoji blog",
    "emote blog",
    "f2u emoji",
    "ftu emoji",
    "aac emoji",
    "aac emote",
    "aac image",
    "aac symbol",
    "aac symbols",
    "aac emoji",
    "emoji art",
    "emoji artist",
    "emote artist",
    "cute emoji",
    "cute emojis",
    "cute emote",
    "cute emotes",
    "discord emoji blog",
    "word emojis",
    "wordmoji",
    "word emoji",
    "word moji",
    "wordmojis",
    "word emojis",
    "word mojis"
]


def count_tags():
    with open("output.py", "r", encoding="utf-8") as file:
        data = eval(file.read())
        
    tag_counts = {}
    for tag in taglist:
        tag_counts[tag] = 0
    for post in data:
        for tag in post["tags"]:
            try:
                tag_counts[tag] += 1
            except KeyError:
                tag_counts[tag] = 1
    
    with open("output2.py", "w", encoding="utf-8") as file:
        file.write(str(sorted(tag_counts.items(), key=lambda kv: (kv[1], kv[0]))))
        
count_tags()