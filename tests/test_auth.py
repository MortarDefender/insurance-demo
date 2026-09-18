from auth import check_password


def test_correct_password(settings):
    assert check_password(settings, "testpass") is True


def test_wrong_password(settings):
    assert check_password(settings, "nope") is False


def test_empty_password(settings):
    assert check_password(settings, "") is False
