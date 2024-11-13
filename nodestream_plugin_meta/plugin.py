from pathlib import Path
from typing import Iterable, Optional

from nodestream.model import DesiredIngestion, Node, Relationship
from nodestream.pipeline import Extractor
from nodestream.project import Project
from nodestream.schema import Adjacency, GraphObjectSchema, PropertyMetadata, Schema

NODE_TYPE_TYPE = "NodeType"
REL_TYPE_TYPE = "RelationshipType"
GRAPH_OBJECT_TYPE_TYPE = "GraphObjectType"
HAS_PROPERTY_REL = "HAS_PROPERTY"
PROPERTY_TYPE = "Property"
ADJACECNY_TYPE = "Adjacency"


def is_root(path: Path) -> bool:
    return path.absolute() == Path(path.anchor)


def find_nodestream_yaml(dir: Optional[Path] = None) -> Optional[Path]:
    """Walk up the directory tree to find a nodestream.yaml file."""
    current_path = dir or Path.cwd()
    while not is_root(current_path):
        maybe_project_path = current_path / "nodestream.yaml"
        if maybe_project_path.exists():
            return maybe_project_path
        current_path = current_path.parent

    return None


def render_property(
    owner: GraphObjectSchema,
    name: str,
    property: PropertyMetadata,
) -> Node:
    node = Node(type=PROPERTY_TYPE)
    node.key_values.set_property("owner", owner.name)
    node.key_values.set_property("name", name)
    node.properties.set_property("type", property.type.value)
    node.properties.set_property("is_key", property.is_key)
    return node


def has_property_rel() -> Relationship:
    return Relationship(type=HAS_PROPERTY_REL)


def rel_by_name(name: str) -> Node:
    node = Node(type=REL_TYPE_TYPE, additional_types=(GRAPH_OBJECT_TYPE_TYPE,))
    node.key_values.set_property("name", name)
    return node


def node_by_name(name: str) -> Node:
    node = Node(type=NODE_TYPE_TYPE, additional_types=(GRAPH_OBJECT_TYPE_TYPE,))
    node.key_values.set_property("name", name)
    return node


def render_node(schema: GraphObjectSchema):
    ingest = DesiredIngestion()
    ingest.source = node_by_name(schema.name)
    for name, property in schema.properties.items():
        ingest.add_relationship(
            related_node=render_property(schema, name, property),
            relationship=has_property_rel(),
            outbound=True,
        )
    return ingest


def render_relationship(schema: GraphObjectSchema):
    ingest = DesiredIngestion()
    ingest.source = rel_by_name(schema.name)
    for name, property in schema.properties.items():
        property_node = render_property(schema, name, property)
        ingest.add_relationship(
            related_node=property_node,
            relationship=has_property_rel(),
            outbound=True,
        )

    return ingest


def render_adjacency(adjacency: Adjacency):
    ingest = DesiredIngestion()
    node = Node(type=ADJACECNY_TYPE)
    id = f"{adjacency.from_node_type}_{adjacency.to_node_type}_{adjacency.relationship_type}"
    node.key_values.set_property("id", id)

    from_node = node_by_name(adjacency.from_node_type)
    from_node_rel = Relationship(type="FROM")
    to_node = node_by_name(adjacency.to_node_type)
    to_node_rel = Relationship(type="TO")
    rel = rel_by_name(adjacency.relationship_type)
    rel_rel = Relationship(type="THROUGH")

    ingest.source = node

    ingest.add_relationship(
        related_node=from_node,
        relationship=from_node_rel,
        outbound=True,
    )

    ingest.add_relationship(
        related_node=to_node,
        relationship=to_node_rel,
        outbound=True,
    )

    ingest.add_relationship(
        related_node=rel,
        relationship=rel_rel,
        outbound=True,
    )

    return ingest


class SchemaRenderer(Extractor):
    """Emits ingestions for all nodes, relationships, and adjacencies."""

    @classmethod
    def from_file_data(
        cls,
        project_path: Optional[str] = None,
        overrides_path: Optional[str] = None,
    ):
        project_path = project_path or find_nodestream_yaml()
        if not project_path:
            raise ValueError(
                "Could not find nodestream.yaml in the current directory "
                "or any parent directories. Please specify the path to "
                "the nodestream.yaml file."
            )

        project_path = Path(project_path)
        overrides_path = Path(overrides_path) if overrides_path else None
        return cls(project_path, overrides_path)

    def __init__(
        self,
        project_path: Path,
        overrides_path: Optional[Path] = None,
    ) -> None:
        self.project_path = project_path
        self.overrides_path = overrides_path

    def render_schema(self, schema: Schema) -> Iterable[DesiredIngestion]:
        for node_type in schema.nodes:
            yield render_node(node_type)

        for rel_type in schema.relationships:
            yield render_relationship(rel_type)

        for adjacency in schema.adjacencies:
            yield render_adjacency(adjacency)

    async def extract_records(self):
        project = Project.read_from_file(self.project_path)
        schema = project.get_schema(self.overrides_path)
        for ingest in self.render_schema(schema):
            yield ingest
