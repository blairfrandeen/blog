"""
blog_admin.py
Tools for posting & administering my roll-your-own blog.

My blog entries are typically composed using Obsidian in Windows,
and the blog administration and backend is done using WSL Ubuntu.
This set of tools exists in order to easily transfer files
between the two systems, and remove the friction in doing so.
"""

import os
import re
from datetime import datetime, date
from itertools import accumulate
from pprint import pprint
from typing import Optional
from shutil import copyfile

from colorama import Fore

from app import db
from app.models import Post

# Directory on computer where posts are composed
# Equal to Obsidian vault root
NOTES_DIRECTORY = "/mnt/c/users/blair/my drive/notes"

# Location of posts files in site working directory
POSTS_DIRECTORY = "./posts"

# Location of images for the flask app
IMAGES_DIRECTORY = "./app/static/post_images"

# WEBHOST SSH TARGET
WEBHOST = "***REMOVED***@aurora.***REMOVED***.com"


# TODO: Improve type hints for Path-like objects


def make_post(markdown_file: Optional[str] = None) -> Post:
    """Generate a post from a markdown source file. Adds
    the post to the blog database.

    Arguments:
        markdown_file:  Markdown file to generate the post from.
                        If no argument passed, fzf search is opened
                        in the notes directory.

    Returns:
        Post object.
    """
    if not markdown_file:
        # If no specific file path passed, open
        # fuzzy finder search
        markdown_file = copy_post()
    title, content = parse_markdown(markdown_file)
    content = replace_image_sources(content)
    handle = get_handle(title)
    new_post = Post(
        title=title,
        content=content,
        handle=handle,
        hidden=False,
    )
    db.session.add(new_post)
    db.session.commit()

    return new_post


def push_db() -> None:
    """Push the updated blog database
    to the datum_b server."""
    # push the database file
    scp_cmd = f"scp blog.db {WEBHOST}:datum-b.com"
    os.popen(scp_cmd)


def restart_server() -> None:
    """Restart the flask app on the server"""
    restart_cmd = f"ssh {WEBHOST} touch /home/***REMOVED***/datum-b.com/tmp/restart.txt"
    os.popen(restart_cmd)


def list_posts() -> None:
    """List all posts in the database. Posts
    colored in grey are hidden."""
    for post in Post.query.all():
        if post.hidden:
            print(Fore.WHITE, end="")
        print(post, Fore.RESET)


def push_post_images(post_id: int) -> None:
    """Push images associated with a post_id
    to the web server.

    Arguments:
        post_id:    Post ID
    """
    post_content = db.session.get(Post, post_id).content
    for image in find_html_images(post_content):
        img_path = os.path.join(IMAGES_DIRECTORY, os.path.basename(image))
        scp_cmd = f"scp {img_path} {WEBHOST}:datum-b.com/app/static/post_images"
        os.popen(scp_cmd)


def toggle_hidden(post_id: int) -> None:
    """Toggle a post's hidden status.
    Arguments:
        post_id:    The id of the post to be toggled
    """
    target_post = db.session.get(Post, post_id)
    target_post.hidden = False if target_post.hidden else True
    db.session.commit()


def find_html_images(html_source: str) -> list[str]:
    """Find all image paths in an HTML source."""
    image_re = re.compile(r'<img src="(.+?)"')
    return re.findall(image_re, html_source)


def replace_image_sources(html_source: str) -> str:
    """Replace links to images with the correct path."""
    for image in find_html_images(html_source):
        html_source = html_source.replace(image, f"/static/post_images/{image}")
    return html_source


def copy_post(post_file: Optional[str] = None) -> str:
    """Copy a target file and any associated images.
    to the posts directory. Return the path of the
    copied post."""
    if not post_file:
        # Get the new entry using fzf
        post_file = fuzzy_find_new_entry()
    file_name = os.path.basename(post_file)
    if post_file is None:
        print("Aborted.")
        exit(-1)

    # Get the text from the entry
    with open(post_file, "r") as markdown_fh:
        markdown_text = "\n".join([line for line in markdown_fh])

    # Find any images that are part of the post
    post_images = find_markdown_images(markdown_text)
    for image in post_images:
        img_path = copyfile(
            os.path.join(NOTES_DIRECTORY, image[0]),
            os.path.join(IMAGES_DIRECTORY, image[0]),
        )
        print("Copied ", img_path)

    # Copy the post to the local directory
    new_path = copyfile(post_file, os.path.join(POSTS_DIRECTORY, file_name))

    return new_path


def fuzzy_find_new_entry(search_dir: str = NOTES_DIRECTORY) -> Optional[str]:
    """User fuzzy finder to identify a file in a given
    directory. Return the file path of the selected file."""
    starting_dir = os.getcwd()
    os.chdir(search_dir)
    file_selection = os.popen("fzf").read()
    os.chdir(starting_dir)
    if file_selection:
        file_handle = os.path.join(search_dir + file_selection.strip()[1:])
        return file_handle
    return None


def parse_markdown(markdown_file: str) -> tuple[str, str]:
    """Parse a markdown file into HTML"""
    if not os.path.isfile(markdown_file):
        raise FileNotFoundError(f"Error: {markdown_file} not found.")
    # TODO: use the --extract_media=DIR pandoc option
    # instead of having to find them with copy_post
    pdoc_cmd = f'pandoc -f markdown+implicit_figures -t html5 "{markdown_file}"'
    pdoc_output = os.popen(pdoc_cmd)
    html_str = pdoc_output.read()
    title = get_title(html_str)
    # ignore everything after the horizontal rule for now
    html_str = html_str.split("</h1>")[1].split("<hr />")[0]

    return title, html_str


def find_markdown_images(markdown_text: str) -> list[tuple[str, str]]:
    """Look through a markdown file and identify any images that are embedded.
    Assumes images are in same folder as markdown file.

    Arguments:
        markdown_text:  text of markdown to search.

    Returns:
        List of tuples containing image path and caption.
    """

    images = []
    # Find images in the form ![[image.jpg|Caption]]
    wiki_img_re = re.compile(r"!\[\[([\w.-]+)\|?(.+)?\]\]")
    images += re.findall(wiki_img_re, markdown_text)

    # Find images in the form ![Caption](Image.jpg)
    md_img_re = re.compile(r"!\[(.*)\]\((.+)\)")

    # Switch order to match wiki format
    images += [(img, cap) for cap, img in re.findall(md_img_re, markdown_text)]
    return images


def get_title(html_str: str) -> str:
    """Get the post title from the markdown source file"""
    title_re = re.compile("(?<=>).*(?=</h1>)")
    title_search = re.findall(title_re, html_str)
    if len(title_search) < 1:
        raise Exception(f"No title found in {html_str}")
    return re.findall(title_re, html_str)[0]


def get_handle(title_str: str, max_length: int = 32) -> str:
    """Make a handle from a post title"""
    # remove all non alphanumerics
    words = [
        "".join([letter for letter in word if letter.isalnum()])
        for word in title_str.split()
    ]
    # truncate to 32 characters or fewer
    # don't break across a word
    letter_counts = accumulate([len(w) + 1 for w in words], initial=len(words[0]))
    last_index = sum(map(lambda x: x <= max_length, letter_counts))
    # replace spaces with underscores
    # make all lowercase
    return "_".join(words[0:last_index]).lower()
