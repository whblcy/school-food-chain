"""出库管理页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt


class StockOutDialog(QDialog):
    def __init__(self, parent=None, ingredients=None):
        super().__init__(parent)
        self.setWindowTitle('新增出库')
        self.setFixedSize(480, 380)
        self.ingredients = ingredients or []
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.ingredient_combo = QComboBox()
        for i in self.ingredients:
            stock = i.get('current_stock', 0)
            self.ingredient_combo.addItem(
                f"{i.get('name', '')} (库存: {stock})", i.get('id')
            )
        layout.addRow('食材 *', self.ingredient_combo)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 99999)
        self.quantity_spin.setDecimals(2)
        self.quantity_spin.setSuffix(' kg')
        layout.addRow('数量 *', self.quantity_spin)

        self.purpose_input = QLineEdit()
        self.purpose_input.setPlaceholderText('用途（如：午餐加工）')
        layout.addRow('用途', self.purpose_input)

        self.dept_input = QLineEdit()
        self.dept_input.setPlaceholderText('使用部门')
        layout.addRow('部门', self.dept_input)

        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText('备注')
        layout.addRow('备注', self.remark_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton('取消')
        cancel.setObjectName('defaultBtn')
        cancel.clicked.connect(self.reject)
        save = QPushButton('确认出库')
        save.setObjectName('primaryBtn')
        save.clicked.connect(self._validate)
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addRow(btn_layout)

    def _validate(self):
        if self.quantity_spin.value() <= 0:
            QMessageBox.warning(self, '提示', '请输入数量')
            return
        self.accept()

    def get_data(self):
        return {
            'ingredient_id': self.ingredient_combo.currentData(),
            'quantity': self.quantity_spin.value(),
            'purpose': self.purpose_input.text().strip(),
            'department': self.dept_input.text().strip(),
            'remark': self.remark_input.text().strip(),
        }


class StockOutView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('出库记录'))
        toolbar.addStretch()
        add_btn = QPushButton('+ 新增出库')
        add_btn.setObjectName('primaryBtn')
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['食材', '数量', '单价', '总额', '用途', '出库日期', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 80)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        try:
            result = self.api.get_stock_out_list()
            self.data = result if isinstance(result, list) else result.get('items', [])
        except Exception:
            self._load_mock()
        self._render()

    def _load_mock(self):
        self.data = [
            {'id': 1, 'ingredient_name': '东北大米', 'quantity': 100, 'unit_price': 3.20, 'total_price': 320, 'purpose': '午餐加工', 'created_at': '2025-06-20'},
            {'id': 2, 'ingredient_name': '五花肉', 'quantity': 30, 'unit_price': 28.00, 'total_price': 840, 'purpose': '午餐加工', 'created_at': '2025-06-20'},
            {'id': 3, 'ingredient_name': '西红柿', 'quantity': 50, 'unit_price': 4.50, 'total_price': 225, 'purpose': '晚餐加工', 'created_at': '2025-06-19'},
            {'id': 4, 'ingredient_name': '食用油', 'quantity': 5, 'unit_price': 65.00, 'total_price': 325, 'purpose': '午餐加工', 'created_at': '2025-06-19'},
        ]

    def _render(self):
        self.table.setRowCount(len(self.data))
        for r, item in enumerate(self.data):
            vals = [
                item.get('ingredient_name', ''),
                f"{item.get('quantity', 0)}",
                f"¥{item.get('unit_price', 0):.2f}",
                f"¥{item.get('total_price', 0):.2f}",
                item.get('purpose', ''),
                str(item.get('created_at', ''))[:10],
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, cell)
            view_btn = QPushButton('查看')
            view_btn.setObjectName('linkBtn')
            self.table.setCellWidget(r, 6, view_btn)

    def _add(self):
        try:
            ingredients = self.api.get_ingredients()
            ingredients = ingredients if isinstance(ingredients, list) else ingredients.get('items', [])
        except Exception:
            ingredients = [{'id': 1, 'name': '东北大米', 'current_stock': 500}]
        dlg = StockOutDialog(self, ingredients=ingredients)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.stock_out(dlg.get_data())
                QMessageBox.information(self, '成功', '出库成功')
            except Exception as e:
                QMessageBox.warning(self, '失败', f'出库失败: {e}')
            self.refresh()
