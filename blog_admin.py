"""
blog_admin.py
Tools for posting & administering my roll-your-own blog.

My blog entries are typically composed using Obsidian in Windows,
and the blog administration and backend is done using WSL Ubuntu.
This set of tools exists in order to easily transfer files
between the two systems, and remove the friction in doing so.
"""

import configparser
import os
import re
from datetime import datetime, date
from itertools import accumulate
from pprint import pprint
from typing import Optional
from shutil import copyfile

import click
from colorama import Fore

from app import db
from app.models import Post

# Read the configuration file
config = configparser.ConfigParser()
config.read("local.cfg")
local_config = config["DEFAULT"]

# TODO: Improve type hints for Path-like objects
# TODO: Access the local_config dictionary directly when one
# of the below items is needed; removes this block of code
NOTES_DIRECTORY = local_config["NOTES_DIRECTORY"]
POSTS_DIRECTORY = local_config["POSTS_DIRECTORY"]
IMAGES_DIRECTORY = local_config["IMAGES_DIRECTORY"]
WEBHOST = local_config["WEBHOST"]


@click.group()
def cli():
    pass


@cli.command(name="post")
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
    content = replace_internal_links(content)
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


@cli.command(name="push_db")
def push_db() -> None:
    """Push the updated blog database
    to the datum_b server."""
    # push the database file
    scp_cmd = f"scp blog.db {WEBHOST}:datum-b.com"
    os.popen(scp_cmd)


@cli.command(name="restart")
def restart_server() -> None:
    """Restart the flask app on the server"""
    restart_cmd = f"ssh {WEBHOST} touch /home/***REMOVED***/datum-b.com/tmp/restart.txt"
    os.popen(restart_cmd)


@cli.command(name="list")
def list_posts() -> None:
    """List all posts in the database. Posts
    colored in grey are hidden."""
    for post in Post.query.all():
        if not post.hidden:
            print(Fore.GREEN, end="")
        print(post, Fore.RESET)


@cli.command(name="push_images")
@click.argument("post_id", type=int)
def push_post_images(post_id: int) -> None:
    """Push images associated with a post_id
    to the web server.

    Arguments:
        post_id:    The id of the post to push images for.
                    Use `blog list` to list posts.
    """
    post_content = db.session.get(Post, post_id).content
    for image in find_html_images(post_content):
        img_path = os.path.join(IMAGES_DIRECTORY, os.path.basename(image))
        scp_cmd = f"scp {img_path} {WEBHOST}:datum-b.com/app/static/post_images"
        os.popen(scp_cmd)


@cli.command(name="toggle")
@click.argument("post_id", type=int)
def toggle_hidden(post_id: int) -> None:
    """Toggle a post's hidden status.
    Arguments:
        post_id:    The id of the post to be toggled
                    Use `blog list` to list posts.
    """
    target_post = db.session.get(Post, post_id)
    if target_post is None:
        raise click.BadParameter(f"Post id {post_id} does not exist in database!")
    target_post.hidden = False if target_post.hidden else True
    db.session.commit()


@cli.command(name="edit")
@click.argument("post_id", type=int)
def edit_post(post_id: int) -> None:
    """Edit the content of a post using vim.

    Arguments:
        post_id:    The id of the post to be edited
                    Use `blog list` to list posts.
    """
    target_post = db.session.get(Post, post_id)
    edited_content = click.edit(target_post.content, editor="vim")
    target_post.content = edited_content
    # change the post updated timestamp
    target_post.post_update_ts = datetime.utcnow
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
        # TODO: Investigate why code that worked on wsl removed the first
        # charactar for file_selection. Seems non-sensical and is working on Ubuntu
        file_handle = os.path.join(search_dir + file_selection.strip())
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


def get_internal_links(html_str: str) -> list[str]:
    # Find all inter-blog links
    internal_link_re = re.compile(r"\[\[(.+?)\]\]")

    # List of all links found in html string as strings
    internal_link_text = re.findall(internal_link_re, html_str)

    return internal_link_text


def replace_internal_links(html_str: str) -> str:
    # Get internal link text
    internal_link_text: list[str] = get_internal_links(html_str)

    # Parse the internal links
    # Links in html string as tuples of title, link text
    internal_links: list[tuple[str, str]] = list(map(parse_internal_link, internal_link_text))

    # Validate the internal links and get handles
    internal_link_handles = list(map(get_link_handle, internal_links))

    # Replace the links in the HTML string
    for index, link in enumerate(internal_link_text):
        html_str = html_str.replace(f"[[{link}]]", generate_link_href(internal_link_handles[index]))
    # Return new HTML string
    return html_str


def generate_link_href(link: tuple[str, str]) -> str:
    return f"<a href='/blog/{link[0]}'>{link[1]}</a>"


def get_link_handle(link: tuple[str, str]) -> tuple[str, str]:
    """Given a post title, return the handle.
    Verify that the handle exists and the post is not hidden"""
    post_title = link[0]
    link_text = link[1]
    handle = get_handle(post_title)
    link_query = Post.query.filter_by(handle=handle).filter_by(hidden=False)
    if len(list(link_query)) == 1:
        return handle, link_text
    raise Exception(f"No unhidden posts found for {handle}")


def parse_internal_link(link: str) -> tuple[str, str]:
    """For a given inter-blog link, return the title of the post being linked to
    and the link text to use."""
    link_elements = link.split("|")
    if len(link_elements) == 1:
        return (link_elements[0], link_elements[0])
    return (link_elements[0], link_elements[1])


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
    words = ["".join([letter for letter in word if letter.isalnum()]) for word in title_str.split()]
    # truncate to 32 characters or fewer
    # don't break across a word
    letter_counts = accumulate([len(w) + 1 for w in words], initial=len(words[0]))
    last_index = sum(map(lambda x: x <= max_length, letter_counts))
    # replace spaces with underscores
    # make all lowercase
    return "_".join(words[0:last_index]).lower()


if __name__ == "__main__":
    cli()
