# MoonTex v0.2.1
![MoonTex Moon Phases](https://github.com/user-attachments/assets/a730efd3-7c5d-460c-94c1-1c7092e91706)

MoonTex is a noise-based texture generator that creates realistic grayscale moon phase images with customizable lighting, crater intensity, and export options for use in games, apps, and procedural art.

* Powered by Python, Pillow, and Noise.
* Creates 8 lunar phases from a single API.
* No dependencies beyond core libs + 2 lightweight packages.

***
## Dependency Installation
```
pip install -r requirements.txt
```
***
## How to Generate a Single Moon Phase Texture
```
#Initialize Generator
generator = moontex.MoonTex()

#You can specify the output directory if you want. Specify a moon phase name.
generator.export_moon_phase_image(output_dir=".", phase="Full")
```
***
## How to Generate All Moon Phase Textures
```
#Initialize Generator
generator = moontex.MoonTex()

#You can specify the output directory if you want. Specify a moon phase name.
generator.export_all_moon_phase_images(output=".")
```
***
## Customization Options
```
MoonTex(
	# --- Core image settings ---
	image_size=300,              # int or (width, height)
	bg_color=(5, 5, 20),         # background RGB (used if not transparent)

	# --- Noise / surface detail ---
	noise_scale=0.01,            # simplex noise scale
	octaves=3,                   # noise octaves
	persistence=0.5,             # noise persistence
	lacunarity=3,                # noise lacunarity
	seed=0,                      # deterministic seed
	intensity=0.4,               # crater contrast (0–1)
	invert_crater_noise=True,    # invert crater depth

	# --- Brightness ---
	brightness=(50, 230),        # grayscale min/max

	# --- Rendering options ---
	transparent_background=False,# RGBA output if True
	padding=4,                   # space between moon edge and image border
	edge_softness=1.5,           # soft edge blend (0 disables)

	# --- Shadow / dark side behavior ---
	shadow_factor=0.15,          # darkness strength (0–1)
	shadow_mode="bg",            # "bg" (blend to bg_color), "neutral" (darken toward black, skybox-safe)
	dark_floor=0.0,              # minimum dark-side visibility (0 = can disappear)
)
```
***
## Skybox Usage (Raycasting, Overlays)
```
MoonTex(
    transparent_background=True,
    shadow_mode="neutral",
    dark_floor=0.0,
)
```
***
## Standalone Image Usage
```
MoonTex(
    transparent_background=False,
    shadow_mode="bg",
)

```
***
## Valid Phases
* "New"
* "Waxing Crescent"
* "First Quarter"
* "Waxing Gibbous"
* "Full"
* "Waning Gibbous"
* "Last Quarter"
* "Waning Crescent"
***
## Related Libraries
* [CQCalendar](https://github.com/BriannaLadson/CQCalendar): A lightweight, tick-based time and calendar system for Python games and simulations.
* [TerraForge](https://github.com/BriannaLadson/TerraForge): A versatile Python toolset for procedural map generation.
