def test_list_groups(client, test_group):
    group, _, _ = test_group

    response = client.get("/group/")

    assert response.status_code == 200
    assert response.json() == [{"id": group.id, "name": group.name}]
