# Datum-B Blog
Code for [Datum-B](https://datum-b.com)

## Process for posting:
1. Write post using Obsidian. Proofread, edit, etc.
2. 
```python
>>> import blog_admin as ba
>>> ba.make_post()
>>> ba.list_posts()
>>> ba.toggle_hidden(<post_id>) # if required
>>> ba.push_post_images(post_id) # if required
>>> ba.push_db()
```
3. Enjoy.
