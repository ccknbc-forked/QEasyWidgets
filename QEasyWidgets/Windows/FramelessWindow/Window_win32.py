import win32gui
import win32con
import win32api
import win32print
from typing import Optional
from ctypes import Structure, c_int, POINTER, WinDLL, byref, windll
from ctypes.wintypes import UINT, HWND, RECT, MSG, LPRECT
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QEvent
from PySide6.QtGui import QGuiApplication, QFont, QCursor, QMouseEvent, QShowEvent, QCloseEvent, QMoveEvent, QResizeEvent
from PySide6.QtWidgets import QApplication, QWidget, QLabel

from ...Common.Theme import BackgroundColorAnimationBase
from ...Common.StyleSheet import StyleSheetBase
from ...Components.Bar import TitleBarBase

##############################################################################################################################

class MARGINS(Structure):
    '''
    typedef struct _MARGINS {
        int cxLeftWidth;
        int cxRightWidth;
        int cyTopHeight;
        int cyBottomHeight;
    } MARGINS, *PMARGINS;
    '''
    _fields_ = [
        ("cxLeftWidth",    c_int),
        ("cxRightWidth",   c_int),
        ("cyTopHeight",    c_int),
        ("cyBottomHeight", c_int),
    ]


PMARGINS = POINTER(MARGINS)


class WINDOWPOS(Structure):
    '''
    typedef struct tagWINDOWPOS {
        HWND hwnd;
        HWND hwndInsertAfter;
        int  x;
        int  y;
        int  cx;
        int  cy;
        UINT flags;
    } WINDOWPOS, *LPWINDOWPOS, *PWINDOWPOS;
    '''
    _fields_ = [
        ('hwnd',            HWND),
        ('hwndInsertAfter', HWND),
        ('x',               c_int),
        ('y',               c_int),
        ('cx',              c_int),
        ('cy',              c_int),
        ('flags',           UINT)
    ]


PWINDOWPOS = POINTER(WINDOWPOS)


class NCCALCSIZE_PARAMS(Structure):
    '''
    typedef struct tagNCCALCSIZE_PARAMS {
        RECT       rgrc[3];
        PWINDOWPOS lppos;
    } NCCALCSIZE_PARAMS, *LPNCCALCSIZE_PARAMS;
    '''
    _fields_ = [
        ('rgrc',  RECT*3),
        ('lppos', PWINDOWPOS)
    ]

##############################################################################################################################

def isWindowMaximized(hWnd: int):
    WindowPlacement = win32gui.GetWindowPlacement(hWnd)

    Result = WindowPlacement[1] == win32con.SW_MAXIMIZE if WindowPlacement else False

    return Result


def isWindowFullScreen(hWnd: int):
    hWnd = int(hWnd)

    WindowRect = win32gui.GetWindowRect(hWnd)

    hMonitor = win32api.MonitorFromWindow(hWnd, win32con.MONITOR_DEFAULTTOPRIMARY)
    MonitorInfo = win32api.GetMonitorInfo(hMonitor)

    Result = all(w == m for w, m in zip(WindowRect, MonitorInfo["Monitor"])) if WindowRect and MonitorInfo else False

    return Result

##############################################################################################################################

def getSystemMetrics(hWnd: int, index: int, dpiScaling: bool):
    if hasattr(windll.user32, 'GetSystemMetricsForDpi'):
        if hasattr(windll.user32, 'GetDpiForWindow'):
            dpi = windll.user32.GetDpiForWindow(hWnd)
        else:
            dpi = 96
            hdc = win32gui.GetDC(hWnd)
            if hdc:
                dpiX = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSX)
                dpiY = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
                if dpiX > 0 and dpiScaling:
                    dpi = dpiX
                if dpiY > 0 and not dpiScaling:
                    dpi = dpiY
                win32gui.ReleaseDC(hWnd, hdc)
        return windll.user32.GetSystemMetricsForDpi(index, dpi)

    else:
        return win32api.getSystemMetrics(index)


def getMissingBorderPixels(hWnd: int):
    MissingBorderSize = []

    for QWindow in QGuiApplication.allWindows():
        if QWindow.winId() == hWnd:
            Window = QWindow
            break

    SIZEFRAME = {
        win32con.SM_CXSIZEFRAME: True,
        win32con.SM_CYSIZEFRAME: False
    }
    for BorderLengthIndex, dpiScaling in SIZEFRAME.items():
        MissingBorderPixels = getSystemMetrics(hWnd, BorderLengthIndex, dpiScaling) + getSystemMetrics(hWnd, 92, dpiScaling) #MissingBorderPixels = win32api.getSystemMetrics(MissingBorderLength) + win32api.getSystemMetrics(win32con.SM_CXPADDEDBORDER)
        if not MissingBorderPixels > 0:
            def isCompositionEnabled():
                Result = windll.dwmapi.DwmIsCompositionEnabled(byref(c_int(0)))
                return bool(Result.value)
            MissingBorderPixels = round((6 if isCompositionEnabled() else 3) * Window.devicePixelRatio())
        MissingBorderSize.append(MissingBorderPixels)

    return MissingBorderSize

##############################################################################################################################

