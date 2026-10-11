import unittest

from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from scanner_outo.ui.shell import Shell, NAVIGATION


class SidebarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = QMainWindow()
        self.window.disconnect_adapter = lambda: self.fail("Unexpected disconnect")
        self.shell = Shell(self.window)
        self.window.setCentralWidget(self.shell)
        for index in range(7):
            self.window.tabs.addTab(QWidget(), str(index))
        self.window.resize(1120, 740)
        self.window.show()
        QTest.qWait(50)
        self.addCleanup(self.window.close)

    def finish(self):
        QTest.qWait(300)
        self.assertEqual(self.shell.sidebar_animation.state(), QAbstractAnimation.State.Stopped)

    def test_toggle_animates_and_preserves_navigation(self):
        self.window.tabs.setCurrentIndex(2)
        QTest.mouseClick(self.shell.sidebar_toggle, Qt.MouseButton.LeftButton)
        QTest.qWait(90)
        self.assertGreater(self.shell.sidebar.width(), 72)
        self.assertLess(self.shell.sidebar.width(), 260)
        self.finish()
        self.assertEqual(self.shell.sidebar.width(), 72)
        self.assertEqual(self.shell.sidebar_toggle.accessibleName(), "Expandir barra lateral")
        self.assertTrue(self.shell.navigation[2].isChecked())
        self.assertEqual(self.window.tabs.currentIndex(), 2)
        self.shell.sidebar_toggle.setFocus()
        QTest.keyClick(self.shell.sidebar_toggle, Qt.Key.Key_Space)
        self.finish()
        self.assertEqual(self.shell.sidebar.width(), 260)
        self.assertEqual(self.shell.sidebar_toggle.toolTip(), "Recolher barra lateral")
        for index, title, _ in NAVIGATION:
            self.assertEqual(self.shell.navigation[index].text(), title)

    def test_quick_reversal_finishes_at_latest_target(self):
        self.shell.sidebar_toggle.click()
        QTest.qWait(70)
        self.shell.sidebar_toggle.click()
        self.finish()
        self.assertEqual(self.shell.sidebar.width(), 260)
        self.assertFalse(self.shell.compact)
        self.assertTrue(self.shell.link.isVisible())

    def test_responsive_default_and_manual_choice_survive_resize(self):
        self.window.resize(860, 600)
        QTest.qWait(50)
        self.assertEqual(self.shell.sidebar.width(), 72)
        self.shell.sidebar_toggle.click()
        self.finish()
        self.assertEqual(self.shell.sidebar.width(), 260)
        self.window.resize(1120, 740)
        QTest.qWait(50)
        self.assertEqual(self.shell.sidebar.width(), 260)
        self.shell.sidebar_toggle.click()
        self.finish()
        self.window.resize(1440, 900)
        QTest.qWait(50)
        self.assertEqual(self.shell.sidebar.width(), 72)


if __name__ == "__main__":
    unittest.main()
