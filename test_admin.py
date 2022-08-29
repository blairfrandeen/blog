import pytest

from blog_admin import get_handle


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