class WindowBase(BackgroundColorAnimationBase):
    '''
    '''
    showed = Signal()
    closed = Signal()

    langChanged = Signal()

    rectChanged = Signal(QRect)

    edge_size = 3 # 窗体边缘尺寸（出现缩放标记的范围）

    def __init__(self,
        min_width = 630, # 窗体的最小宽度
        min_height = 420, # 窗体的最小高度
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.titleBar = TitleBarBase(self)

        self.mask = QLabel(self)
        self.rectChanged.connect(self.mask.setGeometry)
        self.mask.setStyleSheet('background-color: rgba(0, 0, 0, 111);')
        self.mask.setAlignment(Qt.AlignCenter)
        self.mask.setFont(QFont('Microsoft YaHei', int(min_height / 10), QFont.Bold))
        self.mask.hide()

        self.resize(min_width, min_height)

    def _check_ifdraggable(self, pos) -> bool:
        return (0 < pos.x() < self.width() and 0 < pos.y() < self.titleBar.height()) if self.titleBar is not None else False

    def _move_window(self, pos) -> None:
        self.windowHandle().startSystemMove()
        QApplication.instance().postEvent(
            self.windowHandle(),
            QMouseEvent(
                QEvent.MouseButtonRelease,
                QPoint(-1, -1),
                Qt.LeftButton,
                Qt.NoButton,
                Qt.NoModifier
            )
        )

    def _resize_window(self, pos, edges) -> None:
        self.windowHandle().startSystemResize(edges) if edges is not None else None

    def event(self, event: QEvent) -> bool:
        self.langChanged.emit() if event.type() == QEvent.LanguageChange else None
        return super().event(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._check_ifdraggable(event.position()) == True and event.buttons() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._move_window(event.position())

    def mousePressEvent(self, event: QMouseEvent) -> None:
            return

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._check_ifdraggable(event.position()) == True:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._resize_window(event.position(), None)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._check_ifdraggable(event.position()) == True and event.buttons() == Qt.MouseButton.LeftButton:
            self.showNormal() if self.isMaximized() else self.showMaximized() #self.setWindowState(Qt.WindowState.WindowMaximized)

    def showEvent(self, event: QShowEvent) -> None:
        self.showed.emit()
        event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        event.accept()

    def moveEvent(self, event: QMoveEvent) -> None:
        self.rectChanged.emit(self.rect())

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.rectChanged.emit(self.rect())
        self.titleBar.resize(self.width(), self.titleBar.height()) if isinstance(self.titleBar, TitleBarBase) else None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def nativeEvent(self, eventType, message):
        Message = MSG.from_address(int(message))
        if Message.message == win32con.WM_NCCALCSIZE:
            if Message.wParam != 0:
                Rect = NCCALCSIZE_PARAMS.from_address(Message.lParam).rgrc[0]
                MissingHBorderPixels, MissingVBorderPixels = getMissingBorderPixels(Message.hWnd) if isWindowMaximized(Message.hWnd) and not isWindowFullScreen(Message.hWnd) else (0, 0)
                Rect.left += MissingHBorderPixels
                Rect.top += MissingVBorderPixels
                Rect.right -= MissingHBorderPixels
                Rect.bottom -= MissingVBorderPixels
                return True, win32con.WVR_REDRAW
            else:
                Rect = LPRECT.from_address(Message.lParam)
                return True, 0
        if Message.message == win32con.WM_NCHITTEST:
            border_width = self.edge_size if not isWindowMaximized(Message.hWnd) and not isWindowFullScreen(Message.hWnd) else 0
            left   = QCursor.pos().x() - self.x() < border_width
            top    = QCursor.pos().y() - self.y() < border_width
            right  = QCursor.pos().x() - self.x() > self.frameGeometry().width() - border_width
            bottom = QCursor.pos().y() - self.y() > self.frameGeometry().height() - border_width
            if True not in (left, top, right, bottom):
                pass
            elif left and top:
                return True, win32con.HTTOPLEFT
            elif left and bottom:
                return True, win32con.HTBOTTOMLEFT
            elif right and top:
                return True, win32con.HTTOPRIGHT
            elif right and bottom:
                return True, win32con.HTBOTTOMRIGHT
            elif left:
                return True, win32con.HTLEFT
            elif top:
                return True, win32con.HTTOP
            elif right:
                return True, win32con.HTRIGHT
            elif bottom:
                return True, win32con.HTBOTTOM
        return QWidget.nativeEvent(self, eventType, message)

    def setFrameless(self, setStrechable: bool = True, setDropShadowEffect: bool = True) -> None:
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        hWnd = self.winId()
        Index = win32con.GWL_STYLE
        Value = win32gui.GetWindowLong(hWnd, Index)
        win32gui.SetWindowLong(hWnd, Index, Value | win32con.WS_THICKFRAME | win32con.WS_CAPTION)
        if not setStrechable:
            self.edge_size = 0
        if setDropShadowEffect:
            ExtendFrameIntoClientArea = WinDLL("dwmapi").DwmExtendFrameIntoClientArea
            ExtendFrameIntoClientArea.argtypes = [c_int, PMARGINS]
            ExtendFrameIntoClientArea(hWnd, byref(MARGINS(-1, -1, -1, -1)))

    def setTitleBar(self, titleBar: Optional[QWidget]) -> None:
        try:
            self.titleBar.deleteLater()
            self.titleBar.hide()
            StyleSheetBase.Bar.deregistrate(self.titleBar)
        except:
            pass
        if titleBar is not None:
            self.titleBar = titleBar
            self.titleBar.setParent(self) if self.titleBar.parent() is None else None
            self.titleBar.raise_() if self.titleBar.isHidden() else None
        else:
            self.titleBar = None

    def showMask(self, setVisible: bool, maskContent: Optional[str] = None) -> None:
        if setVisible:
            self.mask.raise_() if self.mask.isHidden() else None
            self.mask.setText(maskContent) if maskContent is not None else self.mask.clear()
            self.mask.show()
        else:
            self.mask.clear()
            self.mask.hide()

##############################################################################################################################