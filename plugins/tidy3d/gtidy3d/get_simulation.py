"""
Returns simulation from component

Questions:

- How to define a field_monitor_port
    field_monitor_port = component.ports[port_field_monitor_name]
    field_monitor_point = field_monitor_port.center.tolist() + [0]  # (x, y, z=0)

- how to define cladding material
- show index of refraction
- cache simulations
- zmin = 1.
- add sidewall_angle
- visualize modes
- visualize fields for simultion
- simulate dispersive materials
- review simulation before sending it?
- gdslayer with gdslayer/gdspurpose

"""
from typing import Dict, Optional, Tuple
import warnings

import pydantic
import matplotlib.pyplot as plt
import numpy as np
import pp
from pp.component import Component
from pp.components.extension import move_polar_rad_copy
from pp.routing.sort_ports import sort_ports_x, sort_ports_y

import tidy3d as td
from gtidy3d.materials import get_material


LAYER_TO_THICKNESS_NM = {(1, 0): 220.0}
LAYER_TO_MATERIAL = {(1, 0): "cSi"}
LAYER_TO_ZMIN = {(1, 0): 0}
LAYER_TO_SIDEWALL_ANGLE = {(1, 0): 0}


@pydantic.validate_arguments
def get_simulation(
    component: Component,
    mode_index: int = 0,
    n_modes: int = 2,
    extend_ports_length: Optional[float] = 4.0,
    layer_to_thickness_nm: Dict[Tuple[int, int], float] = LAYER_TO_THICKNESS_NM,
    layer_to_material: Dict[Tuple[int, int], str] = LAYER_TO_MATERIAL,
    layer_to_zmin_nm: Dict[Tuple[int, int], float] = LAYER_TO_ZMIN,
    layer_to_sidewall_angle: Dict[Tuple[int, int], float] = LAYER_TO_SIDEWALL_ANGLE,
    t_clad_top: float = 1.0,
    t_clad_bot: float = 1.0,
    tpml: float = 1.0,
    clad_material: str = "SiO2",
    port_source_name: str = "W0",
    port_margin: float = 0.5,
    distance_source_to_monitors: float = 0.2,
    mesh_step: float = 0.040,
    wavelength: float = 1.55,
) -> td.Simulation:
    """Returns Simulation object from gdsfactory component

    based on GDS example
    https://simulation.cloud/docs/html/examples/ParameterScan.html

    Args:
        component: gdsfactory Component
        mode_index: mode index
        n_modes: number of modes
        extend_ports_function: function to extend the ports for a component to ensure it goes beyond the PML
        layer_to_thickness_nm: Dict of layer number (int, int) to thickness (nm)
        t_clad_top: thickness for cladding above core
        t_clad_bot: thickness for cladding below core
        tpml: PML thickness (um)
        clad_material: material for cladding
        sidewall_angle: in degrees
        port_source_name: input port name
        port_margin: margin on each side of the port
        distance_source_to_monitors: in (um) source goes before
        mesh_step: in all directions
        wavelength: in (um)

    Make sure you visualize the simulation region with gdsfactory before you simulate a component


    .. code::

        import matplotlib.pyplot as plt
        import pp
        import gtidy as gm

        c = pp.components.bend_circular()
        sim = gm.get_simulation(c)
        gm.plot_simulation(sim)

    """
    assert isinstance(
        component, Component
    ), f"component needs to be a gdsfactory Component, got Type {type(component)}"
    if port_source_name not in component.ports:
        warnings.warn(
            f"port_source_name={port_source_name} not in {component.ports.keys()}"
        )
        port_source = component.get_ports_list()[0]
        port_source_name = port_source.name
        warnings.warn(f"Selecting port_source_name={port_source_name} instead.")

    component = component.copy()
    component.x = 0
    component.y = 0

    component_extended = (
        pp.extend.extend_ports(component=component, length=extend_ports_length)
        if extend_ports_length
        else component
    )

    pp.show(component_extended)
    component_extended.flatten()

    structures = [
        td.Box(
            material=get_material(name=clad_material),
            size=(td.inf, td.inf, td.inf),
            center=(0, 0, 0),
        )
    ]

    t_core = max(layer_to_thickness_nm.values()) * 1e-3
    cell_thickness = tpml + t_clad_bot + t_core + t_clad_top + tpml
    sim_size = [component.xsize + 2 * tpml, component.ysize + 2 * tpml, cell_thickness]

    layer_to_polygons = component_extended.get_polygons(by_spec=True)
    for layer, polygons in layer_to_polygons.items():
        if layer in layer_to_thickness_nm and layer in layer_to_material:
            height = layer_to_thickness_nm[layer] * 1e-3
            zmin_um = layer_to_zmin_nm[layer] * 1e-3
            z_cent = (height + zmin_um) / 2
            material_name = layer_to_material[layer]
            material = get_material(name=material_name)

            geometry = td.GdsSlab(
                material=material,
                gds_cell=component_extended,
                gds_layer=layer[0],
                gds_dtype=layer[1],
                z_cent=z_cent,
                z_size=height,
            )
            structures.append(geometry)

    # Add source
    port = component.ports[port_source_name]
    angle = port.orientation
    width = port.width + 2 * port_margin
    size_x = width * abs(np.sin(angle * np.pi / 180))
    size_y = width * abs(np.cos(angle * np.pi / 180))
    size_x = 0 if size_x < 0.001 else size_x
    size_y = 0 if size_y < 0.001 else size_y
    size_z = cell_thickness - 2 * tpml
    size = [size_x, size_y, size_z]
    center = port.center.tolist() + [0]  # (x, y, z=0)
    freq0 = td.constants.C_0 / wavelength
    fwidth = freq0 / 10

    msource = td.ModeSource(
        size=size,
        center=center,
        source_time=td.GaussianPulse(frequency=freq0, fwidth=fwidth),
        direction="forward",
    )

    # Add port monitors
    monitors = {}
    ports = sort_ports_x(sort_ports_y(component.get_ports_list()))
    for port in ports:
        port_name = port.name
        angle = port.orientation
        width = port.width + 2 * port_margin
        size_x = width * abs(np.sin(angle * np.pi / 180))
        size_y = width * abs(np.cos(angle * np.pi / 180))
        size_x = 0 if size_x < 0.001 else size_x
        size_y = 0 if size_y < 0.001 else size_y
        size = (size_x, size_y, size_z)

        # if monitor has a source move monitor inwards
        length = -distance_source_to_monitors if port_name == port_source_name else 0
        xy_shifted = move_polar_rad_copy(
            np.array(port.center), angle=angle * np.pi / 180, length=length
        )
        center = xy_shifted.tolist() + [0]  # (x, y, z=0)

        monitors[port_name] = td.ModeMonitor(
            center=[port.x, port.y, t_core / 2],
            size=size,
            freqs=[freq0],
            Nmodes=1,
            name=port.name,
        )

    domain_monitor = td.FreqMonitor(
        center=[0, 0, z_cent], size=[sim_size[0], sim_size[1], 0], freqs=[freq0]
    )

    sim = td.Simulation(
        size=sim_size,
        mesh_step=mesh_step,
        structures=structures,
        sources=[msource],
        monitors=[domain_monitor] + list(monitors.values()),
        run_time=20 / fwidth,
        pml_layers=[12, 12, 12],
    )
    # set the modes
    sim.compute_modes(msource, Nmodes=n_modes)
    sim.set_mode(msource, mode_ind=mode_index)
    return sim


