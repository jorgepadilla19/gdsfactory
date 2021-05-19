from typing import Dict, Iterable, Optional, Tuple

import numpy as np
from pydantic import validate_arguments

import pp
from pp.cell import cell
from pp.component import Component
from pp.components.electrical.tlm import tlm
from pp.components.extension import line
from pp.components.hline import hline
from pp.components.straight import straight
from pp.cross_section import get_waveguide_settings
from pp.layers import LAYER
from pp.port import Port, auto_rename_ports
from pp.types import ComponentFactory, Layer, Number


@cell
@validate_arguments
def heater(
    length: float = 10.0,
    width: float = 0.5,
    layer_heater: Tuple[int, int] = LAYER.HEATER,
) -> Component:
    """Straight heater"""
    c = pp.Component()
    _ref = c.add_ref(hline(length=length, width=width, layer=layer_heater))
    c.ports = _ref.ports  # Use ports from latest layer as heater ports
    for p in c.ports.values():
        p.layer = layer_heater
        p.port_type = "heater"
    c.absorb(_ref)
    return c


def add_trenches(
    c: Component,
    sstw: float = 2.0,
    trench_width: float = 0.5,
    trench_keep_out: float = 2.0,
    trenches: Tuple[Dict[str, Number], ...] = (
        {"nb_segments": 2, "lane": 1, "x_start_offset": 0},
        {"nb_segments": 2, "lane": -1, "x_start_offset": 0},
    ),
    layer_trench: Tuple[int, int] = LAYER.DEEPTRENCH,
) -> Component:
    """
    Add trenches to a straight-heater-like component
    """

    heater_width = c.settings["heater_width"]
    heater_spacing = c.settings["heater_spacing"]
    width = c.settings["width"]
    length = c.settings["length"]

    a = heater_spacing + (width + heater_width) / 2

    # Add trenches
    if trench_width and trench_width > 0:
        tko = trench_keep_out

        for trench in trenches:
            lane = trench["lane"]
            td = tko + a + (trench_width + heater_width) / 2
            y = np.sign(lane) * (td + (abs(lane) - 1) * (trench_width + tko))
            x_start_offset = trench["x_start_offset"]

            if "segments" not in trench:
                nb_segments = trench["nb_segments"]
                trench_length = (length - (nb_segments - 1) * sstw) / nb_segments
                segments = [trench_length] * nb_segments
            else:
                segments = trench["segments"]
            x = x_start_offset
            for trench_length in segments:
                trench = hline(
                    length=trench_length, width=trench_width, layer=layer_trench
                )
                _trench = trench.ref(
                    port_id="W0", position=c.ports["W0"].position + (x, y)
                )
                c.add(_trench)
                c.absorb(_trench)
                x += trench_length + sstw

    return c


@cell
def straight_heater(
    length: float = 10.0,
    heater_width: float = 0.5,
    heater_spacing: float = 1.2,
    sstw: float = 2.0,
    trench_width: float = 0.5,
    trench_keep_out: float = 2.0,
    trenches: Tuple[Dict[str, Number], ...] = (
        {"nb_segments": 2, "lane": 1, "x_start_offset": 0},
        {"nb_segments": 2, "lane": -1, "x_start_offset": 0},
    ),
    layer_heater: Tuple[int, int] = LAYER.HEATER,
    straight_factory: ComponentFactory = straight,
    layer_trench: Tuple[int, int] = LAYER.DEEPTRENCH,
    waveguide: str = "strip",
    **waveguide_settings,
) -> Component:
    """Waveguide with heater and trenches.

    .. code::

        TTTTTTTTTTTTT    TTTTTTTTTTTTT <-- trench

        HHHHHHHHHHHHHHHHHHHHHHHHHHHHHH <-- heater

        ------------------------------ <-- straight

        HHHHHHHHHHHHHHHHHHHHHHHHHHHHHH <-- heater

        TTTTTTTTTTTTT    TTTTTTTTTTTTT <-- trench


    """
    c = Component()
    _heater = heater(length=length, width=heater_width, layer_heater=layer_heater)
    waveguide_settings = get_waveguide_settings(waveguide, **waveguide_settings)
    width = waveguide_settings["width"]

    y_heater = heater_spacing + (width + heater_width) / 2
    heater_top = c << _heater
    heater_bot = c << _heater

    heater_top.movey(+y_heater)
    heater_bot.movey(-y_heater)

    wg = c << straight_factory(
        length=length,
        waveguide=waveguide,
        **waveguide_settings,
    )

    for i in [heater_top, heater_bot, wg]:
        c.absorb(i)

    # Add wg ports
    for p in wg.ports.values():
        c.add_port(name=p.name, port=p)

    # Add heater ports
    for p in heater_top.ports.values():
        c.add_port(name="HT" + p.name, port=p)

    for p in heater_bot.ports.values():
        c.add_port(name="HB" + p.name, port=p)

    c.settings["heater_width"] = heater_width
    c.settings["heater_spacing"] = heater_spacing
    c.settings["length"] = length
    c.settings["width"] = width
    add_trenches(
        c, sstw, trench_width, trench_keep_out, trenches, layer_trench=layer_trench
    )

    return c


