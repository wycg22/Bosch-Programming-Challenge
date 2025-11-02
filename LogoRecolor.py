from PIL import Image
import numpy as np
from pathlib import Path
from typing import Union, Tuple
import argparse
import sys


class ColorConverter:
    """Handle color conversion between HEX and RGB formats"""

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert HEX color to RGB tuple"""
        hex_color = hex_color.strip().lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        if len(hex_color) != 6:
            raise ValueError(f"Invalid HEX color: {hex_color}")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def parse_color(color_input: str) -> Tuple[int, int, int]:
        """Parse color input (HEX or RGB) and return RGB tuple"""
        color_input = color_input.strip().lower()

        # HEX (#FF0000 or FF0000)
        if color_input.startswith("#") or all(c in "0123456789abcdef" for c in color_input if c != ","):
            try:
                return ColorConverter.hex_to_rgb(color_input)
            except ValueError:
                pass

        # RGB formats: "rgb(255,0,0)", "(255,0,0)", or "255,0,0"
        cleaned = color_input.replace("rgb", "").replace("(", "").replace(")", "").replace(" ", "")
        parts = cleaned.split(",")
        if len(parts) == 3:
            try:
                rgb = tuple(int(p) for p in parts)
                if all(0 <= c <= 255 for c in rgb):
                    return rgb
            except ValueError:
                pass

        raise ValueError(f"Invalid color format: {color_input}. Use HEX (#FF0000) or RGB (255,0,0).")


class NonWhiteRecolorer:
    """Recolor all non-white pixels of an image to a specified color"""

    def __init__(self, preserve_transparency: bool = True, white_threshold: int = 240):
        """
        Args:
            preserve_transparency: Keep alpha channel intact if True.
            white_threshold: RGB value above which pixels are treated as white (default: 240).
        """
        self.preserve_transparency = preserve_transparency
        self.white_threshold = white_threshold

    def recolor_image(
        self,
        input_path: Union[str, Path],
        color: Tuple[int, int, int],
        output_path: Union[str, Path] = None
    ) -> str:
        """Recolor all non-white pixels"""
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")

        if output_path is None:
            output_path = self._generate_output_path(input_path, color)

        with Image.open(input_path) as img:
            rgba_img = img.convert("RGBA")
            recolored_img = self._apply_color_to_nonwhite(rgba_img, color)
            recolored_img.save(output_path, "PNG", optimize=True)

        return str(output_path)

    def _apply_color_to_nonwhite(self, image: Image.Image, new_color: Tuple[int, int, int]) -> Image.Image:
        img_array = np.array(image).astype(np.float32)
        r, g, b, a = img_array[..., 0], img_array[..., 1], img_array[..., 2], img_array[..., 3]

        brightness = (r + g + b) / 3.0 / 255.0
        whiteness = np.clip(brightness, 0.0, 1.0)

        threshold = self.white_threshold / 255.0
        transition_width = 0.6  # Adjust this value
        
        # Transition starts at (threshold - transition_width) and ends at threshold
        transition_start = threshold - transition_width
        
        # Calculate distance with proper bounds
        distance = (whiteness - transition_start) / transition_width
        recolor_strength = 1.0 - np.clip(distance, 0, 1)
        
        recolor_strength[whiteness >= threshold] = 0.0

        mask = a > 0
        recolored = img_array.copy()
        for c in range(3):
            recolored[..., c][mask] = (
                r[mask] * (1 - recolor_strength[mask]) +
                new_color[c] * recolor_strength[mask]
            )

        return Image.fromarray(np.clip(recolored, 0, 255).astype(np.uint8), "RGBA")


    def _generate_output_path(self, input_path: Path, color: Tuple[int, int, int]) -> Path:
        """Generate output filename"""
        hex_code = f"{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        return input_path.parent / f"{input_path.stem}_recolored_{hex_code}.png"


class CommandLineInterface:
    """Command-line interface"""

    def __init__(self):
        self.converter = ColorConverter()

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description="Recolor all non-white pixels in a PNG image to a specified color.",
            epilog="""
Examples:
  python recolor.py logo.png "#00FF00"
  python recolor.py logo.png "rgb(0, 128, 255)" --output blue_logo.png
  python recolor.py logo.png "F00" -w 250
            """,
            formatter_class=argparse.RawTextHelpFormatter
        )

        parser.add_argument("input_file", help="Input PNG file path")
        parser.add_argument("color", help="New color in HEX (#00FF00) or RGB (0,255,0)")
        parser.add_argument("-o", "--output", help="Optional output file path")
        parser.add_argument("-w", "--white-threshold", type=int, default=250,
                            help="Pixels with R,G,B > threshold are considered white (default: 240)")

        return parser.parse_args()

    def run(self):
        args = self.parse_arguments()
        try:
            color = self.converter.parse_color(args.color)
            recolorer = NonWhiteRecolorer(white_threshold=args.white_threshold)
            out_path = recolorer.recolor_image(args.input_file, color, args.output)
            print(f"✅ Recoloring complete! Saved to: {out_path}")
        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    cli = CommandLineInterface()
    cli.run()


if __name__ == "__main__":
    main()
