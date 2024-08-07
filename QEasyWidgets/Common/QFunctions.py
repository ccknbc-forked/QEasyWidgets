import os
import darkdetect
import locale
from enum import Enum
from typing import Union, Optional
from ctypes import c_int, byref, windll
from PySide6.QtCore import Qt, QObject, QFile, QRect, QRectF, QSize, QTranslator, Signal, Slot, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QUrl
from PySide6.QtGui import QGuiApplication, QColor, QRgba64, QIcon, QIconEngine, QPainter, QPixmap, QImage, QFont, QDesktopServices
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtXml import QDomDocument
from PySide6.QtWidgets import *

from .Utils import *
from ..Resources.Sources import *

##############################################################################################################################

class CustomSignals_ComponentsCustomizer(QObject):
    '''
    Set up signals for components
    '''
    # Set theme
    Signal_SetTheme = Signal(str)

    # Set language
    Signal_SetLanguage = Signal(str)
    '''
    # Get clicked button
    Signal_ClickedButton = Signal(QMessageBox.StandardButton)
    '''

ComponentsSignals = CustomSignals_ComponentsCustomizer()

##############################################################################################################################

class Theme:
    '''
    '''
    Dark = 'Dark'
    Light = 'Light'

    Auto = darkdetect.theme()


class ThemeBase:
    '''
    '''
    THEME = Theme.Auto if Theme.Auto is not None else Theme.Dark

    def Update(self, theme: str):
        if theme in (Theme.Dark, Theme.Light):
            self.THEME = theme


EasyTheme = ThemeBase()

##############################################################################################################################

RegistratedWidgets = {}


class StyleSheetBase(Enum):
    '''
    '''
    Label = 'Label'
    Button = 'Button'
    ScrollArea = 'ScrollArea'
    Tree = 'Tree'
    ToolBox = 'ToolBox'
    SpinBox = 'SpinBox'
    ComboBox = 'ComboBox'
    Edit = 'Edit'
    Player = 'Player'
    Table = 'Table'

    Bar = 'Bar'
    Window = 'Window'
    Dialog = 'Dialog'

    def Registrate(self, widget, value):
        RegistratedWidgets[widget] = value

    def Deregistrate(self, widget):
        RegistratedWidgets.pop(widget)

    def Apply(self, widget: QWidget, theme: Optional[str] = None, registrate: bool = True):
        QApplication.processEvents()

        EasyTheme.Update(theme) if theme is not None else None

        Prefix = 'QSS'
        FilePath = f'QSS/{EasyTheme.THEME}/{self.value}.qss'
        File = QFile(Path(f':/{Prefix}').joinpath(FilePath))
        File.open(QFile.ReadOnly | QFile.Text)
        QSS = str(File.readAll(), encoding = 'utf-8')
        File.close()

        widget.setStyleSheet(QSS)

        self.Registrate(widget, self.value) if registrate else None


def Function_UpdateStyleSheet(
    theme: Optional[str] = None
):
    '''
    '''
    for Widget, value in list(RegistratedWidgets.items()):
        for Value in StyleSheetBase:
            if Value.value != value:
                continue
            try:
                Value.Apply(Widget, theme)
            except RuntimeError:
                Value.Deregistrate(Widget)
            finally:
                continue


ComponentsSignals.Signal_SetTheme.connect(Function_UpdateStyleSheet)

##############################################################################################################################

