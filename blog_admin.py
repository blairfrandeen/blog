import os
import re
from datetime import datetime, date
from itertools import accumulate
from typing import Optional
from shutil import copyfile

from app import db
from app.models import Post

NOTES_DIRECTORY = "/mnt/c/users/blair/my drive/notes"
POSTS_DIRECTORY = "posts"


def make_post(markdown_file: Optional[str] = None) -> Post:
    """Generate a post from a markdown source file."""
    if not markdown_file:
        markdown_file = copy_post()
    title, content = parse_markdown(markdown_file)
    handle = get_handle(title)
    new_post = Post(
        title=title,
        content=content,
        handle=handle,
        hidden=True,
    )
    db.session.add(new_post)
    db.session.commit()

    return new_post


def parse_markdown(markdown_file: str) -> tuple[str, str]:
    """Parse a markdown file into HTML"""
    if not os.path.isfile(markdown_file):
        raise FileNotFoundError(f"Error: {markdown_file} not found.")
    pdoc_cmd = f'pandoc -f markdown -t html "{markdown_file}"'
    pdoc_output = os.popen(pdoc_cmd)
    html_str = pdoc_output.read()
    title = get_title(html_str)
    # ignore everything after the horizontal rule for now
    html_str = html_str.split("</h1>")[1].split("<hr />")[0]

    return title, html_str


def find_new_entry() -> str:
    os.chdir(NOTES_DIRECTORY)
    file_selection = os.popen("fzf")
    file_handle = NOTES_DIRECTORY + file_selection.read().strip()[1:]
    os.chdir(os.path.join(os.path.expanduser("~"), "site"))
    return file_handle


def copy_post() -> str:
    post_dir = find_new_entry()
    file_name = post_dir.split("/")[-1]
    new_path = copyfile(post_dir, os.path.join(POSTS_DIRECTORY, file_name))
    return new_path


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
