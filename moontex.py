__version__ = "0.2.1"

import os
from PIL import Image
import noise


class MoonTex:
	"""
	Generate grayscale moon textures for all major lunar phases
	using 2D simplex noise.

	v0.2.1 changes:
	- Skybox-safe dark side rendering (no bg_color tint bleeding)
	- Optional transparent background (RGBA)
	- Phase index OR phase name support
	- Preview rendering (size override)
	- Slightly smoother moon edge

	NOTE:
	- Free MoonTex exports images only (PNG).
	"""

	def __init__(
		self,
		image_size=300,
		bg_color=(5, 5, 20),
		noise_scale=0.01,
		octaves=3,
		persistence=0.5,
		lacunarity=3,
		seed=0,
		intensity=0.4,
		invert_crater_noise=True,
		brightness=(50, 230),
		transparent_background=False,
		padding=4,
		edge_softness=1.5,
		shadow_factor=0.15,
		shadow_mode="bg",   # "bg" (legacy) or "neutral" (skybox-safe)
		dark_floor=0.0,     # 0..1 minimum dark-side visibility
	):
		self.phases = [
			"New Moon",
			"Waxing Crescent",
			"First Quarter",
			"Waxing Gibbous",
			"Full Moon",
			"Waning Gibbous",
			"Last Quarter",
			"Waning Crescent",
		]

		# Image size
		self.image_size = self._validate_image_size(image_size)

		# Background color (used for non-transparent output + legacy shadows)
		self.bg_color = self._validate_color(bg_color, "bg_color")

		# Transparent background (RGBA)
		if not isinstance(transparent_background, bool):
			raise ValueError("transparent_background must be a bool.")
		self.transparent_background = transparent_background

		# Padding so the moon doesn't hug the edges
		self.padding = self._validate_positive_int(padding, "padding", min_value=0)

		# Soft edge blending
		self.edge_softness = self._validate_float_range(
			edge_softness, "edge_softness", 0.0, 10.0
		)

		# Shadow strength
		self.shadow_factor = self._validate_float_range(
			shadow_factor, "shadow_factor", 0.0, 1.0
		)

		# Shadow mode
		if shadow_mode not in ("bg", "neutral"):
			raise ValueError("shadow_mode must be 'bg' or 'neutral'.")
		self.shadow_mode = shadow_mode

		# Minimum visibility for dark side (earthshine)
		self.dark_floor = self._validate_float_range(dark_floor, "dark_floor", 0.0, 1.0)

		# Noise parameters
		self.noise_scale = self._validate_positive_float(noise_scale, "noise_scale")
		self.octaves = self._validate_positive_int(octaves, "octaves", min_value=1)
		self.persistence = self._validate_float_range(
			persistence, "persistence", 0.0, 1.0
		)
		self.lacunarity = self._validate_positive_float(lacunarity, "lacunarity")

		# Seed
		self.seed = int(seed)

		# Intensity
		self.intensity = self._validate_float_range(intensity, "intensity", 0.0, 1.0)

		# Invert crater flag
		if not isinstance(invert_crater_noise, bool):
			raise ValueError("invert_crater_noise must be a bool.")
		self.invert_crater_noise = invert_crater_noise

		# Brightness range
		self.brightness = self._validate_brightness(brightness)

	# ---------- VALIDATION HELPERS ----------

	def _validate_image_size(self, image_size):
		if image_size is None:
			return (300, 300)

		if isinstance(image_size, int):
			if image_size <= 0:
				raise ValueError("image_size must be positive.")
			return (image_size, image_size)

		if (
			isinstance(image_size, (tuple, list))
			and len(image_size) == 2
			and all(isinstance(v, int) for v in image_size)
		):
			w, h = image_size
			if w <= 0 or h <= 0:
				raise ValueError("image_size values must be positive.")
			return (w, h)

		raise ValueError("image_size must be int or (w, h).")

	def _validate_color(self, color, name):
		if (
			not isinstance(color, (tuple, list))
			or len(color) != 3
			or not all(isinstance(c, int) for c in color)
		):
			raise ValueError(f"{name} must be (r, g, b).")
		for c in color:
			if c < 0 or c > 255:
				raise ValueError(f"{name} values must be 0–255.")
		return tuple(color)

	def _validate_positive_float(self, value, name):
		value = float(value)
		if value <= 0:
			raise ValueError(f"{name} must be > 0.")
		return value

	def _validate_positive_int(self, value, name, min_value=1):
		value = int(value)
		if value < min_value:
			raise ValueError(f"{name} must be >= {min_value}.")
		return value

	def _validate_float_range(self, value, name, min_value, max_value):
		value = float(value)
		if not (min_value <= value <= max_value):
			raise ValueError(f"{name} must be between {min_value} and {max_value}.")
		return value

	def _validate_brightness(self, brightness):
		if not isinstance(brightness, (tuple, list)) or len(brightness) != 2:
			raise ValueError("brightness must be (min, max).")
		b0, b1 = int(brightness[0]), int(brightness[1])
		if not (0 <= b0 <= 255 and 0 <= b1 <= 255):
			raise ValueError("brightness must be 0–255.")
		if b0 > b1:
			raise ValueError("brightness min must be <= max.")
		return (b0, b1)

	# ---------- PHASE NORMALIZATION ----------

	def _normalize_phase(self, phase):
		if isinstance(phase, int):
			if not (0 <= phase < len(self.phases)):
				raise ValueError("phase index out of range.")
			return self.phases[phase]

		if not isinstance(phase, str):
			raise ValueError("phase must be str or int.")

		name = phase.strip().title()
		aliases = {"New": "New Moon", "Full": "Full Moon"}
		name = aliases.get(name, name)

		if name not in self.phases:
			raise ValueError(f"Invalid phase: {phase}")
		return name

	# ---------- CORE GENERATION ----------

	def generate(self, phase="Full Moon", size=None):
		phase = self._normalize_phase(phase)

		image_size = self.image_size if size is None else self._validate_image_size(size)
		w, h = image_size

		if self.transparent_background:
			img = Image.new("RGBA", image_size, (0, 0, 0, 0))
		else:
			img = Image.new("RGB", image_size, self.bg_color)

		pixels = img.load()

		cx, cy = w / 2, h / 2
		radius = (min(w, h) / 2) - self.padding
		radius_sq = radius * radius

		b0, b1 = self.brightness
		b_range = b1 - b0
		snoise2 = noise.snoise2

		shadow_offset_factor = {
			"Waxing Crescent": -0.3,
			"Waxing Gibbous": -1.4,
			"Waning Crescent": 0.3,
			"Waning Gibbous": 1.4,
		}.get(phase, None)

		for y in range(h):
			for x in range(w):
				dx = x - cx
				dy = y - cy
				dist_sq = dx * dx + dy * dy

				if dist_sq >= radius_sq:
					if not self.transparent_background:
						pixels[x, y] = self.bg_color
					continue

				# Crater noise
				n = snoise2(
					dx * self.noise_scale,
					dy * self.noise_scale,
					octaves=self.octaves,
					persistence=self.persistence,
					lacunarity=self.lacunarity,
					base=self.seed,
				)

				crater = ((n + 1) / 2.0) * self.intensity
				gray_factor = (1 - crater) if self.invert_crater_noise else crater
				gray = int(b0 + b_range * gray_factor)
				gray = max(0, min(255, gray))
				r = g = b = gray

				# Lighting
				if phase == "New Moon":
					lit = False
				elif phase == "Full Moon":
					lit = True
				elif phase == "First Quarter":
					lit = dx >= 0
				elif phase == "Last Quarter":
					lit = dx <= 0
				else:
					offset = shadow_offset_factor * radius
					lit = not ((dx - offset) ** 2 + dy ** 2 <= radius_sq)

				if not lit:
					sf = self.shadow_factor

					# SKYBOX FIX
					if self.transparent_background or self.shadow_mode == "neutral":
						r = int(r * sf)
						g = int(g * sf)
						b = int(b * sf)

						if self.dark_floor > 0:
							floor_val = int(255 * self.dark_floor)
							r = max(r, floor_val)
							g = max(g, floor_val)
							b = max(b, floor_val)
					else:
						r = int(self.bg_color[0] * (1 - sf) + r * sf)
						g = int(self.bg_color[1] * (1 - sf) + g * sf)
						b = int(self.bg_color[2] * (1 - sf) + b * sf)

				# Soft edge
				if self.edge_softness > 0:
					edge_band = self.edge_softness + 1
					if radius_sq - dist_sq <= edge_band * edge_band:
						dist = dist_sq ** 0.5
						inner = radius - dist
						if inner < self.edge_softness:
							a = max(0.0, min(1.0, inner / self.edge_softness))
							if self.transparent_background:
								pixels[x, y] = (r, g, b, int(255 * a))
								continue
							else:
								r = int(self.bg_color[0] * (1 - a) + r * a)
								g = int(self.bg_color[1] * (1 - a) + g * a)
								b = int(self.bg_color[2] * (1 - a) + b * a)

				if self.transparent_background:
					pixels[x, y] = (r, g, b, 255)
				else:
					pixels[x, y] = (r, g, b)

		return img

	def generate_preview(self, phase="Full Moon", max_size=256):
		max_size = self._validate_positive_int(max_size, "max_size", 32)
		return self.generate(phase=phase, size=max_size)

	# ---------- EXPORT ----------

	def export_moon_phase_image(self, output_dir=".", phase=None):
		if phase is None:
			raise ValueError("phase is required.")

		phase = self._normalize_phase(phase)
		os.makedirs(output_dir, exist_ok=True)

		img = self.generate(phase)
		filename = phase.lower().replace(" ", "_") + ".png"
		path = os.path.join(output_dir, filename)
		img.save(path)
		return path

	def export_all_moon_phase_images(self, output_dir="."):
		return [self.export_moon_phase_image(output_dir, p) for p in self.phases]


if __name__ == "__main__":
	# Skybox-friendly defaults
	generator = MoonTex(
		transparent_background=True,
		shadow_mode="neutral",
		dark_floor=0.0,
		image_size=(500, 500)
	)
	generator.export_all_moon_phase_images("moons_v0_2_1")
	print("Export complete.")
