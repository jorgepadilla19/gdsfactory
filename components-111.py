import gdsfactory as gf

c = gf.components.mzi_phase_shifter(delta_length=10.0, length_y=2.0, with_splitter=True, port_e1_splitter='o2', port_e0_splitter='o3', port_e1_combiner='o2', port_e0_combiner='o3', nbends=2)
c.plot()