import pytest

from blog_admin import get_handle, find_markdown_images


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
def test_find_images(md_string, img_list, monkeypatch):
    assert find_markdown_images(md_string) == img_list
