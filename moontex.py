__version__ = "1.1.0"

import os
from PIL import Image
import noise


class MoonTex:
	"""
	MoonTex (Moon Texture Generator)

	Features:
	- Procedural moon surface texture via simplex noise
	- Manual crescent geometry via phase_offset (-1..1)
	- Moon tinting via RGB or hex (CQCalendar-compatible)
	- Shadow styles: blend / alpha / multiply / auto
	- Soft terminator edge (smooth light-to-dark boundary)
	- Optional transparent background

	Notes (v1.0.0 behavior):
	- Built-in phase names are validated against self.phases.
	- Custom phase strings are allowed ONLY if you provide phase_offset.

	Notes (v1.0.1 behavior):
	- If phase_offset is provided, it overrides built-in phase behavior.
	- phase_offset ~= 0 produces a quarter-like terminator (half-lit).
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
		shadow_mode="bg",   # legacy / compatibility
		dark_floor=0.0,     # min alpha in alpha-shadow mode
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

		self.image_size = self._validate_image_size(image_size)
		self.bg_color = self._validate_color(bg_color, "bg_color")
		self.transparent_background = bool(transparent_background)

		self.padding = self._validate_positive_int(padding, "padding", min_value=0)
		self.edge_softness = self._validate_float_range(edge_softness, "edge_softness", 0.0, 10.0)
		self.shadow_factor = self._validate_float_range(shadow_factor, "shadow_factor", 0.0, 1.0)

		if shadow_mode not in ("bg", "neutral"):
			raise ValueError("shadow_mode must be 'bg' or 'neutral'.")
		self.shadow_mode = shadow_mode

		self.dark_floor = self._validate_float_range(dark_floor, "dark_floor", 0.0, 1.0)

		self.noise_scale = self._validate_positive_float(noise_scale, "noise_scale")
		self.octaves = self._validate_positive_int(octaves, "octaves", min_value=1)
		self.persistence = self._validate_float_range(persistence, "persistence", 0.0, 1.0)
		self.lacunarity = self._validate_positive_float(lacunarity, "lacunarity")
		self.seed = int(seed)

		self.intensity = self._validate_float_range(intensity, "intensity", 0.0, 1.0)

		if not isinstance(invert_crater_noise, bool):
			raise ValueError("invert_crater_noise must be a bool.")
		self.invert_crater_noise = invert_crater_noise

		self.brightness = self._validate_brightness(brightness)

	# ---------- VALIDATION ----------

	def _validate_phase_offset(self, phase_offset):
		if phase_offset is None:
			return None
		return max(-1.0, min(1.0, float(phase_offset)))

	def _validate_image_size(self, image_size):
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

	def _validate_hex_color(self, value):
		if value is None:
			return None
		if not isinstance(value, str):
			raise ValueError("hex color must be a string.")
		s = value.lstrip("#")
		if len(s) != 6:
			raise ValueError("hex color must be #RRGGBB.")
		return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))

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

	# ---------- PHASE ----------

	def _normalize_phase(self, phase):
		if isinstance(phase, int):
			if not (0 <= phase < len(self.phases)):
				raise ValueError("phase index out of range.")
			return self.phases[phase]

		if not isinstance(phase, str):
			raise ValueError("phase must be str or int.")

		name = phase.strip().title()
		aliases = {"New": "New Moon", "Full": "Full Moon"}
		return aliases.get(name, name)

	# ---------- SMOOTHSTEP ----------

	def _smoothstep(self, e0, e1, x):
		if e0 == e1:
			return 1.0 if x >= e1 else 0.0
		t = (x - e0) / (e1 - e0)
		t = max(0.0, min(1.0, t))
		return t * t * (3 - 2 * t)

	# ---------- CORE ----------

	def generate(
		self,
		phase="Full Moon",
		size=None,
		phase_offset=None,
		moon_color_hex=None,
		moon_color_rgb=None,
		shadow_style="auto",
		shadow_color_hex=None,
		shadow_color_rgb=None,
		terminator_softness=1.25,
	):
		phase = self._normalize_phase(phase)
		phase_offset = self._validate_phase_offset(phase_offset)

		# Fix #1: validate phase usage
		# - If it's a known phase, ok.
		# - If it's custom, you MUST provide phase_offset (manual mode).
		is_builtin_phase = (phase in self.phases)
		if (not is_builtin_phase) and (phase_offset is None):
			raise ValueError(
				"Unknown phase name. Use one of MoonTex.phases, or provide phase_offset for custom phases."
			)

		if moon_color_rgb is not None:
			tint = self._validate_color(moon_color_rgb, "moon_color_rgb")
		else:
			tint = self._validate_hex_color(moon_color_hex) or (255, 255, 255)

		if shadow_color_rgb is not None:
			shadow_color = self._validate_color(shadow_color_rgb, "shadow_color_rgb")
		else:
			shadow_color = self._validate_hex_color(shadow_color_hex) or self.bg_color

		if shadow_style == "auto":
			shadow_style = "alpha" if self.transparent_background else "blend"

		if shadow_style not in ("blend", "alpha", "multiply"):
			raise ValueError("shadow_style must be 'blend', 'alpha', 'multiply', or 'auto'.")

		w, h = self.image_size if size is None else self._validate_image_size(size)

		img = Image.new(
			"RGBA" if self.transparent_background else "RGB",
			(w, h),
			(0, 0, 0, 0) if self.transparent_background else self.bg_color
		)
		pixels = img.load()

		cx, cy = w / 2, h / 2
		radius = (min(w, h) / 2) - self.padding
		radius_sq = radius * radius

		b0, b1 = self.brightness
		b_range = b1 - b0
		snoise2 = noise.snoise2

		default_offsets = {
			"Waxing Crescent": -0.75,
			"Waxing Gibbous": -0.25,
			"Waning Gibbous": 0.25,
			"Waning Crescent": 0.75,
		}

		feather = terminator_softness * (radius * 0.06)

		quarter_band = 0.12  # |phase_offset| below this blends toward quarter-like terminator

		for y in range(h):
			for x in range(w):
				dx = x - cx
				dy = y - cy
				dist_sq = dx * dx + dy * dy

				if dist_sq >= radius_sq:
					if not self.transparent_background:
						pixels[x, y] = self.bg_color
					continue

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

				# Fix #2: clamp gray before luminance conversion
				gray = max(0, min(255, gray))
				lum = gray / 255.0

				lr = int(tint[0] * lum)
				lg = int(tint[1] * lum)
				lb = int(tint[2] * lum)

				# Litness factor (0..1)
				# v1.0.1 change:
				# - If phase_offset is provided (even for built-in phases), it overrides built-in behavior.
				# - Manual mode treats phase_offset ~= 0 as a quarter-like terminator (half-lit).
				if is_builtin_phase and (phase_offset is None) and phase == "Full Moon":
					lit = 1.0
				elif is_builtin_phase and (phase_offset is None) and phase == "New Moon":
					lit = 0.0
				elif is_builtin_phase and (phase_offset is None) and phase == "First Quarter":
					lit = self._smoothstep(-feather, feather, dx)
				elif is_builtin_phase and (phase_offset is None) and phase == "Last Quarter":
					lit = 1.0 - self._smoothstep(-feather, feather, dx)
				else:
					# Manual/custom, or any built-in phase when phase_offset is provided.
					po = phase_offset
					if po is None:
						# built-in crescent/gibbous without explicit phase_offset
						po = default_offsets.get(phase, 0.0)

					abs_po = abs(po)

					# Quarter-like terminator near zero offset (requested behavior: phase_offset=0 -> quarter)
					if abs_po < quarter_band:
						# Waxing (negative): light on right. Waning (positive): light on left.
						if po > 0:
							lit_plane = 1.0 - self._smoothstep(-feather, feather, dx)
						else:
							lit_plane = self._smoothstep(-feather, feather, dx)

						# Blend into circle-based geometry as you move away from 0
						po_adj = quarter_band if po >= 0 else -quarter_band
						offset = (1.0 - abs(po_adj)) * radius
						dx_eff = -dx if po_adj < 0 else dx
						s = (dx_eff - offset) ** 2 + dy ** 2 - radius_sq
						lit_circle = self._smoothstep(-feather, feather, s)

						t = abs_po / quarter_band  # 0..1
						lit = (1.0 - t) * lit_plane + t * lit_circle
					else:
						offset = (1.0 - abs_po) * radius
						dx_eff = -dx if po < 0 else dx
						s = (dx_eff - offset) ** 2 + dy ** 2 - radius_sq
						lit = self._smoothstep(-feather, feather, s)

				sf = self.shadow_factor
				r, g, b = lr, lg, lb
				a = 255

				if shadow_style == "blend":
					sr = int(shadow_color[0] * (1 - sf) + lr * sf)
					sg = int(shadow_color[1] * (1 - sf) + lg * sf)
					sb = int(shadow_color[2] * (1 - sf) + lb * sf)
					r = int(sr * (1 - lit) + lr * lit)
					g = int(sg * (1 - lit) + lg * lit)
					b = int(sb * (1 - lit) + lb * lit)

				elif shadow_style == "alpha":
					min_a = int(255 * self.dark_floor)
					shadow_a = max(int(255 * sf), min_a)
					a = int(shadow_a * (1 - lit) + 255 * lit)

					# Keep a subtle darkening so the shadow side isn't identical
					r = int(lr * sf * (1 - lit) + lr * lit)
					g = int(lg * sf * (1 - lit) + lg * lit)
					b = int(lb * sf * (1 - lit) + lb * lit)

				elif shadow_style == "multiply":
					# Fix #3: implement multiply properly
					r = int(lr * (sf * (1 - lit) + lit))
					g = int(lg * (sf * (1 - lit) + lit))
					b = int(lb * (sf * (1 - lit) + lit))

				if self.transparent_background:
					pixels[x, y] = (r, g, b, a)
				else:
					pixels[x, y] = (r, g, b)

		return img
		
	def export_png(
		self,
		path,
		*,
		phase="Full Moon",
		size=None,
		phase_offset=None,
		moon_color_hex=None,
		moon_color_rgb=None,
		shadow_style="auto",
		shadow_color_hex=None,
		shadow_color_rgb=None,
		terminator_softness=1.25,
		makedirs=True
	):
		"""
		Convenience: generate one phase and save it as a PNG (or any PIL-supported format by extension).
		Returns the output path.
		"""
		if makedirs:
			dirname = os.path.dirname(path)
			if dirname:
				os.makedirs(dirname, exist_ok=True)

		img = self.generate(
			phase=phase,
			size=size,
			phase_offset=phase_offset,
			moon_color_hex=moon_color_hex,
			moon_color_rgb=moon_color_rgb,
			shadow_style=shadow_style,
			shadow_color_hex=shadow_color_hex,
			shadow_color_rgb=shadow_color_rgb,
			terminator_softness=terminator_softness
		)
		img.save(path)
		return path


	def export_cycle(
		self,
		out_dir,
		*,
		phases=None,
		size=None,
		moon_color_hex=None,
		moon_color_rgb=None,
		shadow_style="auto",
		shadow_color_hex=None,
		shadow_color_rgb=None,
		terminator_softness=1.25,
		phase_offsets=None,
		filename_fn=None,
		overwrite=True
	):
		"""
		Generate + export a full set of phases using the CURRENT MoonTex settings (noise/seed/etc).

		- phases: list[str] of phases. Defaults to self.phases.
		- phase_offsets: optional dict[str, float] for custom phases (required for unknown phase names).
		- filename_fn: optional function (phase:str) -> filename (no directory).
		- overwrite: if False, skips files that already exist.

		Returns a list of written file paths.
		"""
		os.makedirs(out_dir, exist_ok=True)

		if phases is None:
			phases = list(self.phases)

		if filename_fn is None:
			def filename_fn(p):
				return p.strip().replace(" ", "_").lower() + ".png"

		written = []

		for phase in phases:
			phase = str(phase).strip()
			if not phase:
				continue

			path = os.path.join(out_dir, filename_fn(phase))

			if (not overwrite) and os.path.exists(path):
				continue

			po = None
			if phase_offsets and phase in phase_offsets:
				po = phase_offsets[phase]

			img = self.generate(
				phase=phase,
				size=size,
				phase_offset=po,
				moon_color_hex=moon_color_hex,
				moon_color_rgb=moon_color_rgb,
				shadow_style=shadow_style,
				shadow_color_hex=shadow_color_hex,
				shadow_color_rgb=shadow_color_rgb,
				terminator_softness=terminator_softness
			)

			img.save(path)
			written.append(path)

		return written

if __name__ == "__main__":
	print("Testing MoonTex library...")

	# Create output directory
	OUT_DIR = "moontex_test_output"
	os.makedirs(OUT_DIR, exist_ok=True)

	# Initialize generator with obvious, visible parameters
	mt = MoonTex(
		image_size=512,
		seed=42,
		intensity=0.5,
		noise_scale=0.015,
		transparent_background=False
	)

	# -------------------------------------------------
	# Test 1: Basic generate() + manual save
	# -------------------------------------------------
	print("Test 1: generate() return value")
	img = mt.generate(phase="Full Moon", moon_color_hex="#ddddff")
	img.save(os.path.join(OUT_DIR, "manual_full_moon.png"))

	# -------------------------------------------------
	# Test 2: export_png()
	# -------------------------------------------------
	print("Test 2: export_png()")
	mt.export_png(
		os.path.join(OUT_DIR, "exported_red_full_moon.png"),
		phase="Full Moon",
		moon_color_hex="#ff4a4a"
	)

	# -------------------------------------------------
	# Test 3: export_cycle() with default phases
	# -------------------------------------------------
	print("Test 3: export_cycle() default phases")
	mt.export_cycle(
		os.path.join(OUT_DIR, "default_cycle"),
		moon_color_hex="#cfcfcf"
	)

	# -------------------------------------------------
	# Test 4: export_cycle() with fantasy phases
	# -------------------------------------------------
	print("Test 4: export_cycle() fantasy phases")
	mt.export_cycle(
		os.path.join(OUT_DIR, "fantasy_cycle"),
		phases=["Blood Moon", "Half Lit", "Thin Lune"],
		phase_offsets={
			"Blood Moon": 0.35,
			"Half Lit": 0.0,
			"Thin Lune": 0.85
		},
		moon_color_hex="#ff2b2b"
	)

	print("All tests complete.")
	print(f"Check the '{OUT_DIR}' folder for output images.")
