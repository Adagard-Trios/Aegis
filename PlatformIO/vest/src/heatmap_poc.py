import asyncio
import threading
import time
import numpy as np
import pyvista as pv
from bleak import BleakClient, BleakScanner

# --- Configuration ---
DEVICE_NAME = "Vest_Heatmap_ESP32"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# Global temperature storage and thread lock for safety
temp_lock = threading.Lock()
# Default starting temperatures (approximate room temp for testing gradients)
current_temps = np.array([25.0, 25.0, 25.0])

# --- 3D Mapping Coordinates ---
# Pushed the Left and Right sensors out to +/- 18.0 so they clear the mesh surface
SENSOR_COORDS = np.array([
    [-18.0,  0.0,  5.0],  # Location 1: Left Axilla
    [ 18.0,  0.0,  5.0],  # Location 2: Right Axilla
    [  0.0, -8.0, 15.0]   # Location 3: C7 Cervical Trunk
])

# Label Offset (Pushed the text outwards away from the body so it doesn't clip)
LABEL_COORDS = SENSOR_COORDS + np.array([
    [-4.0,  0.0, 3.0],  # Push Left label further left
    [ 4.0,  0.0, 3.0],  # Push Right label further right
    [ 0.0, -4.0, 3.0]   # Push C7 label further back
])

# --- Mathematical Interpolation ---
def calculate_gaussian_heatmap(mesh_vertices, sensor_coords, temps, spread=8.0):
    """
    Gaussian Radial Basis Function (RBF).
    Creates localized 'heat blooms' exactly like a medical thermal camera.
    """
    # Use the lowest sensor reading as the baseline 'ambient' temperature of the room/body
    ambient = np.min(temps)
    heatmap = np.full(mesh_vertices.shape[0], ambient)
    
    for i, coord in enumerate(sensor_coords):
        # Calculate squared distance from all mesh points to this specific sensor
        dist_sq = np.sum((mesh_vertices - coord) ** 2, axis=1)
        
        # Apply the Gaussian falloff curve based on the 'spread' radius
        weight = np.exp(-dist_sq / (2 * (spread ** 2)))
        
        # Add the sensor's heat bloom onto the mesh
        heatmap += (temps[i] - ambient) * weight
        
    return heatmap

# --- BLE Architecture ---
def handle_ble_notification(sender, data):
    """Callback for handling incoming BLE data."""
    global current_temps
    try:
        decoded_data = data.decode('utf-8')
        parts = decoded_data.split(',')
        if len(parts) == 3:
            with temp_lock:
                current_temps = np.array([float(p) for p in parts])
            print(f"Stream -> Left: {current_temps[0]:.2f}°C | Right: {current_temps[1]:.2f}°C | C7: {current_temps[2]:.2f}°C")
    except Exception as e:
        print(f"Error parsing BLE data: {e}")

async def run_ble_client():
    """Scans for the ESP32 and connects to listen for notifications."""
    print(f"Scanning for {DEVICE_NAME}...")
    devices = await BleakScanner.discover()
    target_device = next((d for d in devices if d.name == DEVICE_NAME), None)

    if not target_device:
        print(f"Could not find {DEVICE_NAME}. Ensure ESP32 is powered on.")
        return

    print(f"Found {DEVICE_NAME} at {target_device.address}. Connecting...")
    
    async with BleakClient(target_device.address) as client:
        print("BLE Connected! Receiving telemetry...")
        await client.start_notify(CHARACTERISTIC_UUID, handle_ble_notification)
        
        # Keep connection alive indefinitely
        while True:
            await asyncio.sleep(1)

def ble_thread_runner():
    """Runs the Asyncio BLE loop in a background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_ble_client())

# --- 3D Visualization Engine ---
def main():
    # 1. Start the BLE client in the background
    ble_thread = threading.Thread(target=ble_thread_runner, daemon=True)
    ble_thread.start()

    # 2. Initialize the PyVista 3D Plotter
    plotter = pv.Plotter(title="Real-Time Vest Heatmap POC")
    
    # 3. Load the Vest 3D Model
    try:
        mesh = pv.read("detailed_vest.stl")
        print("Loaded detailed_vest.stl successfully!")
    except Exception:
        print("\n[NOTE] No 'detailed_vest.stl' found in directory.")
        print("Generating a programmatic torso shape for testing...\n")
        mesh = pv.Cylinder(radius=15, height=35, direction=(0, 0, 1), center=(0, 0, 7.5))
        mesh.points[:, 1] *= 0.6  

    # 4. Calculate initial temperatures
    with temp_lock:
        initial_temps = current_temps.copy()
    
    # Apply initial Gaussian heatmap
    mesh['Temperature'] = calculate_gaussian_heatmap(mesh.points, SENSOR_COORDS, initial_temps)
    
    # 5. Add the mesh to the plotter and capture the mesh actor!
    mesh_actor = plotter.add_mesh(
        mesh, 
        scalars='Temperature', 
        cmap='coolwarm',       
        show_scalar_bar=True,
        smooth_shading=True
    )
    
    # 6. Mark the physical sensor locations with black spheres
    for coord in SENSOR_COORDS:
        sphere = pv.Sphere(radius=1.0, center=coord)
        plotter.add_mesh(sphere, color='black')

    # 7. Start the interactive real-time update loop
    plotter.add_axes()
    plotter.show(interactive_update=True)
    
    print("3D Renderer active. Waiting for BLE data...")
    
    label_actor = None 
    
    try:
        while True:
            with temp_lock:
                latest_temps = current_temps.copy()
                
            # Recalculate the heat blooms
            mesh['Temperature'] = calculate_gaussian_heatmap(mesh.points, SENSOR_COORDS, latest_temps)
            
            # --- THE FIX: DYNAMIC AUTO-SCALING ---
            # Automatically adjust the color scale to the current min/max temperatures
            min_t = np.min(latest_temps)
            max_t = np.max(latest_temps)
            
            # Prevent the rendering engine from crashing if all temps are identical
            if (max_t - min_t) < 0.5:
                max_t = min_t + 0.5
                
            # Force the color map to stretch perfectly across the new temperature bounds
            mesh_actor.mapper.scalar_range = (min_t, max_t)
            
            # Dynamically update the text labels
            if label_actor is not None:
                plotter.remove_actor(label_actor) 
                
            label_texts = [
                f"Left Axilla\n{latest_temps[0]:.1f} C",
                f"Right Axilla\n{latest_temps[1]:.1f} C",
                f"C7 Trunk\n{latest_temps[2]:.1f} C"
            ]
            
            label_actor = plotter.add_point_labels(
                LABEL_COORDS, 
                label_texts, 
                point_size=0, 
                font_size=12,
                text_color="black",
                shape_opacity=0.7
            )
            
            plotter.update()
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("Closing application...")
        plotter.close()

if __name__ == "__main__":
    main()