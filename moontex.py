import math
from PIL import Image
import noise

class MoonTex:
	"""
	Generate grayscale moon textures for all major lunar phases
	using 2D simplex noise.

	Features:
	- Adjustable crater noise intensity, brightness, and inversion
	- Configurable resolution, color, and noise parameters
	- Exports individual or full set of moon phases
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
	):
		self.phases = [
			"New",
			"Waxing Crescent",
			"First Quarter",
			"Waxing Gibbous",
			"Full",
			"Waning Gibbous",
			"Last Quarter",
			"Waning Crescent",
		]

		# Image size
		self.image_size = self._validate_image_size(image_size)

		# Background color
		self.bg_color = self._validate_color(bg_color, "bg_color")

		# Noise parameters
		self.noise_scale = self._validate_positive_float(noise_scale, "noise_scale")
		self.octaves = self._validate_positive_int(octaves, "octaves", min_value=1)
		self.persistence = self._validate_float_range(
			persistence, "persistence", 0.0, 1.0
		)
		self.lacunarity = self._validate_positive_float(lacunarity, "lacunarity")

		# Seed (any int)
		self.seed = int(seed)

		# Intensity (0 - 1 recommended)
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
				raise ValueError("image_size must be a positive integer.")
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

		raise ValueError(
			"image_size must be an int or a (width, height) tuple of positive ints."
		)

	def _validate_color(self, color, name):
		if (
			not isinstance(color, (tuple, list))
			or len(color) != 3
			or not all(isinstance(c, int) for c in color)
		):
			raise ValueError(f"{name} must be a tuple/list of 3 integers.")
		r, g, b = color
		for c in (r, g, b):
			if c < 0 or c > 255:
				raise ValueError(f"{name} components must be in range 0–255.")
		return (r, g, b)

	def _validate_positive_float(self, value, name):
		try:
			value = float(value)
		except (TypeError, ValueError):
			raise ValueError(f"{name} must be a number.")
		if value <= 0:
			raise ValueError(f"{name} must be > 0.")
		return value

	def _validate_positive_int(self, value, name, min_value=1):
		try:
			value = int(value)
		except (TypeError, ValueError):
			raise ValueError(f"{name} must be an integer.")
		if value < min_value:
			raise ValueError(f"{name} must be >= {min_value}.")
		return value

	def _validate_float_range(self, value, name, min_value, max_value):
		try:
			value = float(value)
		except (TypeError, ValueError):
			raise ValueError(f"{name} must be a number.")
		if not (min_value <= value <= max_value):
			raise ValueError(f"{name} must be between {min_value} and {max_value}.")
		return value

	def _validate_brightness(self, brightness):
		if (
			not isinstance(brightness, (tuple, list))
			or len(brightness) != 2
		):
			raise ValueError("brightness must be a (min, max) tuple or list.")

		try:
			b_min = int(brightness[0])
			b_max = int(brightness[1])
		except (TypeError, ValueError):
			raise ValueError("brightness values must be integers.")

		if not (0 <= b_min <= 255 and 0 <= b_max <= 255):
			raise ValueError("brightness values must be in range 0–255.")

		if b_min > b_max:
			raise ValueError("brightness min must be <= max.")

		return (b_min, b_max)


	# ---------- CORE GENERATION LOGIC ----------

	def generate(self, phase="Full"):

		# NEW: Phase validation
		if phase not in self.phases:
			raise ValueError(
				f"Invalid phase '{phase}'. Must be one of: {', '.join(self.phases)}"
			)

		img = Image.new("RGB", self.image_size, self.bg_color)
		pixels = img.load()

		w, h = self.image_size
		cx = w / 2
		cy = h / 2
		radius = min(w, h) / 2
		radius_sq = radius * radius  # NEW: faster distance comparison

		# Shadow offset for crescents/gibbous
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

				# NEW: faster distance check
				if dist_sq <= radius_sq:

					# crater noise
					nx = dx * self.noise_scale
					ny = dy * self.noise_scale
					n = noise.snoise2(
						nx,
						ny,
						octaves=self.octaves,
						persistence=self.persistence,
						lacunarity=self.lacunarity,
						base=self.seed,
					)

					crater = ((n + 1) / 2.0) * self.intensity
					gray_factor = (1.0 - crater) if self.invert_crater_noise else crater
					gray = int(self.brightness[0] + (self.brightness[1] - self.brightness[0]) * gray_factor)

					gray = max(0, min(255, gray))  # clamp

					r = g = b = gray

					# lighting model
					if phase == "New":
						lit = False
					elif phase == "Full":
						lit = True
					elif phase == "First Quarter":
						lit = (dx >= 0)
					elif phase == "Last Quarter":
						lit = (dx <= 0)
					else:
						offset = shadow_offset_factor * radius
						inside_shadow = (dx - offset) ** 2 + dy ** 2 <= radius_sq
						lit = not inside_shadow

					if not lit:
						shadow_factor = 0.15
						r = int(self.bg_color[0] * (1 - shadow_factor) + r * shadow_factor)
						g = int(self.bg_color[1] * (1 - shadow_factor) + g * shadow_factor)
						b = int(self.bg_color[2] * (1 - shadow_factor) + b * shadow_factor)

					pixels[x, y] = (r, g, b)

				else:
					pixels[x, y] = self.bg_color

		return img


	# ---------- EXPORT FUNCTIONS ----------

	def export_moon_phase_image(self, output_dir=".", phase=None):
		if phase not in self.phases:
			raise ValueError(f"Invalid phase: {phase}")
		img = self.generate(phase)
		img.save(f"{output_dir}/{phase} Moon.png")

	def export_all_moon_phase_images(self, output_dir="."):
		for p in self.phases:
			self.export_moon_phase_image(output_dir, p)


if __name__ == "__main__":
	generator = MoonTex()
	generator.export_all_moon_phase_images()
	print("Export complete.")
