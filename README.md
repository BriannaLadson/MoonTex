# MoonTex v0.1.0
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
	image_size=300,          # int or (width, height)
	bg_color=(5, 5, 20),     # background RGB
	noise_scale=0.01,
	octaves=3,
	persistence=0.5,
	lacunarity=3,
	seed=0,
	intensity=0.4,           # crater contrast 0-1
	invert_crater_noise=True,
	brightness=(50, 230),    # grayscale min/max
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