class IconEngine(QIconEngine):
    '''
    '''
    def __init__(self):
        super().__init__()

        self.IsIconSVG = False

    def loadSVG(self, SVGString: str):
        self.IsIconSVG = True
        self.Icon = SVGString.encode(errors = 'replace')

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State) -> None:
        if self.IsIconSVG:
            renderer = QSvgRenderer(self.Icon)
            renderer.render(painter, QRectF(rect))
        else:
            super().paint(painter, rect, mode, state)

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        image = QImage(size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        pixmap = QPixmap.fromImage(image, Qt.NoFormatConversion)

        painter = QPainter(pixmap)
        rect = QRect(0, 0, size.width(), size.height())
        self.paint(painter, rect, mode, state)

        return pixmap


class IconBase(Enum):
    '''
    '''
    Ellipsis = 'Ellipsis'
    OpenedFolder = 'OpenedFolder'
    Play = 'Play'
    Pause = 'Pause'
    Dash = 'Dash'
    FullScreen = 'FullScreen'
    X = 'X'

    def paint(self, painter: QPainter, rect: Union[QRect, QRectF], theme: Optional[str] = None):
        Prefix = 'Icons'
        IconPath = f'Icons/{theme if theme is not None else EasyTheme.THEME}/{self.value}.svg'
        IconPath = Path(f':/{Prefix}').joinpath(IconPath).as_posix()
        Renderer = QSvgRenderer(IconPath)
        Renderer.render(painter, QRectF(rect))

    def create(self, theme: Optional[str] = None) -> QIcon:
        Prefix = 'Icons'
        IconPath = f'Icons/{theme if theme is not None else EasyTheme.THEME}/{self.value}.svg'
        File = QFile(Path(f':/{Prefix}').joinpath(IconPath))
        File.open(QFile.ReadOnly)
        DomDocument = QDomDocument()
        DomDocument.setContent(File.readAll())
        File.close()

        Engine = IconEngine()
        Engine.loadSVG(DomDocument.toString())
        Icon = QIcon(Engine)

        return Icon


def Function_DrawIcon(
    icon: Union[str, QIcon],
    painter: QPainter,
    rect: Union[QRect, QRectF]
):
    '''
    Draw icon
    '''
    if isinstance(icon, IconBase):
        icon.paint(painter, rect, EasyTheme.THEME)
    else:
        icon = QIcon(icon)
        icon.paint(painter, QRectF(rect).toRect(), Qt.AlignCenter, state = QIcon.Off)


def Function_ToQIcon(
    icon: Union[str, QIcon, IconBase]
):
    if isinstance(icon, IconBase):
        return icon.create()
    else:
        return QIcon(icon)

##############################################################################################################################

class Language:
    '''
    '''
    ZH = 'Chinese'
    EN = 'English'

    Auto = locale.getdefaultlocale()[0]


class LanguageBase:
    '''
    '''
    LANG = 'Chinese' if Language.Auto in ('zh', 'zh_CN') else 'English'

    def Update(self, language: str):
        if language in (Language.ZH, Language.EN):
            self.LANG = language


EasyLanguage= LanguageBase()

##############################################################################################################################

class TranslationBase(QTranslator):
    '''
    '''
    def __init__(self, parent = None):
        super().__init__(parent)

    def load(self, language: Optional[str] = None):
        EasyLanguage.Update(language) if language is not None else None

        Prefix = 'QM'
        FilePath = f'i18n/{EasyLanguage.LANG}.qm'
        FilePath = Path(f':/{Prefix}').joinpath(FilePath).as_posix()

        super().load(FilePath)


"""
def Function_UpdateLanguage(
    language: Optional[str] = None
):
    '''
    '''
    QApplication.processEvents()

    Translator = TranslationBase()
    Translator.load(language)

    QApplication.instance().installTranslator(Translator)


ComponentsSignals.Signal_SetLanguage.connect(Function_UpdateLanguage)
"""

##############################################################################################################################

def Function_FindChildUI(
    ParentUI: QWidget,
    ChildType: object
):
    '''
    Function to find child UI
    '''
    ParentUI_Children = ParentUI.children()

    for ParentUI_Child in ParentUI_Children:
        if isinstance(ParentUI_Child, ChildType):
            return ParentUI_Child


def Function_FindParentUI(
    ChildUI: QWidget,
    ParentType: object
):
    '''
    Function to find parent UI
    '''
    ChildUI_Parent = ChildUI.parent()

    while not isinstance(ChildUI_Parent, ParentType):
        try:
            ChildUI_Parent = ChildUI_Parent.parent()
        except:
            raise Exception(f"{ChildUI}'s parent UI not found! Please check if the layout is correct.")

    return ChildUI_Parent

##############################################################################################################################

def Function_SetFont(
    Widget: QWidget,
    FontSize:int = 12,
    Weight = QFont.Normal
):
    '''
    Set the font of widget
    '''
    Font = QFont()
    Font.setFamilies(['Microsoft YaHei'])
    Font.setPixelSize(FontSize)
    Font.setWeight(Weight)
    Widget.setFont(Font)

##############################################################################################################################

def Function_SetRetainSizeWhenHidden(
    Widget: QWidget,
    RetainSize: bool = True
):
    sizePolicy = Widget.sizePolicy()
    sizePolicy.setRetainSizeWhenHidden(RetainSize)
    Widget.setSizePolicy(sizePolicy)


def Function_SetDropShadowEffect(
    Widget: QWidget,
    Radius: float = 3.,
    Color: Union[QColor, QRgba64] = Qt.gray
):
    DropShadowEffect = QGraphicsDropShadowEffect()
    DropShadowEffect.setOffset(0, 0)
    DropShadowEffect.setBlurRadius(Radius)
    DropShadowEffect.setColor(Color)
    Widget.setGraphicsEffect(DropShadowEffect)

##############################################################################################################################

def Function_SetAnimation(
    Animation: QPropertyAnimation,
    StartValue,
    EndValue,
    Duration: int
):
    Animation.setStartValue(StartValue)
    Animation.setEndValue(EndValue)
    Animation.setDuration(Duration)
    Animation.setEasingCurve(QEasingCurve.InOutQuart)
    return Animation


def Function_SetWidgetPosAnimation(
    Widget: QWidget,
    Duration: int = 99
):
    OriginalGeometry = Widget.geometry()
    AlteredGeometry = QRect(OriginalGeometry.left(), OriginalGeometry.top() + OriginalGeometry.height() / Duration, OriginalGeometry.width(), OriginalGeometry.height())

    WidgetAnimation = QPropertyAnimation(Widget, b"geometry", Widget)

    return Function_SetAnimation(WidgetAnimation, OriginalGeometry, AlteredGeometry, Duration)


def Function_SetWidgetSizeAnimation(
    Frame: QWidget,
    TargetWidth: Optional[int] = None,
    TargetHeight: Optional[int] = None,
    Duration: int = 210,
    SupportSplitter: bool = False
):
    '''
    Function to animate widget size
    '''
    CurrentWidth = Frame.geometry().width() if Frame.size() == QSize(100, 30) else Frame.width()
    CurrentHeight = Frame.geometry().height() if Frame.size() == QSize(100, 30) else Frame.height()

    FrameAnimationMinWidth = QPropertyAnimation(Frame, b"minimumWidth", Frame)
    FrameAnimationMaxWidth = QPropertyAnimation(Frame, b"maximumWidth", Frame)
    FrameAnimationMinHeight = QPropertyAnimation(Frame, b"minimumHeight", Frame)
    FrameAnimationMaxHeight = QPropertyAnimation(Frame, b"maximumHeight", Frame)

    AnimationGroup = QParallelAnimationGroup(Frame)

    AnimationGroup.addAnimation(Function_SetAnimation(FrameAnimationMinWidth, CurrentWidth, TargetWidth, Duration)) if TargetWidth is not None and not SupportSplitter else None
    AnimationGroup.addAnimation(Function_SetAnimation(FrameAnimationMaxWidth, CurrentWidth, TargetWidth, Duration)) if TargetWidth is not None else None
    AnimationGroup.addAnimation(Function_SetAnimation(FrameAnimationMinHeight, CurrentHeight, TargetHeight, Duration)) if TargetHeight is not None and not SupportSplitter else None
    AnimationGroup.addAnimation(Function_SetAnimation(FrameAnimationMaxHeight, CurrentHeight, TargetHeight, Duration)) if TargetHeight is not None else None

    return AnimationGroup


def Function_SetWidgetOpacityAnimation(
    Widget: QWidget,
    OriginalOpacity: float,
    TargetOpacity: float,
    Duration: int = 99
):
    OpacityEffect = QGraphicsOpacityEffect()
    Widget.setGraphicsEffect(OpacityEffect)

    OriginalOpacity = OriginalOpacity
    AlteredOpacity = TargetOpacity

    WidgetAnimation = QPropertyAnimation(OpacityEffect, b"opacity", Widget)

    return Function_SetAnimation(WidgetAnimation, OriginalOpacity, AlteredOpacity, Duration)

##############################################################################################################################

def Function_SetNoContents(
    Widget: QWidget
):
    if isinstance(Widget, QStackedWidget):
        while Widget.count():
            Widget.removeWidget(Widget.widget(0))

##############################################################################################################################

def Function_SetText(
    Widget: QWidget,
    Text: str,
    SetHtml: bool = True,
    SetPlaceholderText: bool = False,
    PlaceholderText: Optional[str] = None
):
    if hasattr(Widget, 'setText'):
        Widget.setText(Text)
    if hasattr(Widget, 'setPlainText'):
        Widget.setPlainText(Text)
    if hasattr(Widget, 'setHtml') and SetHtml:
        Widget.setHtml(Text)
    if hasattr(Widget, 'setPlaceholderText') and SetPlaceholderText:
        Widget.setPlaceholderText(str(PlaceholderText) if Text.strip() in ('', str(None)) else Text)


def Function_GetText(
    Widget: QWidget,
    GetHtml: bool = False,
    GetPlaceholderText: bool = False
):
    if hasattr(Widget, 'text'):
        Text = Widget.text()
    if hasattr(Widget, 'toPlainText'):
        Text = Widget.toPlainText()
    if hasattr(Widget, 'toHtml') and GetHtml:
        Text = Widget.toHtml()
    if hasattr(Widget, 'placeholderText') and GetPlaceholderText:
        Text = Widget.placeholderText() if Text.strip() in ('', str(None)) else Text
    return Text

##############################################################################################################################

def Function_GetFileDialog(
    Mode: str,
    FileType: Optional[str] = None,
    Directory: Optional[str] = None
):
    os.makedirs(Directory, exist_ok = True) if Directory is not None and Path(Directory).exists() == False else None
    if Mode == 'SelectFolder':
        DisplayText = QFileDialog.getExistingDirectory(
            caption = "选择文件夹",
            dir = Directory if Directory is not None else os.getcwd()
        )
    if Mode == 'SelectFile':
        DisplayText, _ = QFileDialog.getOpenFileName(
            caption = "选择文件",
            dir = Directory if Directory is not None else os.getcwd(),
            filter = FileType if FileType is not None else '任意类型 (*.*)'
        )
    if Mode == 'SaveFile':
        DisplayText, _ = QFileDialog.getSaveFileName(
            caption = "保存文件",
            dir = Directory if Directory is not None else os.getcwd(),
            filter = FileType if FileType is not None else '任意类型 (*.*)'
        )
    return DisplayText

##############################################################################################################################

def GetMissingBorderPixels(hWnd: int):
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
        MissingBorderPixels = GetSystemMetrics(hWnd, BorderLengthIndex, dpiScaling) + GetSystemMetrics(hWnd, 92, dpiScaling) #MissingBorderPixels = win32api.GetSystemMetrics(MissingBorderLength) + win32api.GetSystemMetrics(win32con.SM_CXPADDEDBORDER)
        if not MissingBorderPixels > 0:
            def IsCompositionEnabled():
                Result = windll.dwmapi.DwmIsCompositionEnabled(byref(c_int(0)))
                return bool(Result.value)
            MissingBorderPixels = round((6 if IsCompositionEnabled() else 3) * Window.devicePixelRatio())
        MissingBorderSize.append(MissingBorderPixels)

    return MissingBorderSize

##############################################################################################################################

def Function_OpenURL(
    URL: Union[str, list],
    CreateIfNotExist: bool = False
):
    '''
    Function to open web/local URL
    '''
    def OpenURL(URL):
        QURL = QUrl().fromLocalFile(NormPath(URL))
        if QURL.isValid():
            os.makedirs(NormPath(URL), exist_ok = True) if CreateIfNotExist else None
            IsSucceeded = QDesktopServices.openUrl(QURL)
            RunCMD([f'start {URL}']) if not IsSucceeded else None
        else:
            print(f"Invalid URL: {URL} !")

    if isinstance(URL, str):
        OpenURL(URL)
    else:
        URLList = ToIterable(URL)
        for Index, URL in enumerate(URLList):
            #URL = Function_ParamsChecker(URLList)[Index] if isinstance(URL, QObject) else URL
            OpenURL(URL)

##############################################################################################################################