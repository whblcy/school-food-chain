"""主窗口 - 侧边栏导航 + 内容区"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QScrollArea,
    QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QFont

from ui.views.dashboard_view import DashboardView
from ui.views.ingredients_view import IngredientsView
from ui.views.stock_in_view import StockInView
from ui.views.stock_out_view import StockOutView
from ui.views.inventory_view import InventoryView
from ui.views.suppliers_view import SuppliersView
from ui.views.finance_view import FinanceView
from ui.views.trace_view import TraceView
from ui.views.users_view import UsersView

from core.config import settings


class MainWindow(QMainWindow):
    def __init__(self, api, user_info: dict):
        super().__init__()
        self.api = api
        self.user_info = user_info
        self.current_view = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(settings.APP_NAME)
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setObjectName('mainWindow')

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # 右侧区域
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 顶部栏
        self.header = self._create_header()
        right_layout.addWidget(self.header)

        # 内容区
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName('contentArea')
        right_layout.addWidget(self.content_stack, 1)

        main_layout.addWidget(right, 1)

        # 注册页面
        self._register_views()

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        title = QLabel('🍽 食材管理平台')
        title.setObjectName('sidebarTitle')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(56)
        layout.addWidget(title)

        # 导航按钮
        self.nav_buttons = []
        nav_items = [
            ('概览统计', 'dashboard'),
            ('食材管理', 'ingredients'),
            ('入库管理', 'stock_in'),
            ('出库管理', 'stock_out'),
            ('库存盘点', 'inventory'),
            ('供应商', 'suppliers'),
            ('财务统计', 'finance'),
            ('追溯管理', 'trace'),
            ('用户管理', 'users'),
        ]

        for label_text, key in nav_items:
            btn = QPushButton(f'  {label_text}')
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty('nav_key', key)
            btn.clicked.connect(lambda checked, k=key: self._navigate(k))
            layout.addWidget(btn)
            self.nav_buttons.append((key, btn))

        layout.addStretch()

        # 退出按钮
        logout_btn = QPushButton('  退出登录')
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff453a;
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-size: 13px;
                border-radius: 6px;
                margin: 2px 8px;
            }
            QPushButton:hover { background-color: #3a1a18; }
        """)
        logout_btn.clicked.connect(self._handle_logout)
        layout.addWidget(logout_btn)

        # 默认选中第一个
        if self.nav_buttons:
            self.nav_buttons[0][1].setChecked(True)

        return sidebar

    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName('headerBar')
        header.setFixedHeight(56)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        self.header_title = QLabel('概览统计')
        self.header_title.setObjectName('headerTitle')
        layout.addWidget(self.header_title)

        layout.addStretch()

        user_label = QLabel(f'👤 {self.user_info.get("username", "管理员")}')
        user_label.setObjectName('headerUser')
        layout.addWidget(user_label)

        return header

    def _register_views(self):
        views = {
            'dashboard': DashboardView(self.api),
            'ingredients': IngredientsView(self.api),
            'stock_in': StockInView(self.api),
            'stock_out': StockOutView(self.api),
            'inventory': InventoryView(self.api),
            'suppliers': SuppliersView(self.api),
            'finance': FinanceView(self.api),
            'trace': TraceView(self.api),
            'users': UsersView(self.api),
        }
        self.views = views
        for key, view in views.items():
            self.content_stack.addWidget(view)

    def _navigate(self, key: str):
        self.header_title.setText({
            'dashboard': '概览统计',
            'ingredients': '食材管理',
            'stock_in': '入库管理',
            'stock_out': '出库管理',
            'inventory': '库存盘点',
            'suppliers': '供应商管理',
            'finance': '财务统计',
            'trace': '追溯管理',
            'users': '用户管理',
        }.get(key, ''))

        for k, btn in self.nav_buttons:
            btn.setChecked(k == key)

        idx = list(self.views.keys()).index(key)
        self.content_stack.setCurrentIndex(idx)

        # 切换时刷新数据
        view = self.views[key]
        if hasattr(view, 'refresh'):
            view.refresh()

    def _handle_logout(self):
        reply = QMessageBox.question(
            self, '退出确认', '确定要退出登录吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, '退出确认', '确定要退出程序吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
