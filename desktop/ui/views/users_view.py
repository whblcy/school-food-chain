"""用户管理页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QComboBox, QDialog, QFormLayout, QMessageBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class UserDialog(QDialog):
    def __init__(self, parent=None, data=None, is_edit=False):
        super().__init__(parent)
        self.setWindowTitle('编辑用户' if is_edit else '新增用户')
        self.setFixedSize(480, 440)
        self.data = data or {}
        self.is_edit = is_edit
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.username_input = QLineEdit(self.data.get('username', ''))
        self.username_input.setDisabled(self.is_edit)
        layout.addRow('用户名 *', self.username_input)

        self.realname_input = QLineEdit(self.data.get('real_name', ''))
        layout.addRow('姓名', self.realname_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('不少于6位')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow('密码' + (' *' if not self.is_edit else ''), self.password_input)

        self.role_combo = QComboBox()
        roles = [
            ('super_admin', '系统管理员'),
            ('admin', '管理员'),
            ('manager', '经理'),
            ('operator', '操作员'),
            ('viewer', '查看者'),
        ]
        for val, label in roles:
            self.role_combo.addItem(label, val)
        current_role = self.data.get('role', 'operator')
        for i in range(self.role_combo.count()):
            if self.role_combo.itemData(i) == current_role:
                self.role_combo.setCurrentIndex(i)
                break
        layout.addRow('角色 *', self.role_combo)

        self.phone_input = QLineEdit(self.data.get('phone', ''))
        layout.addRow('手机号', self.phone_input)

        self.email_input = QLineEdit(self.data.get('email', ''))
        layout.addRow('邮箱', self.email_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton('取消')
        cancel.setObjectName('defaultBtn')
        cancel.clicked.connect(self.reject)
        save = QPushButton('保存')
        save.setObjectName('primaryBtn')
        save.clicked.connect(self._validate)
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addRow(btn_layout)

    def _validate(self):
        if not self.username_input.text().strip() and not self.is_edit:
            QMessageBox.warning(self, '提示', '请输入用户名')
            return
        if not self.is_edit and not self.password_input.text():
            QMessageBox.warning(self, '提示', '请输入密码')
            return
        self.accept()

    def get_data(self):
        data = {
            'username': self.username_input.text().strip(),
            'real_name': self.realname_input.text().strip(),
            'role': self.role_combo.currentData(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
        }
        if self.password_input.text():
            data['password'] = self.password_input.text()
        return data


class ResetPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('重置密码')
        self.setFixedSize(360, 200)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.pwd1 = QLineEdit()
        self.pwd1.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd1.setPlaceholderText('新密码')
        layout.addRow('新密码 *', self.pwd1)

        self.pwd2 = QLineEdit()
        self.pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd2.setPlaceholderText('确认密码')
        layout.addRow('确认密码 *', self.pwd2)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton('取消')
        cancel.setObjectName('defaultBtn')
        cancel.clicked.connect(self.reject)
        save = QPushButton('确认重置')
        save.setObjectName('primaryBtn')
        save.clicked.connect(self._validate)
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addRow(btn_layout)

    def _validate(self):
        if not self.pwd1.text() or len(self.pwd1.text()) < 6:
            QMessageBox.warning(self, '提示', '密码不少于6位')
            return
        if self.pwd1.text() != self.pwd2.text():
            QMessageBox.warning(self, '提示', '两次密码不一致')
            return
        self.accept()

    def get_password(self):
        return self.pwd1.text()


class UsersView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('用户管理'))
        toolbar.addStretch()
        add_btn = QPushButton('+ 新增用户')
        add_btn.setObjectName('primaryBtn')
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['用户名', '姓名', '角色', '手机号', '邮箱', '状态', '最后登录', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 200)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            result = self.api.get_users()
            self.data = result if isinstance(result, list) else result.get('items', [])
        except Exception:
            self._load_mock()
        self._render()

    def _load_mock(self):
        role_map = {'super_admin': '系统管理员', 'admin': '管理员', 'manager': '经理', 'operator': '操作员', 'viewer': '查看者'}
        self.data = [
            {'id': 1, 'username': 'admin', 'real_name': '系统管理员', 'role': 'super_admin', 'phone': '13800138000', 'email': 'admin@school.com', 'is_active': True, 'last_login': '2025-06-20 09:30'},
            {'id': 2, 'username': 'zhangsan', 'real_name': '张三', 'role': 'manager', 'phone': '13900139000', 'email': 'zs@school.com', 'is_active': True, 'last_login': '2025-06-19 17:20'},
            {'id': 3, 'username': 'lisi', 'real_name': '李四', 'role': 'operator', 'phone': '13700137000', 'email': 'ls@school.com', 'is_active': True, 'last_login': '2025-06-18 11:00'},
            {'id': 4, 'username': 'wangwu', 'real_name': '王五', 'role': 'operator', 'phone': '13600136000', 'email': 'ww@school.com', 'is_active': False, 'last_login': '2025-06-10 14:30'},
        ]
        self._role_map = role_map

    def _render(self):
        role_map = getattr(self, '_role_map', {
            'super_admin': '系统管理员', 'admin': '管理员', 'manager': '经理',
            'operator': '操作员', 'viewer': '查看者'
        })
        self.table.setRowCount(len(self.data))
        for r, item in enumerate(self.data):
            vals = [
                item.get('username', ''),
                item.get('real_name', ''),
                role_map.get(item.get('role', ''), item.get('role', '')),
                item.get('phone', ''),
                item.get('email', ''),
                '启用' if item.get('is_active', True) else '停用',
                str(item.get('last_login', ''))[:16],
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 5:
                    color = '#30d158' if item.get('is_active', True) else '#ff453a'
                    cell.setForeground(QColor(color))
                self.table.setItem(r, c, cell)

            ops = QWidget()
            ops_l = QHBoxLayout(ops)
            ops_l.setContentsMargins(4, 0, 4, 0)
            edit_btn = QPushButton('编辑')
            edit_btn.setObjectName('linkBtn')
            edit_btn.clicked.connect(lambda _, i=item: self._edit(i))
            ops_l.addWidget(edit_btn)
            reset_btn = QPushButton('重置密码')
            reset_btn.setObjectName('linkBtn')
            reset_btn.clicked.connect(lambda _, i=item: self._reset_pwd(i))
            ops_l.addWidget(reset_btn)
            del_btn = QPushButton('删除')
            del_btn.setObjectName('linkBtn')
            del_btn.setStyleSheet('color: #ff453a;')
            del_btn.clicked.connect(lambda _, i=item: self._delete(i))
            ops_l.addWidget(del_btn)
            self.table.setCellWidget(r, 7, ops)

    def _add(self):
        dlg = UserDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.create_user(dlg.get_data())
            except Exception:
                pass
            self.refresh()

    def _edit(self, item):
        dlg = UserDialog(self, data=item, is_edit=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.update_user(item['id'], dlg.get_data())
            except Exception:
                pass
            self.refresh()

    def _reset_pwd(self, item):
        dlg = ResetPasswordDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.update_user(item['id'], {'password': dlg.get_password()})
                QMessageBox.information(self, '成功', '密码已重置')
            except Exception as e:
                QMessageBox.warning(self, '失败', f'重置失败: {e}')

    def _delete(self, item):
        reply = QMessageBox.question(self, '确认', f'确定删除用户 "{item["username"]}" 吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_user(item['id'])
            except Exception:
                pass
            self.refresh()
