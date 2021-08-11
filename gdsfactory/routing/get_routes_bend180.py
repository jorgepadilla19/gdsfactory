from typing import Dict, List, Union

import gdsfactory as gf
from gdsfactory.components.bend_euler import bend_euler
from gdsfactory.cross_section import strip
from gdsfactory.difftest import difftest
from gdsfactory.port import Port
from gdsfactory.types import ComponentOrFactory, CrossSectionFactory, Routes


def get_routes_bend180(
    ports: Union[List[Port], Dict[str, Port]],
    bend_factory: ComponentOrFactory = bend_euler,
    cross_section: CrossSectionFactory = strip,
    **kwargs,
) -> Routes:
    """Returns routes made by 180 degree bends.

    Args:
        ports: List or dict of ports
        bend_factory: function for bend
        **kwargs: bend settings
    """
    ports = list(ports.values()) if isinstance(ports, dict) else ports
    bend = bend_factory(angle=180, cross_section=cross_section, **kwargs)
    references = [bend.ref() for port in ports]
    references = [ref.connect("W0", port) for port, ref in zip(ports, references)]
    ports = {f"{i}": ref.ports["W1"] for i, ref in enumerate(references)}
    lengths = [bend.length] * len(ports)
    return Routes(references=references, ports=ports, lengths=lengths)


def test_get_routes_bend180():
    c = gf.Component("get_routes_bend180")
    pad_array = gf.components.pad_array(pitch=150, port_list=("S",))
    c1 = c << pad_array
    c2 = c << pad_array
    c2.rotate(90)
    c2.movex(1000)
    c2.ymax = -200

    routes_bend180 = get_routes_bend180(
        ports=c2.get_ports_list(),
        radius=75 / 2,
    )
    c.add(routes_bend180.references)

    routes = gf.routing.get_bundle(
        ports1=c1.get_ports_list(),
        ports2=routes_bend180.ports,
    )
    for route in routes:
        c.add(route.references)
    difftest(c)
    return c


if __name__ == "__main__":
    c = gf.Component("get_routes_bend180")
    pad_array = gf.components.pad_array(pitch=150, port_list=("S",))
    c1 = c << pad_array
    c2 = c << pad_array
    c2.rotate(90)
    c2.movex(1000)
    c2.ymax = -200
    layer = (2, 0)

    routes_bend180 = get_routes_bend180(
        ports=c2.get_ports_list(), radius=75 / 2, layer=layer
    )
    c.add(routes_bend180.references)

    routes = gf.routing.get_bundle(
        c1.get_ports_list(), routes_bend180.ports, layer=layer
    )
    for route in routes:
        c.add(route.references)
    c.show()