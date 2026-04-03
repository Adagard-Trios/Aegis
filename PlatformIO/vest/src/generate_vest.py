import pyvista as pv
import numpy as np

def generate_detailed_vest_stl():
    print("Generating structured 3D vest geometry...")

    # 1. Base Torso (The mannequin underneath)
    # Using higher resolution for smoother curves
    torso = pv.Cylinder(radius=15, height=40, direction=(0, 0, 1), center=(0, 0, 10), resolution=100)
    torso.points[:, 1] *= 0.6  # Flatten chest/back (Y-axis)
    
    # V-taper for torso: wider at the top, narrower at the bottom
    z_min, z_max = torso.points[:, 2].min(), torso.points[:, 2].max()
    z_norm = (torso.points[:, 2] - z_min) / (z_max - z_min)
    torso.points[:, 0] *= (1.0 + (z_norm * 0.35))

    # 2. Lower Abdominal Belt (matches the bottom section of the reference image)
    # We make it slightly wider than the torso base
    belt = pv.Cylinder(radius=15.5, height=8, direction=(0, 0, 1), center=(0, 0, -5), resolution=100)
    belt.points[:, 1] *= 0.65 
    belt.points[:, 0] *= 1.05

    # 3. Main Chest Plate (The central armored area)
    # Created as a box and then mathematically curved to wrap around the chest
    chest_plate = pv.Cube(center=(0, -9.5, 15), x_length=22, y_length=3, z_length=18)
    # Apply a parabolic curve to the Y-axis based on the X-axis position to wrap it
    chest_plate.points[:, 1] += (chest_plate.points[:, 0]**2) * 0.025

    # 4. Shoulder Straps
    left_strap = pv.Cube(center=(-10, 0, 29), x_length=7, y_length=13, z_length=4)
    right_strap = pv.Cube(center=(10, 0, 29), x_length=7, y_length=13, z_length=4)

    # 5. Central Node Placeholder (The round glowing part on the belt)
    node = pv.Sphere(radius=3.5, center=(0, -10.5, -5), theta_resolution=50, phi_resolution=50)

    # 6. Upper Chest Node Placeholder
    upper_node = pv.Cube(center=(0, -11.5, 20), x_length=6, y_length=2, z_length=3)

    # Merge all the separate components into a single, unified mesh
    print("Merging components into a single manifold mesh...")
    vest_mesh = torso.merge([belt, chest_plate, left_strap, right_strap, node, upper_node])

    # Optional: Apply a smooth filter to make the transitions slightly less harsh
    # vest_mesh = vest_mesh.smooth(n_iter=10)

    # 7. Save the mesh to an STL file
    output_filename = "detailed_vest.stl"
    vest_mesh.save(output_filename)
    
    print(f"Success! '{output_filename}' has been saved to your current directory.")
    print("This multi-part structure provides distinct zones for sensor mapping.")

if __name__ == "__main__":
    generate_detailed_vest_stl()