# Nodestream Meta Plugin

This plugin allows you to build a Graph of your Graph's Schema.

## Installation

```bash
pip install nodestream-plugin-meta
```

## Meta-Schema

The schema of the graph schema is as follows:

![Meta Schema](meta.png)

For extra meta characteristics, the schema of the schema schema is also added to the projects schema like any other pipeline.
In other words, the types `NodeType`, `Property`, and so on are added to the schema of the graph. 

## Getting Started

Unlike other schema plugins, this plugin uses the ingestion system to build the metagraph in your graph. 
That means that you need to build a pipeline to do the ingestion.
For the simple case, you can build a single step pipeline that looks like this:

```yaml
- implementation: nodestream_plugin_meta:SchemaRenderer
```

This will locate the project file located inside the current working directory (or its parent directories) and 
render the schema to the graph. You can also specify the path to the project file:

```yaml
- implementation: nodestream_plugin_meta:SchemaRenderer
  parameters:
    project_path: /path/to/nodestream.yaml
```

You may also specify an overrides file to enrich the inferred schema:

```yaml
- implementation: nodestream_plugin_meta:SchemaRenderer
  parameters:
    project_path: /path/to/nodestream.yaml
    overrides_path: /path/to/overrides.yaml
```

The overrides file should look like this:

```yaml
nodes:
  - name: Person
    properties:
      is_cool:
        type: BOOLEAN
relations:
  - name: Knows
    properties:
      since:
        type: DATE
```

The file is merged with the inferred schema, so you can add new nodes, relations, or properties, or override parts of existing ones.

## Querying the Meta Graph

The meta graph can be queried like any other graph data. 
For example, to get all the node types in the graph:

```cypher
MATCH (n:NodeType) RETURN n.name
```

Or to get all the properties of a node type:

```cypher
MATCH (n:NodeType {name: 'Person'})-[:HAS_PROPERTY]->(p:Property) RETURN p.name, p.type, p.is_key
```

Same goes for relations and their properties:

```cypher
MATCH (r:RelationshipType {name: 'Knows'})-[:HAS_PROPERTY]->(p:Property) RETURN p.name, p.type, p.is_key
```

Also you can get the adjacencies the graph schema:

```cypher
MATCH (a:NodeType)<-[:TO|FROM]-(adj:Adjacency)-[:TO|FROM]->(b:NodeType)
MATCH (adj)-[:THROUGH]->(r:RelationshipType)
RETURN a.name, r.name, b.name
```
