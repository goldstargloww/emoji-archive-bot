<h1 align="center">emoji archive bot</h1>
<p align="center"><img src="https://64.media.tumblr.com/b8f595a3430b24734cc20d8ebd4d16dc/a3e8c1512c1f6774-0e/s128x128u_c1/5762af1243928a7d3d00164ccb910254a4803c72.png"></p>
<h2 align="center">a tumblr bot that archives emojis and AAC symbols from a bloglist</h2>
<p align="center">
    <a href="https://tumblr.com/emoji-archive-bot"><img alt="Check it out on Tumblr" src="https://file.garden/aG_3eJVriWyKKSnP/devins-badges/tumblr_it_cozy.svg" style="height: 64px"></a>
    <img alt="Built with Python" src="https://badges.penpow.dev/badges/built-with/python/cozy.svg">
</p>

every 30 minutes, this bot will reblog a random emoji post from those on the bloglist and automatically tag it with "#blog: \[blog name\]" and the original post's tags (minus a few that are configured to be ignored).
the database containing said posts is only updated every so often, and updates are currently triggered manually, not automatically.

i find blogs on my own, but if you'd like to be added to the bloglist, just send an ask on [tumblr](https://tumblr.com/emoji-archive-bot)!
please note that it'll likely be a while before you're added as i only update the bloglist and database every so often, but once you are, your posts should be in the database within the next few days

additionally, if you see any posts that have any problems with them (eg. there's content under the cut that hasn't been archived, the post reblogged isn't an emoji, etc), please let me know!!!
i'm very unlikely to notice otherwise, this blog has thousands of posts to go through

# FAQ

<dl>
  <dt>
    it's been more than 30 minutes and the bot hasn't posted, why's that?
  </dt>
  <dd>
    it's probably just because my computer's off or restarting. if it's been a while and i haven't said anything, though, like a few days, please check in with me!
  </dd>

  <dt>
    how exactly does the post collection and reblogging work?
  </dt>
  <dd>
    for the simple explanation: every so often, i'll tell the bot to search every blog in the bloglist for all the posts they have with certain tags.
    for every post it finds, if it has any images, it'll add that to a database. then, every 30 minutes, the bot will grab a random post it hasn't yet reblogged and reblog it.<br>
    for the more detailed explanation, check out <a href="#how-it-works">§ how it works</a>!
  </dd>

  <dt>
      how do you get this to run periodically on your computer?
  </dt>
  <dd>
      i run windows, so i use windows' Task Scheduler. the task starts at system startup and repeats every 30 minutes indefinitely. the action is to start a program and the command is <code>cmd /c python "C:\path\to\emoji-archive-bot\poster.py</code>. that's it!
  </dd>
</dl>

# how it works

this bot is split up into three parts - the scraper ([`scraper.py`](scraper.py)), the poster ([`poster.py`](poster.py)), and the database (`posts.sqlite3`).\
the scraper's job is to find all the posts to reblog, and add it to the database. the poster's job is to reblog posts from the database.

## scraping

first, the bot has a taglist and a bloglist.
the taglist is stored in the scraper's code, and includes every tag to search for.
the bloglist is stored in the database, with each blog's name and its uuid.\
for every blog in bloglist, the scraper gets all posts for every tag in the taglist.

the scraper uses a [modified version](custom_pytumblr.py) of [pytumblr](https://github.com/tumblr/pytumblr) to use tumblr's api.
for every tag, it gets up to the first 20 posts, and checks how many posts there are under this tag. if there aren't any, it skips on to the next tag, or to the next blog.
if there are any, it calculates how many "pages" of 20 posts there are, and proceeds to go through that many pages.
for every page, it goes through every post in that page, and for every post, it makes sure it has any images. if it does, and the post isn't already in the database, it saves it to the database to reblog later.
that's pretty much it!

the bot will also check if the blog's name is different than the one it has saved, and if it is, it'll update the name it stores in the database,
and write a note for me telling me to go back through the already reblogged posts to edit the tags to reflect the name change.\
there's also the option to check if each post is already in the database, and if it catches 5 repeated posts in a row, it'll skip the rest of the tag.
i keep forgetting about this though and keep forgetting to use it oops. i don't know if i've ever used it actually. ......i should do that

## posting

every 30 minutes, the bot will get every post from the database that hasn't been reblogged yet, and pick a random one.
then it adds "#blog: \[blogname\]" as a tag along with (most of) the rest of the original post's tags, and reblogs it.
then it tells the database that this post has been reblogged.\
if it turns out all posts have already been reblogged, it checks to see if it's realized this before, and if it hasn't, it makes a post on tumblr that tags me and tells me it's out of posts.

## wait what about the other files

<dl>
  <dt>
    <code>bloglist.txt</code>
  </dt>
  <dd>
    this used to be the bloglist, but now it's just how i add to the bloglist. i put one blog name per line and run <code>util.py</code>'s <code>add_to_bloglist_from_txt()</code>.
  </dd>

  <dt>
    <code>util.py</code>
  </dt>
  <dd>
    various utilities that i can run manually to make things easier, but also has the function that updates blog names when they've been changed, since i used to run that manually
  </dd>

  <dt>
    <code>warnings.txt</code>
  </dt>
  <dd>
    notes to self to check later, either when a blog isn't found, a blog got renamed, a post has a readmore*, or if the bot runs out of posts. ideally this should be empty<br>
    <sub>* in practice this one doesn't work</sub>
  </dd>
</dl>
