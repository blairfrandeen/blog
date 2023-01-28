# Datum-B Blog
Code for [Datum-B](https://datum-b.com)

## Installation
Clone this repository:
```
git clone git@github.com:blairfrandeen/blog.git && cd blog
```
Make a virtual environment and activate it:
```
python -m venv venv && . venv/bin/activate
```
Install the required dependencies:
```
pip install -r requirements.txt
```
Install this package locally for the entry points:
```
pip install --editable .
```

Make sure [pandoc](https://pandoc.org/installing.html) is installed (`sudo apt install pandoc`)

## Process for posting:
1. Write post using Obsidian. Post must have an H1 header (line starts with `# `. Everything after the first horizontal rule (`---`) will be ignored.

Images should be embedded into the post using the following format: `![Caption](image_file.jpg)`. Note that this is not the standard format for Obsidian.

Links to other posts can be made as normal, provided those other posts exist in both the live website and the Obsidian vault, and _the titles have not been changed_.

Proofread, edit, etc.
2. `blog post`. This selects the post from available files, grabs any associated images, parses the content from Markdown to HTML using pandoc, and adds it to the database.
3. Preview the post using `flask run` and then navigate to https://127.0.0.1:5000.
4. If satisfied, run `blog push_db`, followed by `blog push_images` if required. If unsatisfied, you can do `blog delete` or `blog edit` followed by the post ID.
3. Enjoy.
