"""
FIXME: enable Sbend routing when we have no space for a manhattan route

Route manhattan sometimes does not fit a route.
it would be nice to enable Sbend routing for those cases in route_manhattan

"""
import pp
from pp.routing.manhattan import route_manhattan


if __name__ == "__main__":
    c = pp.Component()
    length = 10
    c1 = c << pp.components.straight(length=length)
    c2 = c << pp.components.straight(length=length)

    dy = 4.0
    c2.y = dy
    c2.movex(length + dy)

    route = route_manhattan(
        input_port=c1.ports["E0"],
        output_port=c2.ports["W0"],
        waveguide="nitride",
        radius=5.0,
    )

    c.add(route.references)

    c.show()