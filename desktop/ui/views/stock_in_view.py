"""入库管理页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox, QDateEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor


class StockInDialog(QDialog):
    def __init__(self, parent=None, ingredients=None, users=None):
        super().__init__(parent)
        self.setWindowTitle('新增入库')
        self.setFixedSize(520, 520)
        self.ingredients = ingredients or []
        self.users = users or []
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.ingredient_combo = QComboBox()
        for i in self.ingredients:
            self.ingredient_combo.addItem(f"{i.get('name', '')} ({i.get('code', '')})", i.get('id'))
        layout.addRow('食材 *', self.ingredient_combo)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 99999)
        self.quantity_spin.setDecimals(2)
        self.quantity_spin.setSuffix(' kg')
        layout.addRow('数量 *', self.quantity_spin)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999)
        self.price_spin.setDecimals(2)
        self.price_spin.setPrefix('¥ ')
        layout.addRow('单价 *', self.price_spin)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem('请选择供应商')
        layout.addRow('供应商', self.supplier_combo)

        self.production_date = QDateEdit()
        self.production_date.setCalendarPopup(True)
        self.production_date.setDate(QDate.currentDate())
        self.production_date.setDisplayFormat('yyyy-MM-dd')
        layout.addRow('生产日期', self.production_date)

        self.expiry_date = QDateEdit()
        self.expiry_date.setCalendarPopup(True)
        self.expiry_date.setDate(QDate.currentDate().addMonths(6))
        self.expiry_date.setDisplayFormat('yyyy-MM-dd')
        layout.addRow('保质期至', self.expiry_date)

        self.inspector1 = QComboBox()
        for u in self.users:
            self.inspector1.addItem(u.get('real_name') or u.get('username', ''), u.get('id'))
        layout.addRow('验收人1 *', self.inspector1)

        self.inspector2 = QComboBox()
        for u in self.users:
            self.inspector2.addItem(u.get('real_name') or u.get('username', ''), u.get('id'))
        layout.addRow('验收人2 *', self.inspector2)

        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText('备注')
        layout.addRow('备注', self.remark_input)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton('取消')
        cancel_btn.setObjectName('defaultBtn')
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton('确认入库')
        save_btn.setObjectName('primaryBtn')
        save_btn.clicked.connect(self._validate)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)

    def _validate(self):
        if self.ingredient_combo.currentIndex() < 0:
            QMessageBox.warning(self, '提示', '请选择食材')
            return
        if self.quantity_spin.value() <= 0:
            QMessageBox.warning(self, '提示', '请输入数量')
            return
        self.accept()

    def get_data(self):
        return {
            'ingredient_id': self.ingredient_combo.currentData(),
            'quantity': self.quantity_spin.value(),
            'unit_price': self.price_spin.value(),
            'production_date': self.production_date.date().toString('yyyy-MM-dd'),
            'expiry_date': self.expiry_date.date().toString('yyyy-MM-dd'),
            'inspector1_id': self.inspector1.currentData(),
            'inspector2_id': self.inspector2.currentData(),
            'remark': self.remark_input.text().strip(),
        }


class StockInView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('入库记录'))
        toolbar.addStretch()
        add_btn = QPushButton('+ 新增入库')
        add_btn.setObjectName('primaryBtn')
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['批次号', '食材', '数量', '单价', '总额', '供应商', '入库日期', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 80)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            result = self.api.get_stock_in_list()
            self.stock_data = result if isinstance(result, list) else result.get('items', [])
        except Exception:
            self._load_mock()
        self._render()

    def _load_mock(self):
        self.stock_data = [
            {'id': 1, 'batch_no': 'RK20250620001', 'ingredient_name': '东北大米', 'quantity': 500, 'unit_price': 3.20, 'total_price': 1600, 'supplier_name': '绿源粮油', 'created_at': '2025-06-20'},
            {'id': 2, 'batch_no': 'RK20250620002', 'ingredient_name': '五花肉', 'quantity': 100, 'unit_price': 28.00, 'total_price': 2800, 'supplier_name': '鲜肉联', 'created_at': '2025-06-20'},
            {'id': 3, 'batch_no': 'RK20250619001', 'ingredient_name': '西红柿', 'quantity': 200, 'unit_price': 4.50, 'total_price': 900, 'supplier_name': '蔬菜基地A', 'created_at': '2025-06-19'},
            {'id': 4, 'batch_no': 'RK20250619002', 'ingredient_name': '食用油', 'quantity': 50, 'unit_price': 65.00, 'total_price': 3250, 'supplier_name': '绿源粮油', 'created_at': '2025-06-19'},
            {'id': 5, 'batch_no': 'RK20250618001', 'ingredient_name': '鸡蛋', 'quantity': 300, 'unit_price': 12.00, 'total_price': 3600, 'supplier_name': '禽蛋批发', 'created_at': '2025-06-18'},
        ]

    def _render(self):
        self.table.setRowCount(len(self.stock_data))
        for r, item in enumerate(self.stock_data):
            vals = [
                item.get('batch_no', ''),
                item.get('ingredient_name', ''),
                f"{item.get('quantity', 0)}",
                f"¥{item.get('unit_price', 0):.2f}",
                f"¥{item.get('total_price', 0):.2f}",
                item.get('supplier_name', ''),
                str(item.get('created_at', ''))[:10],
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, cell)

            # 查看按钮
            view_btn = QPushButton('查看')
            view_btn.setObjectName('linkBtn')
            self.table.setCellWidget(r, 7, view_btn)

    def _add(self):
        try:
            ingredients = self.api.get_ingredients()
            ingredients = ingredients if isinstance(ingredients, list) else ingredients.get('items', [])
            users = self.api.get_users()
            users = users if isinstance(users, list) else users.get('items', [])
        except Exception:
            ingredients = [{'id': 1, 'name': '东北大米', 'code': 'DC001'}]
            users = [{'id': 1, 'username': 'admin', 'real_name': '管理员'}]

        dlg = StockInDialog(self, ingredients=ingredients, users=users)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.stock_in(dlg.get_data())
                QMessageBox.information(self, '成功', '入库成功')
            except Exception as e:
                QMessageBox.warning(self, '失败', f'入库失败: {e}')
            self.refresh()