def plot_simulation(
    sim: td.Simulation,
    normal1: str = "z",
    normal2: str = "x",
    position1: float = 0.0,
    position2: float = 0.0,
):
    """Returns figure with two axis of the Simulation.

    Args:
        normal1: {'x', 'y', 'z'} Axis normal to the cross-section plane.
        normal2: {'x', 'y', 'z'} Axis normal to the cross-section plane.
        position1: Position offset along the normal axis.
        position2: Position offset along the normal axis.

    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
    sim.viz_eps_2D(normal=normal1, position=position1, ax=ax1)
    sim.viz_eps_2D(normal=normal2, position=position2, ax=ax2, source_alpha=1)
    plt.show()
    return fig


def plot_materials(
    sim: td.Simulation,
    normal1: str = "z",
    normal2: str = "x",
    position1: float = 0.0,
    position2: float = 0.0,
):
    """Returns figure with two axis of the Simulation.

    Args:
        normal1: {'x', 'y', 'z'} Axis normal to the cross-section plane.
        normal2: {'x', 'y', 'z'} Axis normal to the cross-section plane.
        position1: Position offset along the normal axis.
        position2: Position offset along the normal axis.

    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
    sim.viz_mat_2D(normal=normal1, position=position1, ax=ax1)
    sim.viz_mat_2D(
        normal=normal2, position=position2, ax=ax2, source_alpha=1, legend=True
    )
    plt.show()
    return fig


if __name__ == "__main__":

    c = pp.components.mmi1x2()
    c = pp.add_padding(c, default=0, bottom=2, top=2, layers=[(100, 0)])

    c = pp.components.bend_circular(radius=2)
    # c = pp.add_padding(c, default=0, bottom=2, right=2, layers=[(100, 0)])

    # c = pp.add_padding(c, default=0, bottom=2, top=2, layers=[(100, 0)])
    c = pp.components.straight(length=2)

    sim = get_simulation(c)
    # fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
    # sim.viz_eps_2D(normal="z", position=0, ax=ax1)
    # sim.viz_eps_2D(normal="x", ax=ax2, source_alpha=1)
    # ax2.set_xlim([-3, 3])
    plot_simulation(sim)