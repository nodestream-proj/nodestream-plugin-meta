from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from nodestream.model import DesiredIngestion, Node, Relationship
from nodestream.schema import (Adjacency, AdjacencyCardinality,
                               GraphObjectSchema, PropertyMetadata, Schema)

from nodestream_plugin_meta.plugin import (SchemaRenderer,
                                           find_nodestream_yaml,
                                           has_property_rel, node_by_name,
                                           rel_by_name, render_adjacency,
                                           render_node, render_property,
                                           render_relationship)


def test_find_nodestream_yaml_in_current_dir():
    # nodestream.yaml is in the current directory
    path = Path.cwd() / "tests"
    assert find_nodestream_yaml(path) == path / "nodestream.yaml"


def test_find_nodestream_yaml_in_parent_dir():
    # nodestream.yaml is in the parent directory
    path = Path.cwd() / "tests" / "something"
    assert find_nodestream_yaml(path) == Path.cwd() / "tests" / "nodestream.yaml"


def test_find_nodestream_yaml_not_found():
    # defaults to cwd, which doesn't have a nodestream.yaml in its parent dirs
    assert find_nodestream_yaml() is None


def test_render_property():
    property_name = "name"
    property = PropertyMetadata(is_key=True)
    owner = GraphObjectSchema(name="Person")
    node = render_property(owner, property_name, property)

    expected_keys = {"owner": "Person", "name": "name"}
    assert node.key_values == expected_keys
    assert node.properties["type"] == property.type.value
    assert node.properties["is_key"] == property.is_key


def test_has_property_rel():
    relationship = has_property_rel()
    assert isinstance(relationship, Relationship)
    assert relationship.type == "HAS_PROPERTY"


def test_rel_by_name():
    name = "REL_NAME"
    node = rel_by_name(name)
    assert isinstance(node, Node)
    assert node.type == "RelationshipType"
    assert node.key_values["name"] == name


def test_node_by_name():
    name = "NODE_NAME"
    node = node_by_name(name)
    assert isinstance(node, Node)
    assert node.type == "NodeType"
    assert node.key_values["name"] == name


def test_render_node():
    schema = GraphObjectSchema(
        name="Person", properties={"name": PropertyMetadata(is_key=True)}
    )
    ingestion = render_node(schema)
    assert isinstance(ingestion, DesiredIngestion)
    assert ingestion.source.key_values["name"] == "Person"
    assert len(ingestion.relationships) == 1
    assert ingestion.relationships[0].to_node.key_values["name"] == "name"


def test_render_relationship():
    schema = GraphObjectSchema(
        name="FRIENDS_WITH", properties={"since": PropertyMetadata(is_key=False)}
    )
    ingestion = render_relationship(schema)
    assert isinstance(ingestion, DesiredIngestion)
    assert ingestion.source.key_values["name"] == "FRIENDS_WITH"
    assert len(ingestion.relationships) == 1
    assert ingestion.relationships[0].to_node.key_values["name"] == "since"


def test_render_adjacency():
    adjacency = Adjacency(
        from_node_type="Person", to_node_type="City", relationship_type="LIVES_IN"
    )
    ingestion = render_adjacency(adjacency)
    assert isinstance(ingestion, DesiredIngestion)
    assert ingestion.source.key_values["id"] == "Person_City_LIVES_IN"
    assert len(ingestion.relationships) == 3
    assert ingestion.relationships[0].to_node.key_values["name"] == "Person"
    assert ingestion.relationships[1].to_node.key_values["name"] == "City"
    assert ingestion.relationships[2].to_node.key_values["name"] == "LIVES_IN"


def test_schema_renderer_from_file_data():
    with patch("nodestream_plugin_meta.plugin.find_nodestream_yaml") as mock_find:
        mock_find.return_value = Path("/path/to/nodestream.yaml")
        renderer = SchemaRenderer.from_file_data()
        assert renderer.project_path == Path("/path/to/nodestream.yaml")
        assert renderer.overrides_path is None

    with patch("nodestream_plugin_meta.plugin.find_nodestream_yaml") as mock_find:
        mock_find.return_value = None
        with pytest.raises(ValueError):
            SchemaRenderer.from_file_data()


def test_schema_renderer_init():
    project_path = Path("/path/to/nodestream.yaml")
    overrides_path = Path("/path/to/overrides.yaml")
    renderer = SchemaRenderer(project_path, overrides_path)
    assert renderer.project_path == project_path
    assert renderer.overrides_path == overrides_path


def test_schema_renderer_render_schema():
    schema = Schema()
    schema.put_node_type(
        GraphObjectSchema(
            name="Person", properties={"name": PropertyMetadata(is_key=True)}
        )
    )
    schema.put_relationship_type(
        GraphObjectSchema(
            name="FRIENDS_WITH",
            properties={"since": PropertyMetadata(is_key=False)},
        )
    )

    schema.add_adjacency(
        Adjacency(
            from_node_type="Person",
            to_node_type="City",
            relationship_type="LIVES_IN",
        ),
        AdjacencyCardinality(),
    )

    renderer = SchemaRenderer(Path("/path/to/nodestream.yaml"))
    ingestions = list(renderer.render_schema(schema))
    assert len(ingestions) == 3


@pytest.mark.asyncio
async def test_schema_renderer_extract_records():
    project_mock = MagicMock()
    schema_mock = MagicMock()
    project_mock.get_schema.return_value = schema_mock

    with patch(
        "nodestream_plugin_meta.plugin.Project.read_from_file",
        return_value=project_mock,
    ):
        renderer = SchemaRenderer(Path("/path/to/nodestream.yaml"))
        records = [record async for record in renderer.extract_records()]
        assert len(records) == 0  # Adjust this based on the mock schema's content
