"""供应商管理页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QComboBox, QDialog, QFormLayout, QMessageBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class SupplierDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle('编辑供应商' if data else '新增供应商')
        self.setFixedSize(480, 420)
        self.data = data or {}
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.name_input = QLineEdit(self.data.get('name', ''))
        layout.addRow('名称 *', self.name_input)

        self.code_input = QLineEdit(self.data.get('code', ''))
        layout.addRow('编码 *', self.code_input)

        self.contact_input = QLineEdit(self.data.get('contact_person', ''))
        layout.addRow('联系人', self.contact_input)

        self.phone_input = QLineEdit(self.data.get('phone', ''))
        layout.addRow('电话', self.phone_input)

        self.email_input = QLineEdit(self.data.get('email', ''))
        layout.addRow('邮箱', self.email_input)

        self.address_input = QLineEdit(self.data.get('address', ''))
        layout.addRow('地址', self.address_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(['active', 'suspended', 'blacklisted'])
        status = self.data.get('status', 'active')
        idx = self.status_combo.findText(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        layout.addRow('状态', self.status_combo)

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
        if not self.name_input.text().strip():
            QMessageBox.warning(self, '提示', '请输入供应商名称')
            return
        self.accept()

    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'code': self.code_input.text().strip(),
            'contact_person': self.contact_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'address': self.address_input.text().strip(),
            'status': self.status_combo.currentText(),
        }


class SuppliersView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索供应商...')
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self._filter)
        toolbar.addWidget(self.search)

        self.status_filter = QComboBox()
        self.status_filter.addItems(['全部状态', 'active', 'suspended', 'blacklisted'])
        self.status_filter.currentTextChanged.connect(self._filter)
        toolbar.addWidget(self.status_filter)

        toolbar.addStretch()
        add_btn = QPushButton('+ 新增供应商')
        add_btn.setObjectName('primaryBtn')
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['名称', '编码', '联系人', '电话', '邮箱', '评分', '状态', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 160)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            result = self.api.get_suppliers()
            self.data = result if isinstance(result, list) else result.get('items', [])
        except Exception:
            self._load_mock()
        self._render()

    def _load_mock(self):
        self.data = [
            {'id': 1, 'name': '绿源粮油', 'code': 'GY001', 'contact_person': '张经理', 'phone': '13800001111', 'email': 'gy@food.com', 'rating': 4.8, 'status': 'active'},
            {'id': 2, 'name': '鲜肉联', 'code': 'XR001', 'contact_person': '李总', 'phone': '13800002222', 'email': 'xr@food.com', 'rating': 4.5, 'status': 'active'},
            {'id': 3, 'name': '蔬菜基地A', 'code': 'SC001', 'contact_person': '王主任', 'phone': '13800003333', 'email': 'sc@food.com', 'rating': 4.2, 'status': 'active'},
            {'id': 4, 'name': '禽蛋批发', 'code': 'QD001', 'contact_person': '赵经理', 'phone': '13800004444', 'email': 'qd@food.com', 'rating': 3.8, 'status': 'suspended'},
            {'id': 5, 'name': '调味品商行', 'code': 'TW001', 'contact_person': '刘老板', 'phone': '13800005555', 'email': 'tw@food.com', 'rating': 2.0, 'status': 'blacklisted'},
        ]

    def _filter(self):
        keyword = self.search.text().strip().lower()
        status = self.status_filter.currentText()
        filtered = []
        for item in self.data:
            if keyword and keyword not in item.get('name', '').lower():
                continue
            if status != '全部状态' and item.get('status') != status:
                continue
            filtered.append(item)
        self._render(filtered)

    def _render(self, data=None):
        items = data or self.data
        self.table.setRowCount(len(items))
        status_map = {'active': ('合作中', '#30d158'), 'suspended': ('已暂停', '#ff9f0a'), 'blacklisted': ('已拉黑', '#ff453a')}
        for r, item in enumerate(items):
            vals = [
                item.get('name', ''),
                item.get('code', ''),
                item.get('contact_person', ''),
                item.get('phone', ''),
                item.get('email', ''),
                f"{'⭐' * int(item.get('rating', 0))} {item.get('rating', 0):.1f}",
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, cell)

            status_text, status_color = status_map.get(item.get('status', ''), ('未知', '#86868b'))
            status_cell = QTableWidgetItem(status_text)
            status_cell.setForeground(QColor(status_color))
            status_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 6, status_cell)

            ops = QWidget()
            ops_l = QHBoxLayout(ops)
            ops_l.setContentsMargins(4, 0, 4, 0)
            edit_btn = QPushButton('编辑')
            edit_btn.setObjectName('linkBtn')
            edit_btn.clicked.connect(lambda _, i=item: self._edit(i))
            ops_l.addWidget(edit_btn)
            del_btn = QPushButton('删除')
            del_btn.setObjectName('linkBtn')
            del_btn.setStyleSheet('color: #ff453a;')
            del_btn.clicked.connect(lambda _, i=item: self._delete(i))
            ops_l.addWidget(del_btn)
            self.table.setCellWidget(r, 7, ops)

    def _add(self):
        dlg = SupplierDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.create_supplier(dlg.get_data())
            except Exception:
                pass
            self.refresh()

    def _edit(self, item):
        dlg = SupplierDialog(self, data=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.update_supplier(item['id'], dlg.get_data())
            except Exception:
                pass
            self.refresh()

    def _delete(self, item):
        reply = QMessageBox.question(self, '确认', f'确定删除 "{item["name"]}" 吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_supplier(item['id'])
            except Exception:
                pass
            self.refresh()
