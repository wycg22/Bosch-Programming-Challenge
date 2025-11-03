import unittest
import tempfile
import os
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

from LogoRecolor import ColorConverter, NonWhiteRecolorer


class TestColorConverter(unittest.TestCase):
    """Test color conversion and parsing functionality"""

    def setUp(self):
        self.converter = ColorConverter()

    def test_hex_to_rgb_6_digit(self):
        # Test 6-digit HEX colors
        self.assertEqual(self.converter.hex_to_rgb("#FF0000"), (255, 0, 0))
        self.assertEqual(self.converter.hex_to_rgb("#00FF00"), (0, 255, 0))
        self.assertEqual(self.converter.hex_to_rgb("#0000FF"), (0, 0, 255))
        self.assertEqual(self.converter.hex_to_rgb("#FFFFFF"), (255, 255, 255))
        self.assertEqual(self.converter.hex_to_rgb("#000000"), (0, 0, 0))
        self.assertEqual(self.converter.hex_to_rgb("#123456"), (18, 52, 86))

    def test_hex_to_rgb_3_digit(self):
        # Test 3-digit HEX colors
        self.assertEqual(self.converter.hex_to_rgb("#F00"), (255, 0, 0))
        self.assertEqual(self.converter.hex_to_rgb("#0F0"), (0, 255, 0))
        self.assertEqual(self.converter.hex_to_rgb("#00F"), (0, 0, 255))
        self.assertEqual(self.converter.hex_to_rgb("#FFF"), (255, 255, 255))

    def test_hex_to_rgb_no_hash(self):
        # Test HEX colors without hash
        self.assertEqual(self.converter.hex_to_rgb("FF0000"), (255, 0, 0))
        self.assertEqual(self.converter.hex_to_rgb("00FF00"), (0, 255, 0))

    def test_hex_to_rgb_invalid(self):
        # Test invalid HEX colors
        with self.assertRaises(ValueError):
            self.converter.hex_to_rgb("#GGGGGG")
        with self.assertRaises(ValueError):
            self.converter.hex_to_rgb("#FF")
        with self.assertRaises(ValueError):
            self.converter.hex_to_rgb("#FFFF")

    def test_parse_color_hex(self):
        # Test HEX color parsing
        self.assertEqual(self.converter.parse_color("#FF0000"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("FF0000"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("#F00"), (255, 0, 0))

    def test_parse_color_rgb(self):
        # Test RGB color parsing
        self.assertEqual(self.converter.parse_color("rgb(255,0,0)"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("(255,0,0)"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("255,0,0"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("0,128,255"), (0, 128, 255))

    def test_parse_color_rgb_with_spaces(self):
        # Test RGB with spaces
        self.assertEqual(self.converter.parse_color("rgb(255, 0, 0)"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("(255, 0, 0)"), (255, 0, 0))
        self.assertEqual(self.converter.parse_color("255, 0, 0"), (255, 0, 0))

    def test_parse_color_invalid(self):
        # Test invalid color formats
        with self.assertRaises(ValueError):
            self.converter.parse_color("not_a_color")
        with self.assertRaises(ValueError):
            self.converter.parse_color("rgb(256,0,0)")  # Value out of range
        with self.assertRaises(ValueError):
            self.converter.parse_color("255,0")  # Not enough values


class TestNonWhiteRecolorer(unittest.TestCase):
    """Test image recoloring functionality"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.recolorer = NonWhiteRecolorer()

    def tearDown(self):
        # Clean up temporary files
        for file in Path(self.temp_dir).glob("*"):
            file.unlink()
        os.rmdir(self.temp_dir)

    def create_test_image(self, filename, colors, size=(100, 100)):
        """Helper to create test images with specific colors"""
        filepath = Path(self.temp_dir) / filename
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw colored rectangles
        width_per_color = size[0] // len(colors)
        for i, color in enumerate(colors):
            x0 = i * width_per_color
            x1 = (i + 1) * width_per_color
            draw.rectangle([x0, 0, x1, size[1]], fill=color)
        
        img.save(filepath, "PNG")
        return filepath

    def test_recolor_image_basic(self):
        # Test basic recoloring with simple image
        test_colors = [(255, 0, 0, 255), (0, 255, 0, 255)]  # Red and green
        input_path = self.create_test_image("test_basic.png", test_colors)
        new_color = (0, 0, 255)  # Blue
        
        output_path = self.recolorer.recolor_image(input_path, new_color)
        
        # Verify output file exists
        self.assertTrue(Path(output_path).exists())
        
        # Load and verify the image
        with Image.open(output_path) as img:
            self.assertEqual(img.mode, "RGBA")
            # Check that image was processed (basic smoke test)

    def test_recolor_preserves_white(self):
        # Test that white pixels remain unchanged
        test_colors = [(255, 255, 255, 255), (200, 200, 200, 255)]  # White and gray
        input_path = self.create_test_image("test_white.png", test_colors)
        new_color = (0, 0, 255)  # Blue
        
        output_path = self.recolorer.recolor_image(input_path, new_color)
        
        with Image.open(output_path) as img:
            img_array = np.array(img)
            # White area should remain white (first quarter of image)
            white_region = img_array[:, :25]  # First quarter
            self.assertTrue(np.all(white_region[..., :3] == 255))  # RGB channels

    def test_recolor_changes_non_white(self):
        # Test that non-white pixels get recolored
        test_colors = [(0, 0, 0, 255), (100, 100, 100, 255)]  # Black and dark gray
        input_path = self.create_test_image("test_black.png", test_colors)
        new_color = (255, 0, 0)  # Red
        
        output_path = self.recolorer.recolor_image(input_path, new_color)
        
        with Image.open(output_path) as img:
            img_array = np.array(img)
            # Non-white regions should be recolored
            # We can't check exact values due to blending, but should not be original black
            non_white_region = img_array[:, 25:75]  # Middle section
            self.assertFalse(np.all(non_white_region[..., 0] == 0))  # Red channel changed

    def test_recolor_preserves_transparency(self):
        # Test that transparency is preserved
        test_colors = [(255, 0, 0, 128), (0, 255, 0, 255)]  # Semi-transparent and opaque
        input_path = self.create_test_image("test_transparent.png", test_colors)
        new_color = (0, 0, 255)  # Blue
        
        output_path = self.recolorer.recolor_image(input_path, new_color)
        
        with Image.open(output_path) as img:
            img_array = np.array(img)
            # Check that alpha values are preserved
            self.assertEqual(img_array[0, 0, 3], 128)  # First pixel alpha
            self.assertEqual(img_array[0, -1, 3], 255)  # Last pixel alpha

    def test_generate_output_path(self):
        # Test output filename generation
        input_path = Path("/path/to/test_image.png")
        color = (255, 0, 0)
        
        output_path = self.recolorer._generate_output_path(input_path, color)
        
        expected = Path("/path/to/test_image_recolored_rgb(255,0,0).png")
        self.assertEqual(output_path, expected)

    def test_recolor_nonexistent_file(self):
        # Test error handling for non-existent file
        with self.assertRaises(FileNotFoundError):
            self.recolorer.recolor_image("nonexistent.png", (255, 0, 0))

    def test_apply_color_to_nonwhite_smoke_test(self):
        # Smoke test for the core recoloring function
        # Create a simple test image
        img = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([2, 2, 8, 8], fill=(100, 100, 100, 255))
        
        new_color = (255, 0, 0)
        result = self.recolorer._apply_color_to_nonwhite(img, new_color)
        
        # Verify output is valid image
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (10, 10))
        self.assertEqual(result.mode, "RGBA")

    def test_edge_case_colors(self):
        # Test with edge case colors
        edge_colors = [
            (0, 0, 0, 255),        # Pure black
            (255, 255, 255, 255),  # Pure white  
            (250, 250, 250, 255),  # Almost white (at threshold)
            (1, 1, 1, 255),        # Very dark
        ]
        input_path = self.create_test_image("test_edge.png", edge_colors)
        new_color = (128, 128, 128)  # Gray
        
        output_path = self.recolorer.recolor_image(input_path, new_color)
        
        # Just verify it processes without error
        self.assertTrue(Path(output_path).exists())


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.converter = ColorConverter()
        self.recolorer = NonWhiteRecolorer()

    def tearDown(self):
        for file in Path(self.temp_dir).glob("*"):
            file.unlink()
        os.rmdir(self.temp_dir)

    def create_simple_test_image(self):
        """Create a simple test image"""
        filepath = Path(self.temp_dir) / "integration_test.png"
        img = Image.new("RGBA", (50, 50), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 40, 40], fill=(100, 100, 100, 255))
        img.save(filepath, "PNG")
        return filepath

    def test_complete_workflow_hex(self):
        # Test complete workflow with HEX color
        input_path = self.create_simple_test_image()
        color_input = "#FF0000"
        
        color = self.converter.parse_color(color_input)
        output_path = self.recolorer.recolor_image(input_path, color)
        
        self.assertTrue(Path(output_path).exists())
        self.assertIn("_recolored_rgb(255,0,0)", str(output_path))

    def test_complete_workflow_rgb(self):
        # Test complete workflow with RGB color
        input_path = self.create_simple_test_image()
        color_input = "rgb(0,255,0)"
        
        color = self.converter.parse_color(color_input)
        output_path = self.recolorer.recolor_image(input_path, color)
        
        self.assertTrue(Path(output_path).exists())
        self.assertIn("_recolored_rgb(0,255,0)", str(output_path))


if __name__ == "__main__":
    # Run tests
    unittest.main()