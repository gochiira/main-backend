import pytest


def add_follow(client, headers, params):
    return client.post(
        '/timeline/follow',
        headers=headers,
        json=params
    )


def remove_follow(client, headers, params):
    return client.post(
        '/timeline/unfollow',
        headers=headers,
        json=params
    )


def get_follow(client, headers):
    return client.get(
        '/timeline/following',
        headers=headers
    )


def get_timeline(client, headers):
    return client.get(
        '/timeline',
        headers=headers
    )


@pytest.mark.timeline
def test_post_follow_valid(params):
    cl, headers = params
    rv = add_follow(cl, headers, {"type": 1, "id": 1})
    assert rv.get_json()['message'] == "Follow succeed."


@pytest.mark.timeline
def test_post_follow_invalid_no_params(params):
    cl, headers = params
    rv = add_follow(cl, headers, {})
    assert rv.get_json()['message'] == "Request parameters are not satisfied."


@pytest.mark.timeline
def test_post_follow_invalid_unsatisfied_params(params):
    cl, headers = params
    rv = add_follow(cl, headers, {"id": 1})
    assert rv.get_json()['message'] == "Request parameters are not satisfied."


@pytest.mark.timeline
def test_post_follow_invalid_already_following(params):
    cl, headers = params
    rv = add_follow(cl, headers, {"type": 1, "id": 1})
    add_follow(cl, headers, {"type": 1, "id": 1})
    assert rv.get_json()['message'] == "You already following."


@pytest.mark.timeline
def test_post_follow_invalid_too_mamy_follow(params):
    cl, headers = params
    for i in range(30):
        add_follow(cl, headers, {"type": 1, "id": i})
    rv = add_follow(cl, headers, {"type": 1, "id": i})
    assert rv.get_json()['message'] == "Maximum follow count reached.\nYou must reduce follow."


@pytest.mark.timeline
def test_post_follow_bombed(params):
    cl, headers = params
    rv = add_follow(cl, headers, {"type": 1, "id": "香風智乃"})
    assert rv.get_json()['message'] == "Server bombed."


@pytest.mark.timeline
def test_post_unfollow_valid(params):
    cl, headers = params
    add_follow(cl, headers, {"type": 1, "id": 1})
    rv = remove_follow(cl, headers, {"type": 1, "id": 1})
    assert rv.get_json()['message'] == "Remove succeed."


@pytest.mark.timeline
def test_post_unfollow_invalid_no_params(params):
    cl, headers = params
    rv = remove_follow(cl, headers, {})
    assert rv.get_json()['message'] == "Request parameters are not satisfied."


@pytest.mark.timeline
def test_post_unfollow_invalid_unsatisfied_params(params):
    cl, headers = params
    rv = remove_follow(cl, headers, {"id": 1})
    assert rv.get_json()['message'] == "Request parameters are not satisfied."


@pytest.mark.timeline
def test_post_unfollow_invalid_not_following(params):
    cl, headers = params
    rv = remove_follow(cl, headers, {"type": 1, "id": 1})
    assert rv.get_json()['message'] == "You are not following."


@pytest.mark.timeline
def test_post_unfollow_bombed(params):
    cl, headers = params
    rv = remove_follow(cl, headers, {"type": 1, "id": "香風智乃"})
    assert rv.get_json()['message'] == "Server bombed."


@pytest.mark.timeline
def test_get_timeline_zero_follow(params):
    cl, headers = params
    rv = get_timeline(cl, headers)
    assert rv.get_json()['message'] == "You are not following."


@pytest.mark.timeline
def test_get_timeline_single_artist(params):
    cl, headers = params
    add_follow(cl, headers, {"type": 1, "id": 1})
    rv = get_timeline(cl, headers)
    assert rv.get_json()['message'] == "found"


@pytest.mark.timeline
def test_get_timeline_single_tag(params):
    cl, headers = params
    add_follow(cl, headers, {"type": 2, "id": 1})
    rv = get_timeline(cl, headers)
    assert rv.get_json()['message'] == "found"


@pytest.mark.timeline
def test_get_timeline_multiple_artist(params):
    cl, headers = params
    for i in range(3):
        add_follow(cl, headers, {"type": 1, "id": i+1})
    rv = get_timeline(cl, headers)
    assert rv.get_json()['message'] == "found"


@pytest.mark.timeline
def test_get_timeline_multiple_tag(params):
    cl, headers = params
    for i in range(3):
        add_follow(cl, headers, {"type": 2, "id": i+1})
    rv = get_timeline(cl, headers)
    assert rv.get_json()['message'] == "found"


@pytest.mark.timeline
def test_get_timeline_mixed(params):
    cl, headers = params
    for i in range(3):
        add_follow(cl, headers, {"type": 1, "id": i+1})
        add_follow(cl, headers, {"type": 2, "id": i+1})
    rv = remove_follow(cl, headers, {"id": "1", "type": "1"})
    assert rv.get_json()['message'] == "found"


@pytest.mark.timeline
def test_timeline_mixed(params):
    cl, headers = params
    rv = remove_follow(cl, headers, {"id": "1", "type": "1"})
    assert rv.get_json()['message'] == "Request parameters are not satisfied."
