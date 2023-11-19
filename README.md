# Datum-B Blog
Code for [Datum-B](https://datum-b.com). This is a simple blog that runs off of Flask.

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

## First Time Set-Up
If you don't yet heave a `local.cfg` file, simply run `blog` and one will be created for you by copying [the default config file](https://github.com/blairfrandeen/blog/blob/master/config/default.cfg). You'll need to manually edit this file to fill out the `REMOTE_HOST` and `REMOTE_USER` keys to match the SSH login credentials for your web hosting provider.

If you already have a site up an running, you'll want to download everything via ssh to your local machine to match, or otherwise copy the blog.db file to the root folder of this repository.

If you are starting fresh, run
```
flask db upgrade
```
to initialize the blog.db file that the application needs to run.

## Process for posting:
1. Write post using Obsidian. Post must have an H1 header (line starts with `# `. Everything after the first horizontal rule (`---`) will be ignored.

Images should be embedded into the post using the following format: `![Caption](image_file.jpg)`. Note that this is not the standard format for Obsidian. If it's desired for the caption to show up, make sure to have the image be the only thing on the line; otherwise the images will be inline and the captions will be hidden.

Links to other posts can be made as normal, provided those other posts exist in both the live website and the Obsidian vault, and _the titles have not been changed_.

Proofread, edit, etc.

2. `blog post`. This selects the post from available files, grabs any associated images, parses the content from Markdown to HTML using pandoc, and adds it to the database.
3. Preview the post using `flask run` and then navigate to https://127.0.0.1:5000.
4. If satisfied, run `blog push_db`, followed by `blog push_images` if required. If unsatisfied, you can do `blog delete` or `blog edit` followed by the post ID.
3. Enjoy.