@cell
def straight_heater_connector(
    heater_ports: Iterable[Port],
    tlm_layers: Tuple[Layer] = (
        LAYER.VIA1,
        LAYER.M1,
        LAYER.VIA2,
        LAYER.M2,
        LAYER.VIA3,
        LAYER.M3,
    ),
    port_width: Optional[float] = 10.0,
    port_orientation: Optional[int] = None,
) -> Component:
    """Connect together a pair of wg heaters to metal."""

    component = Component()
    assert len(heater_ports) == 2
    assert (
        heater_ports[0].orientation == heater_ports[1].orientation
    ), "both ports should be facing in the same direction"
    angle = heater_ports[0].orientation
    angle = angle % 360
    assert angle in [0, 180], f"angle should be 0 or 180, got {angle}"

    dx = 0.0
    dy = 0.0

    angle_to_dps = {0: [(-dx, -dy), (-dx, dy)], 180: [(dx, -dy), (dx, dy)]}
    ports = list(heater_ports)
    hw = heater_ports[0].width

    if angle in [0, 180]:
        ports.sort(key=lambda p: p.y)
    else:
        ports.sort(key=lambda p: p.x)

    _heater_to_metal = tlm(width=0.5, height=0.5, layers=tlm_layers, vias=[])

    tlm_positions = []
    for port, dp in zip(ports, angle_to_dps[angle]):
        # Extend heater
        p = port.midpoint

        # Add via/metal transitions
        tlm_pos = p + dp
        hm = _heater_to_metal.ref(position=tlm_pos)
        tlm_positions += [tlm_pos]
        component.add(hm)

    ss = 1 if angle == 0 else -1

    # Connect both sides with top metal
    edge_metal_piece_width = 7.0
    x = ss * edge_metal_piece_width / 2
    top_metal_layer = tlm_layers[-1]
    component.add_polygon(
        line(
            tlm_positions[0] + (x, -hw / 2),
            tlm_positions[1] + (x, hw / 2),
            edge_metal_piece_width,
        ),
        layer=top_metal_layer,
    )

    # Add metal port
    component.add_port(
        name="0",
        midpoint=0.5 * sum(tlm_positions) + (ss * edge_metal_piece_width / 2, 0),
        orientation=port_orientation if port_orientation is not None else angle,
        width=port_width,
        layer=top_metal_layer,
        port_type="dc",
    )

    return component


@cell
def straight_with_heater(
    length: float = 10.0,
    straight_heater: ComponentFactory = straight_heater,
    connector: ComponentFactory = straight_heater_connector,
    port_width: Optional[float] = 10.0,
    port_orientation_input: int = 90,
    port_orientation_output: int = 90,
    **kwargs,
) -> Component:
    """Returns a straight with heater.

    Args:
        length: straight length
        straight_heater: function
        connector: function
        port_width:
        port_orientation_input:
        port_orientation_output:
        **kwargs: for straight_heater

    """
    component = Component()

    wg_heater = component << straight_heater(length=length, **kwargs)
    connector1 = connector(
        heater_ports=(wg_heater.ports["HBE0"], wg_heater.ports["HTE0"]),
        port_width=port_width,
    )
    connector2 = connector(
        heater_ports=(wg_heater.ports["HBW0"], wg_heater.ports["HTW0"]),
        port_width=port_width,
    )

    conn1 = component << connector1
    conn2 = component << connector2
    conn1.xmin = wg_heater.xmin
    conn2.xmax = wg_heater.xmax

    for port_name, p in wg_heater.ports.items():
        component.add_port(name=port_name, port=p)

    component.add_port(name=1, port=conn1.ports["0"])
    component.add_port(name=2, port=conn2.ports["0"])
    component.ports[1].orientation = port_orientation_input
    component.ports[2].orientation = port_orientation_output
    auto_rename_ports(component)
    return component


def _demo_straight_heater():
    c = straight_heater(width=0.5)
    c.write_gds()


if __name__ == "__main__":
    # print(c.get_optical_ports())
    # c = straight_heater()
    # c = straight_heater_connector(heater_ports=[c.ports["HBW0"], c.ports["W0"]])

    c = straight_with_heater(length=200.0, port_orientation_input=0)
    # c = straight_heater_connector()
    c.show(show_ports=True)

    # from pp.cell import print_cache
    # print_cache()
    # print(c.ports.keys())
    # for p in c.ports.values():
    #     print(p.name, p.port_type, p.orientation)