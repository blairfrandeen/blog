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
import shutil
import subprocess
import webbrowser
from datetime import datetime
from itertools import accumulate
from pathlib import Path
from typing import Optional

import click
from colorama import Fore
from flask_frozen import Freezer

from app import db
from app.models import Post, Visibility
from app import app, models

# Read the configuration file
config = configparser.ConfigParser()

# Check that local.cfg exists; if not, copy from default
if not os.path.exists("local.cfg"):
    print(Fore.RED, "ERROR: ", Fore.RESET, "No configuration file found!")
    shutil.copyfile("config/default.cfg", "local.cfg")
    print("local.cfg has been created for you. Please edit local.cfg and try again.")
    exit(-1)

config.read("local.cfg")
local_config = config["DEFAULT"]

# TODO: Improve type hints for Path-like objects
# TODO: Access the local_config dictionary directly when one
# of the below items is needed; removes this block of code

# TODO: Check that things imported from the config file are working
NOTES_DIRECTORY = local_config["NOTES_DIRECTORY"]
POSTS_DIRECTORY = local_config["POSTS_DIRECTORY"]
REMOTE_HOST = local_config["REMOTE_HOST"]
REMOTE_USER = local_config["REMOTE_USER"]


SSH_TARGET = f"{REMOTE_USER}@{REMOTE_HOST}"
IMAGES_DIRECTORY = "app/build/static/post_images"
SITE_ROOT = "datum-b.com"
DB_FILE = "blog.db"


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
    summary=content.split("\n")[1]
    content = replace_image_sources(content)
    content = replace_internal_links(content)
    content = remove_image_sizing_from_captions(content)
    content = add_autoplay(content)
    handle = get_handle(title)
    with app.app_context():
        new_post = Post(
            title=title,
            content=content,
            summary=summary,
            handle=handle,
            visibility=Visibility.HIDDEN,
        )
        db.session.add(new_post)
        db.session.commit()

    return new_post


@cli.command(name="freeze")
def freeze() -> None:
    """Freeze the static site."""
    freezer = Freezer(app)

    @freezer.register_generator
    def blog_post():
        for post in models.Post.query.filter(
            Post.visibility.in_([Visibility.PUBLISHED, Visibility.UNLISTED]),
        ):
            yield {"post_handle": post.handle}

    freezer.freeze()


@cli.command(name="preview")
def preview() -> None:
    """Preview the static site in your default browser."""
    webbrowser.open(os.path.join(os.getcwd(), "app", "build", "index.html"))


@cli.command(name="restart")
def restart_server() -> None:
    """Restart the flask app on the server"""
    restart_cmd = (
        f"ssh {SSH_TARGET} touch /home/{REMOTE_USER}/{SITE_ROOT}/tmp/restart.txt"
    )
    os.popen(restart_cmd)


@cli.command(name="sync")
def sync_with_server() -> None:
    """Sync the static site with the server."""
    sync_cmd = f"rsync -rv app/build/* {SSH_TARGET}:{SITE_ROOT}"
    os.popen(sync_cmd)


@cli.command(name="list")
def list_posts() -> None:
    """List all posts in the database. Posts
    colored in grey are hidden, yellow are unlisted."""
    with app.app_context():
        for post in Post.query.all():
            if post.visibility == Visibility.PUBLISHED:
                print(Fore.GREEN, end="")
            if post.visibility == Visibility.UNLISTED:
                print(Fore.YELLOW, end="")
            print(post, Fore.RESET)


@cli.command(name="hide")
@click.argument("post_id", type=int)
def set_vis_hidden(post_id: int) -> None:
    """Set a post's visibility to hidden. Hidden posts won't show up on the front page or
    RSS feed, and won't be accessible at their normal url.

    Arguments:
        post_id:    The id of the post to be toggled
    """
    _set_visibility(post_id, Visibility.HIDDEN)


@cli.command(name="unlist")
@click.argument("post_id", type=int)
def set_vis_unlisted(post_id: int) -> None:
    """Set a post's visibility to unlisted. Unlisted posts won't show up on the front page or
    RSS feed, but will be accessible at their normal URL.

    Arguments:
        post_id:    The id of the post to be toggled
    """
    _set_visibility(post_id, Visibility.UNLISTED)


