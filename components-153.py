import gdsfactory as gf

c = gf.components.straight_pin(length=500.0, contact_width=10.0, contact_spacing=2)
c.plot()