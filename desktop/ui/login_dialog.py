"""登录对话框"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from core.api_client import ApiClient
from core.config import settings


class LoginWorker(QThread):
    success = pyqtSignal(dict, dict)
    failed = pyqtSignal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            api = ApiClient(base_url=settings.API_BASE_URL)
            result = api.login(self.username, self.password)
            self.success.emit(result, {'username': self.username})
        except Exception as e:
            self.failed.emit(str(e))


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.token = ''
        self.user_info = {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(settings.APP_NAME)
        self.setFixedSize(420, 480)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        # Logo区域
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon = QLabel('🍽')
        logo_icon.setStyleSheet('font-size: 48px;')
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel(settings.APP_NAME)
        title.setFont(QFont('Microsoft YaHei', 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('color: #1d1d1f;')
        subtitle = QLabel('桌面客户端 v' + settings.APP_VERSION)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet('color: #86868b; font-size: 12px;')
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(title)
        logo_layout.addWidget(subtitle)
        layout.addLayout(logo_layout)

        layout.addSpacing(20)

        # 表单
        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名')
        self.username_input.setFixedHeight(44)
        self.username_input.setText('admin')
        form.addRow('用户名', self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('请输入密码')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(44)
        self.password_input.setText('admin123')
        form.addRow('密码', self.password_input)

        layout.addLayout(form)

        # 错误提示
        self.error_label = QLabel('')
        self.error_label.setStyleSheet('color: #ff453a; font-size: 12px;')
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        layout.addSpacing(10)

        # 登录按钮
        self.login_btn = QPushButton('登 录')
        self.login_btn.setFixedHeight(48)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a84ff;
                color: #ffffff;
                border: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0071e3; }
            QPushButton:pressed { background-color: #0060c0; }
            QPushButton:disabled { background-color: #a1a1a6; }
        """)
        self.login_btn.clicked.connect(self._handle_login)
        layout.addWidget(self.login_btn)

        # 底部提示
        footer = QLabel('连接: ' + settings.API_BASE_URL)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet('color: #c7c7cc; font-size: 11px;')
        layout.addWidget(footer)

        self.password_input.returnPressed.connect(self._handle_login)

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            self.error_label.setText('请输入用户名和密码')
            self.error_label.setVisible(True)
            return

        self.error_label.setVisible(False)
        self.login_btn.setEnabled(False)
        self.login_btn.setText('登录中...')

        self.worker = LoginWorker(username, password)
        self.worker.success.connect(self._on_success)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_success(self, token_data, user_data):
        self.token = token_data.get('access_token', '')
        self.user_info = user_data
        self.done(1)

    def _on_failed(self, msg):
        self.login_btn.setEnabled(True)
        self.login_btn.setText('登 录')
        self.error_label.setText(f'登录失败: {msg}')
        self.error_label.setVisible(True)
