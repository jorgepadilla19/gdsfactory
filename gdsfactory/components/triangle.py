from gdsfactory.cell import cell
from gdsfactory.component import Component
from gdsfactory.types import Layer


@cell
def triangle(
    x: float = 10, xtop: float = 0, y: float = 20, layer: Layer = (1, 0)
) -> Component:
    r"""
    Args:
        x: base xsize
        xtop: top xsize
        y: ysize
        layer:

    .. code::

        xtop
           _
          | \
          |  \
          |   \
         y|    \
          |     \
          |      \
          |_______\
              x
    """
    c = Component()
    points = [[0, 0], [x, 0], [xtop, y], [0, y]]
    c.add_polygon(points, layer=layer)
    return c


if __name__ == "__main__":
    cc = triangle(xtop=5)
    cc.show()