import pytest

import blog_admin
from blog_admin import (
    find_markdown_images,
    generate_link_href,
    get_handle,
    get_internal_links,
    parse_internal_link,
    replace_internal_links,
    get_resize_arg,
)

@pytest.mark.parametrize("caption, expected_output", [
    ("My Image |500", "500x>"),
    ("My Image |x600", "x600>"),
    ("My Image |640x480", "640x480"),
    ("My Image", None),
    ("My Image |invalid", None),
    ("My Image |x", None),
    ("My Image |x600x800", None),
])
def test_get_resize_arg(caption, expected_output):
    """
    Test the get_resize_arg function with various input captions.

    Args:
        caption (str): The input caption string.
        expected_output (str or None): The expected output string or None.
    """
    output = get_resize_arg(caption)
    assert output == expected_output

@pytest.mark.parametrize(
    "html_string, video_tag",
    [
        (
            '<video src="/static/post_images/sudoku-demo.mp4" control="">blah blah blah</video>',
            '<video src="/static/post_images/sudoku-demo.mp4" control="" autoplay muted loop>blah blah blah</video>',
        )
    ],
)
def test_add_autoplay(html_string, video_tag):
    assert blog_admin.add_autoplay(html_string) == video_tag


@pytest.mark.parametrize(
    "title, handle, max_length",
    [
        ("Time to Dual Class", "time_to_dual_class", 24),
        (
            "This title is way too long and self induldling, nobody will read it.",
            "this_title_is_way_too",
            24,
        ),
        ("It's 100% time to 'make bank'", "its_100_time_to_make", 20),
        ("test", "test", 4),
    ],
)
def test_get_handle(title, handle, max_length):
    assert get_handle(title, max_length=max_length) == handle


@pytest.mark.parametrize(
    "md_string, img_list",
    [
        ("", []),
        ("![](image.jpg)", [("image.jpg", "")]),
        ("![Caption](image.jpg)", [("image.jpg", "Caption")]),
        ("Something something.\n![[image.jpg]]\nSomething else.", [("image.jpg", "")]),
        (
            "BLah blah.\n![[image.jpg|A nice image]]\nSomething else.",
            [("image.jpg", "A nice image")],
        ),
        (
            "First image:\n![[this_is-me.PNG|Caption 1]]\nSecond image:![[something.gif|A complicated & long caption that nobody likes.]].",
            [
                ("this_is-me.PNG", "Caption 1"),
                ("something.gif", "A complicated & long caption that nobody likes."),
            ],
        ),
        (
            "A wiki image: ![[wiki-img.jpg|Wiki Caption]]\nA markdown image: ![Markdown Image](md_img.gif)\n",
            [("wiki-img.jpg", "Wiki Caption"), ("md_img.gif", "Markdown Image")],
        ),
    ],
)
def test_find_images(md_string, img_list):
    assert find_markdown_images(md_string) == img_list


@pytest.mark.parametrize(
    "html_string, images",
    [
        (
            '<video src="/static/post_images/sudoku-demo.mp4" controls autoplay loop>',
            ["/static/post_images/sudoku-demo.mp4"],
        ),
        ('<img src="hello.jpg">', ["hello.jpg"]),
    ],
)
def test_image_video_regex(html_string, images):
    assert blog_admin.find_html_images(html_string) == images


@pytest.mark.parametrize(
    "html_string, links",
    [
        (
            "I would like to have [[simple links]] as well as [[these|complex links]]",
            ["simple links", "these|complex links"],
        )
    ],
)
def test_get_internal_links(html_string, links):
    assert get_internal_links(html_string) == links


@pytest.mark.parametrize(
    "link, expected",
    [
        ("simple link", ("simple link", "simple link")),
        ("complex link|like this", ("complex link", "like this")),
    ],
)
def test_parse_link(link, expected):
    assert parse_internal_link(link) == expected


@pytest.mark.parametrize(
    "html_string, expected",
    [
        (
            "Here is a [[simple link]]",
            "Here is a <a href='/blog/simple_link'>simple link</a>",
        )
    ],
)
def test_replace_internal_links(html_string, expected, monkeypatch):
    monkeypatch.setattr(
        "blog_admin.get_link_handle", lambda _: ("simple_link", "simple link")
    )
    assert replace_internal_links(html_string) == expected


@pytest.mark.parametrize(
    "link, expected",
    [
        (
            ("some_handle", "Can you handle it?"),
            "<a href='/blog/some_handle'>Can you handle it?</a>",
        )
    ],
)
def test_link_href(link: tuple[str, str], expected: str):
    assert generate_link_href(link) == expected
