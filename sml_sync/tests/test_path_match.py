import pytest

from sml_sync.path_match import matches


@pytest.mark.parametrize(
    "path,pattern",
    [
        ("/hello/world", "/hello"),
        ("/hello/world/", "/hello/"),
        ("/hello/world", "/hello/world"),
        ("/hello/world/bye", "/hello/world"),
        ("/hello/world", "/"),
        ("/hello/world/bye", "world"),
        ("/hello/world/bye", "world/bye"),
        ("/hello/world/bye", "world/bye/"),
        ("/hello/world", "/hell*"),
        ("/hello/world", "/hell*/world"),
        ("/hello/world", "/*/world"),
        ("/hello/world/bye", "*"),
        ("/hello/", "hel*o"),
    ],
)
def test_should_match(path, pattern):
    assert matches(path, pattern)


@pytest.mark.parametrize(
    "path,pattern",
    [
        ("/hello/world", "/hell"),
        ("/hello/wo", "/hello/world"),
        ("/hello/world/bye", "/world"),
        ("/hello/", "hel*x"),
    ],
)
def test_should_not_match(path, pattern):
    assert not matches(path, pattern)
