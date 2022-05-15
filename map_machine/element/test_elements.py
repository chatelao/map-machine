"""
Draw test nodes, ways, and relations.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from svgwrite import Drawing

from map_machine.geometry.boundary_box import BoundaryBox
from map_machine.constructor import Constructor
from map_machine.geometry.flinger import Flinger
from map_machine.pictogram.icon import ShapeExtractor
from map_machine.map_configuration import MapConfiguration
from map_machine.mapper import Map
from map_machine.osm.osm_reader import OSMData, OSMNode, OSMWay
from map_machine.scheme import Scheme
from map_machine.workspace import Workspace

workspace: Workspace = Workspace(Path("temp"))

SCHEME: Scheme = Scheme.from_file(workspace.DEFAULT_SCHEME_PATH)
SHAPE_EXTRACTOR: ShapeExtractor = ShapeExtractor(
    workspace.ICONS_PATH, workspace.ICONS_CONFIG_PATH
)
DEFAULT_ZOOM: float = 18.0


HIGHWAY_VALUES: List[str] = [
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "service",
    "service_minor",
    "road",
    "pedestrian",
    "living_street",
    "bridleway",
    "cycleway",
    "footway",
    "steps",
    "path",
    "track",
    "raceway",
]

AEROWAY_VALUES: List[str] = [
    "runway",
    "taxiway",
]

RAILWAY_TAGS: List[Dict[str, str]] = [
    {"railway": "rail"},
    {"railway": "light_rail"},
    {"railway": "monorail"},
    {"railway": "funicular"},
    {"railway": "narrow_gauge"},
    {"railway": "subway"},
    {"railway": "subway", "color": "red"},
    {"railway": "subway", "color": "blue"},
]

ROAD_WIDTHS_AND_FEATURES: List[Dict[str, str]] = [
    {"width": "4"},
    {"width": "8"},
    {"width": "12"},
    {"width": "16"},
    {"bridge": "yes", "width": "4"},
    {"bridge": "yes", "width": "8"},
    {"tunnel": "yes", "width": "4"},
    {"tunnel": "yes", "width": "8"},
    {"ford": "yes", "width": "4"},
    {"ford": "yes", "width": "8"},
    {"embankment": "yes", "width": "4"},
    {"embankment": "yes", "width": "8"},
]


ROAD_LANES_AND_FEATURES: List[Dict[str, str]] = [
    {"lanes": "1"},
    {"lanes": "2"},
    {"lanes": "3"},
    {"lanes": "4"},
    {"bridge": "yes", "lanes": "1"},
    {"bridge": "yes", "lanes": "2"},
    {"tunnel": "yes", "lanes": "1"},
    {"tunnel": "yes", "lanes": "2"},
    {"ford": "yes", "lanes": "1"},
    {"ford": "yes", "lanes": "2"},
    {"embankment": "yes", "lanes": "1"},
    {"embankment": "yes", "lanes": "2"},
]


# See https://wiki.openstreetmap.org/wiki/Proposed_features/placement

PLACEMENT_FEATURES_1: List[Dict[str, str]] = [
    {"lanes": "1"},
    {"lanes": "2", "placement": "middle_of:1"},
    {"lanes": "4", "placement": "middle_of:2"},
    {"placement": "transition"},
    {"lanes": "3", "placement": "right_of:1"},  # or placement=left_of:2
]

PLACEMENT_FEATURES_2: List[Dict[str, str]] = [
    {"lanes": "2"},
    # or placement:backward=left_of:1
    {"lanes": "3", "placement:forward": "left_of:1"},
    {"lanes": "3", "placement": "transition"},
    {"lanes": "4", "placement:backward": "middle_of:1"},
    {"lanes": "3"},
]


class Grid:
    """Creating map with elements ordered in grid."""

    def __init__(self) -> None:
        self.x_step: float = 0.0002
        self.y_step: float = 0.0003
        self.x_start: float = 0.0
        self.index: int = 0
        self.nodes: Dict[OSMNode, Tuple[int, int]] = {}
        self.max_j: float = 0
        self.max_i: float = 0

    def add_node(self, tags: Dict[str, str], i: int, j: int) -> OSMNode:
        """Add OSM node to the grid."""
        self.index += 1
        node: OSMNode = OSMNode(
            tags,
            self.index,
            np.array((-i * self.y_step, j * self.x_step)),
        )
        self.nodes[node] = (j, i)
        self.max_j = max(self.max_j, j * self.x_step)
        self.max_i = max(self.max_i, i * self.y_step)
        return node

    def get_boundary_box(self) -> BoundaryBox:
        """Compute resulting boundary box with margin of one grid step."""
        return BoundaryBox(
            -self.x_step,
            -self.max_i - self.y_step,
            self.max_j + self.x_step,
            self.y_step,
        )


def road_features(
    types: List[Dict[str, str]], features: List[Dict[str, str]], path: Path
) -> None:
    """Draw test image with different road features."""
    osm_data: OSMData = OSMData()
    grid: Grid = Grid()

    for i, type_ in enumerate(types):
        previous: Optional[OSMNode] = None

        for j in range(len(features) + 1):
            node: OSMNode = grid.add_node({}, i, j)

            if previous:
                tags: Dict[str, str] = dict(type_)
                tags |= dict(features[j - 1])
                way: OSMWay = OSMWay(
                    tags, i * (len(features) + 1) + j, [previous, node]
                )
                osm_data.add_way(way)
            previous = node

    draw(osm_data, path, grid.get_boundary_box())


def draw(
    osm_data: OSMData,
    output_path: Path,
    boundary_box: BoundaryBox,
    zoom: float = DEFAULT_ZOOM,
) -> None:
    """Draw map."""
    configuration: MapConfiguration = MapConfiguration(level="all")

    flinger: Flinger = Flinger(boundary_box, zoom, osm_data.equator_length)
    svg: Drawing = Drawing(output_path.name, flinger.size)
    constructor: Constructor = Constructor(
        osm_data, flinger, SCHEME, SHAPE_EXTRACTOR, configuration
    )
    constructor.construct()
    map_: Map = Map(flinger, svg, SCHEME, configuration)
    map_.draw(constructor)

    with output_path.open("w") as output_file:
        svg.write(output_file)
        logging.info(f"Map is drawn to {output_path}.")


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

    highway_tags: List[Dict[str, str]] = [
        {"highway": value} for value in HIGHWAY_VALUES
    ]
    aeroway_tags: List[Dict[str, str]] = [
        {"aeroway": value} for value in AEROWAY_VALUES
    ]

    road_features(
        highway_tags, ROAD_LANES_AND_FEATURES, Path("out") / "lanes.svg"
    )
    road_features(
        highway_tags + RAILWAY_TAGS + aeroway_tags,
        ROAD_WIDTHS_AND_FEATURES,
        Path("out") / "width.svg",
    )
    road_features(
        highway_tags,
        PLACEMENT_FEATURES_1 + [{"highway": "none"}] + PLACEMENT_FEATURES_2,
        Path("out") / "placement.svg",
    )