@cli.command(name="publish")
@click.argument("post_id", type=int)
def set_vis_published(post_id: int) -> None:
    """Set a post's visibility to published. Published posts are fully visible on the
    front page and RSS feed.

    Arguments:
        post_id:    The id of the post to be toggled
    """
    _set_visibility(post_id, Visibility.PUBLISHED)


def _set_visibility(post_id: int, visibility) -> None:
    with app.app_context():
        target_post = db.session.get(Post, post_id)
        if target_post is None:
            raise click.BadParameter(f"Post id {post_id} does not exist in database!")
        target_post.visibility = visibility
        db.session.commit()


@cli.command(name="delete")
@click.argument("post_id", type=int)
def delete_post(post_id: int) -> None:
    """Delete a post"""
    with app.app_context():
        target_post = db.session.get(Post, post_id)
        db.session.delete(target_post)
        db.session.commit()


@cli.command(name="edit")
@click.argument("post_id", type=int)
def edit_post(post_id: int) -> None:
    """Edit the content of a post using vim.

    Arguments:
        post_id:    The id of the post to be edited
                    Use `blog list` to list posts.
    """
    with app.app_context():
        target_post = db.session.get(Post, post_id)
        edited_content = click.edit(target_post.content, editor="vim")
        target_post.content = edited_content
        # change the post updated timestamp
        target_post.post_update_ts = datetime.utcnow()
        db.session.commit()


def copy_post(post_file: Optional[str] = None) -> str:
    """Copy a target file and any associated images.
    to the posts directory. Return the path of the
    copied post."""
    # Ensure posts and images directories exist
    for directory in [POSTS_DIRECTORY, IMAGES_DIRECTORY]:
        _mkdir_if_not_exists(directory)

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
        # check for resizing in caption:
        resize_arg = get_resize_arg(image[1])
        img_path = Path(image[0])
        img_path = shutil.copyfile(
            os.path.join(NOTES_DIRECTORY, img_path),
            os.path.join(IMAGES_DIRECTORY, img_path),
        )
        if resize_arg:
            reduced_img_path = resize_image(img_path, resize_arg)
            if reduced_img_path:
                shutil.move(
                    reduced_img_path,
                    os.path.join(IMAGES_DIRECTORY, reduced_img_path),
                )
                print("Copied ", reduced_img_path)
        print("Copied ", img_path)

    # Copy the post to the local directory
    new_path = shutil.copyfile(post_file, os.path.join(POSTS_DIRECTORY, file_name))

    return new_path


def _mkdir_if_not_exists(directory: str) -> None:
    """Create a directory if it doesn't already exist"""
    if not os.path.isdir(directory):
        try:
            os.mkdir(directory)
        except FileExistsError:
            print(f"ERROR: '{directory}' exists and is not a directory!")
            print("\tHint: Remove this file and try again.")
            exit(-1)


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
    # strip the title from the document itself
    html_str = html_str.split("</h1>")[1]
    # ignore everything after the horizontal rule for now. This is a temporary
    # workaround, but is the cause of issue #27
    html_str = html_str.split("<hr />")[0]

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


def find_html_images(html_source: str) -> list[str]:
    """Find all image OR video paths in an HTML source."""
    image_re = re.compile(r'<(?:img)?(?:video)? src="(.+?)"')
    return re.findall(image_re, html_source)


def replace_image_sources(html_source: str, prefix: str = "../static/post_images") -> str:
    """Replace image sources with the correct path, and create links to any full-size
    images that exist.

    The correct path is created by prepending ``prefix`` to the image path.

    If there is an image in the ``IMAGES_DIRECTORY`` that matches the pattern
    <STEM>_reduced.jpg, where <STEM> is the stem of the image file name:
    - Replace the image with the reduced version
    - Make a link around the `<img>` tag to the full size version

    Arguments
    ---------
    html_source:
        Source HTML
    prefix:
        Prefix to prepend to image paths

    Returns
    -------
    HTML source with correct image paths and links to full size images

    """
    def replace_image(match):
        img_src = match.group(1)
        stem, ext = os.path.splitext(img_src)
        reduced_img = f"{stem}_reduced{ext}"
        full_img = os.path.join(IMAGES_DIRECTORY, img_src)

        if os.path.exists(full_img):
            reduced_img_path = os.path.join(prefix, reduced_img)
            full_img_path = os.path.join(prefix, img_src)

            if os.path.exists(os.path.join(IMAGES_DIRECTORY, reduced_img)):
                return f'<a href="{full_img_path}"><img src="{reduced_img_path}" alt="" /></a>'
            else:
                return f'<img src="{full_img_path}" alt="" />'
        else:
            return match.group(0)

    return re.sub(r'<img\s+src="(.*?)" alt=".*" />', replace_image, html_source)


