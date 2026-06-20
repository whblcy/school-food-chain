"""
学校食材供应链管理平台 - 桌面客户端
PyQt6 + QSS 现代UI
"""
import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from core.api_client import ApiClient
from core.config import settings


def main():
    # 高DPI支持
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 全局样式
    app.setStyleSheet(STYLESHEET)

    # 登录
    login = LoginDialog()
    if login.exec() != 1:
        sys.exit(0)

    token = login.token
    user_info = login.user_info

    # 主窗口
    api = ApiClient(base_url=settings.API_BASE_URL, token=token)
    window = MainWindow(api=api, user_info=user_info)
    window.show()

    sys.exit(app.exec())


STYLESHEET = """
/* ===== 全局 ===== */
QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1d1d1f;
}

/* ===== 主窗口 ===== */
#mainWindow {
    background-color: #f5f5f7;
}

/* ===== 侧边栏 ===== */
#sidebar {
    background-color: #1d1d1f;
    border: none;
}

#sidebarTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
    padding: 16px;
    border-bottom: 1px solid #333333;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #a1a1a6;
    border: none;
    padding: 12px 20px;
    text-align: left;
    font-size: 13px;
    border-radius: 6px;
    margin: 2px 8px;
}

#sidebar QPushButton:hover {
    background-color: #2d2d2f;
    color: #ffffff;
}

#sidebar QPushButton:checked {
    background-color: #0a84ff;
    color: #ffffff;
    font-weight: bold;
}

/* ===== 顶部栏 ===== */
#headerBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e5ea;
    padding: 0 24px;
}

#headerTitle {
    font-size: 18px;
    font-weight: bold;
    color: #1d1d1f;
}

#headerUser {
    color: #636366;
    font-size: 13px;
}

/* ===== 内容区 ===== */
#contentArea {
    background-color: #f5f5f7;
    padding: 20px;
}

/* ===== 卡片 ===== */
QFrame#card {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e5e5ea;
}

QFrame#statCard {
    background-color: #ffffff;
    border-radius: 12px;
    border: 1px solid #e5e5ea;
    padding: 16px;
}

#statValue {
    font-size: 28px;
    font-weight: bold;
    color: #1d1d1f;
}

#statLabel {
    font-size: 13px;
    color: #86868b;
}

/* ===== 表格 ===== */
QTableWidget {
    background-color: #ffffff;
    border-radius: 8px;
    border: 1px solid #e5e5ea;
    gridline-color: #e5e5ea;
    selection-background-color: #0071e3;
    selection-color: #ffffff;
    alternate-background-color: #f5f5f7;
}

QTableWidget::item {
    padding: 8px 12px;
}

QHeaderView::section {
    background-color: #f5f5f7;
    color: #636366;
    font-weight: bold;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #e5e5ea;
    font-size: 12px;
}

/* ===== 按钮 ===== */
QPushButton#primaryBtn {
    background-color: #0a84ff;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton#primaryBtn:hover {
    background-color: #0071e3;
}

QPushButton#primaryBtn:pressed {
    background-color: #0060c0;
}

QPushButton#dangerBtn {
    background-color: #ff453a;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: bold;
}

QPushButton#dangerBtn:hover {
    background-color: #d70015;
}

QPushButton#defaultBtn {
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px 20px;
}

QPushButton#defaultBtn:hover {
    background-color: #f5f5f7;
    border-color: #86868b;
}

QPushButton#linkBtn {
    background-color: transparent;
    color: #0a84ff;
    border: none;
    padding: 4px 8px;
    font-size: 12px;
}

QPushButton#linkBtn:hover {
    color: #0071e3;
    text-decoration: underline;
}

/* ===== 输入框 ===== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1d1d1f;
    font-size: 13px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #0a84ff;
    border-width: 2px;
}

QLineEdit:disabled, QSpinBox:disabled {
    background-color: #f5f5f7;
    color: #86868b;
}

/* ===== 下拉框 ===== */
QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    selection-background-color: #0a84ff;
    selection-color: #ffffff;
    padding: 4px;
}

/* ===== 日期选择 ===== */
QDateEdit {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px 12px;
}

QDateEdit::drop-down {
    border: none;
    width: 30px;
}

/* ===== 文本编辑 ===== */
QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #d1d1d6;
    border-radius: 8px;
    padding: 8px 12px;
}

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #c7c7cc;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a1a1a6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ===== 对话框 ===== */
QDialog {
    background-color: #ffffff;
    border-radius: 12px;
}

/* ===== 标签页 ===== */
QTabWidget::pane {
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    background-color: #ffffff;
}

QTabBar::tab {
    padding: 10px 24px;
    color: #636366;
    border: none;
    font-size: 13px;
}

QTabBar::tab:selected {
    color: #0a84ff;
    border-bottom: 2px solid #0a84ff;
    font-weight: bold;
}

QTabBar::tab:hover:!selected {
    color: #1d1d1f;
    background-color: #f5f5f7;
}

/* ===== 分组框 ===== */
QGroupBox {
    font-weight: bold;
    color: #1d1d1f;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
}

/* ===== 标签 ===== */
QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #1d1d1f;
}

QLabel#subtitleLabel {
    font-size: 13px;
    color: #86868b;
}

QLabel#greenTag {
    background-color: #30d158;
    color: #ffffff;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
}

QLabel#redTag {
    background-color: #ff453a;
    color: #ffffff;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
}

QLabel#yellowTag {
    background-color: #ffd60a;
    color: #1d1d1f;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
}

QLabel#blueTag {
    background-color: #0a84ff;
    color: #ffffff;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
}

QLabel#grayTag {
    background-color: #86868b;
    color: #ffffff;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
}

/* ===== 搜索框 ===== */
QLineEdit#searchInput {
    border: 1px solid #d1d1d6;
    border-radius: 20px;
    padding: 8px 16px 8px 36px;
    background-image: url();
    background-position: left 10px center;
}

/* ===== 加载指示 ===== */
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #e5e5ea;
    text-align: center;
    color: #636366;
    height: 6px;
}

QProgressBar::chunk {
    background-color: #0a84ff;
    border-radius: 4px;
}

/* ===== 消息提示 ===== */
QToolTip {
    background-color: #1d1d1f;
    color: #ffffff;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
}
"""


if __name__ == '__main__':
    main()
