import unittest


def luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


class ThemeContrastTests(unittest.TestCase):
    def test_normal_disabled_selected_and_focus_contrast(self):
        pairs = [
            ("normal", "#0B1C30", "#FFFFFF", 4.5),
            ("desactivado", "#3E4947", "#E5EEFF", 4.5),
            ("seleccionado", "#0B1C30", "#DCE9FF", 4.5),
            ("foco", "#0F766E", "#FFFFFF", 3.0),
            ("navegacao", "#EAF1FF", "#213145", 4.5),
            ("accao", "#FFFFFF", "#0F766E", 4.5),
            ("erro", "#93000A", "#FFDAD6", 4.5),
            ("aviso", "#FFFFFF", "#9C573A", 4.5),
        ]
        for state, foreground, background, minimum in pairs:
            with self.subTest(state=state):
                light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
                self.assertGreaterEqual((light + 0.05) / (dark + 0.05), minimum)