# TODO: Make this an optional flag
def add_autoplay(html_source: str) -> str:
    """Modify video tags so videos are autoplay, looped, and muted."""
    video_regex = re.compile(r'<video src=".*?>')
    for video_tag in re.findall(video_regex, html_source):
        html_source = html_source.replace(
            video_tag, f"{video_tag[:-1]} autoplay muted loop>"
        )
    return html_source


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
    internal_links: list[tuple[str, str]] = list(
        map(parse_internal_link, internal_link_text)
    )

    # Validate the internal links and get handles
    internal_link_handles = list(map(get_link_handle, internal_links))

    # Replace the links in the HTML string
    for index, link in enumerate(internal_link_text):
        html_str = html_str.replace(
            f"[[{link}]]", generate_link_href(internal_link_handles[index])
        )
    # Return new HTML string
    return html_str


def get_resize_arg(caption: str) -> Optional[str]:
    """Given an image caption, return the resizing argument passed to convert if an
    image size was given."""
    # Regular expressions to match different patterns
    width_pattern = r"\|(\d+)$"
    height_pattern = r"\|x(\d+)$"
    dimensions_pattern = r"\|(\d+)x(\d+)$"

    # Check for width only
    match = re.search(width_pattern, caption)
    if match:
        width = match.group(1)
        return f"{width}x>"

    # Check for height only
    match = re.search(height_pattern, caption)
    if match:
        height = match.group(1)
        return f"x{height}>"

    # Check for both width and height
    match = re.search(dimensions_pattern, caption)
    if match:
        width, height = match.groups()
        return f"{width}x{height}"

    # If no pattern matches, return None
    return None


def resize_image(
    source_path: str | os.PathLike, resize_arg: str, quality: float = 0.8
) -> Optional[Path]:
    """Resize an image using ImageMagick convert.

    Arguments
    ---------
    source_path:    Path to image to resize
    resize_arg:     Argument to pass to `convert` to resize image
    quality:        JPG quality. Default 80.

    Returns
    -------
    Path to reduced-size image.
    """
    source_path = Path(source_path).resolve()
    if source_path.stem in [
        ".svg",
        ".mp4",
        ".gif",
    ]:  # Don't try this on svg, mp4, or gif
        return None

    out_path = source_path.parent / Path(source_path.stem + "_reduced.jpg")
    cmd = [
        "convert",
        source_path,
        "-resize",
        resize_arg,
        "-quality",
        str(int(quality * 100)),
        "-strip",
        str(out_path),
    ]
    print(f"Running {cmd}")
    subprocess.run(cmd, check=True)

    return out_path


def generate_link_href(link: tuple[str, str]) -> str:
    return f"<a href='/blog/{link[0]}'>{link[1]}</a>"


def get_link_handle(link: tuple[str, str]) -> tuple[str, str]:
    """Given a post title, return the handle.
    Verify that the handle exists and the post is not hidden"""
    post_title = link[0]
    link_text = link[1]
    handle = get_handle(post_title)
    with app.app_context():
        link_query = Post.query.filter_by(handle=handle).filter_by(
            visibility=Visibility.PUBLISHED
        )
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


def remove_image_sizing_from_captions(html: str) -> str:
    """
    Removes any image sizing information from <figcaption> tags in HTML.

    Arguments
    ---------
    html: The HTML string to process.

    Returns
    -------
    The HTML string with image sizing information removed from <figcaption> tags.
    """

    # Regular expression pattern to match <figcaption> tags and their content
    figcaption_pattern = r"<figcaption>(.*?)</figcaption>"

    def remove_sizing(match):
        # Remove the '|' and everything after it from the matched text
        caption = match.group(1).split("|")[0]
        return f"<figcaption>{caption}</figcaption>"

    # Replace the matched <figcaption> tags with the new content
    cleaned_html = re.sub(figcaption_pattern, remove_sizing, html)

    return cleaned_html


if __name__ == "__main__":
    cli()
