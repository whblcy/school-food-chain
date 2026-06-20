"""库存盘点页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class InventoryDialog(QDialog):
    def __init__(self, parent=None, ingredients=None):
        super().__init__(parent)
        self.setWindowTitle('新增盘点')
        self.setFixedSize(440, 320)
        self.ingredients = ingredients or []
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.ingredient_combo = QComboBox()
        self.ingredient_combo.currentIndexChanged.connect(self._on_ingredient_changed)
        for i in self.ingredients:
            self.ingredient_combo.addItem(
                f"{i.get('name', '')} (系统库存: {i.get('current_stock', 0)})",
                i.get('id')
            )
        layout.addRow('食材 *', self.ingredient_combo)

        self.system_stock_label = QLabel('0')
        layout.addRow('系统库存', self.system_stock_label)

        self.actual_spin = QDoubleSpinBox()
        self.actual_spin.setRange(0, 99999)
        self.actual_spin.setDecimals(2)
        layout.addRow('实盘数量 *', self.actual_spin)

        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText('备注')
        layout.addRow('备注', self.remark_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton('取消')
        cancel.setObjectName('defaultBtn')
        cancel.clicked.connect(self.reject)
        save = QPushButton('保存盘点')
        save.setObjectName('primaryBtn')
        save.clicked.connect(self._validate)
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addRow(btn_layout)

        if self.ingredients:
            self._on_ingredient_changed(0)

    def _on_ingredient_changed(self, idx):
        if idx >= 0 and idx < len(self.ingredients):
            stock = self.ingredients[idx].get('current_stock', 0)
            self.system_stock_label.setText(str(stock))
            self.actual_spin.setValue(stock)

    def _validate(self):
        self.accept()

    def get_data(self):
        idx = self.ingredient_combo.currentIndex()
        system_stock = self.ingredients[idx].get('current_stock', 0) if idx >= 0 else 0
        return {
            'ingredient_id': self.ingredient_combo.currentData(),
            'system_stock': system_stock,
            'actual_stock': self.actual_spin.value(),
            'remark': self.remark_input.text().strip(),
        }


class InventoryView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('库存盘点记录'))
        toolbar.addStretch()
        add_btn = QPushButton('+ 新增盘点')
        add_btn.setObjectName('primaryBtn')
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['食材', '系统库存', '实盘数量', '差异', '状态', '盘点日期'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        self._load_mock()
        self._render()

    def _load_mock(self):
        self.data = [
            {'ingredient_name': '东北大米', 'system_stock': 500, 'actual_stock': 498, 'created_at': '2025-06-20'},
            {'ingredient_name': '五花肉', 'system_stock': 80, 'actual_stock': 80, 'created_at': '2025-06-20'},
            {'ingredient_name': '食用油', 'system_stock': 20, 'actual_stock': 18, 'created_at': '2025-06-19'},
            {'ingredient_name': '鸡蛋', 'system_stock': 200, 'actual_stock': 195, 'created_at': '2025-06-19'},
            {'ingredient_name': '酱油', 'system_stock': 15, 'actual_stock': 15, 'created_at': '2025-06-18'},
        ]

    def _render(self):
        self.table.setRowCount(len(self.data))
        for r, item in enumerate(self.data):
            vals = [
                item.get('ingredient_name', ''),
                f"{item.get('system_stock', 0)}",
                f"{item.get('actual_stock', 0)}",
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, cell)

            diff = item.get('actual_stock', 0) - item.get('system_stock', 0)
            diff_str = f"{diff:+.1f}"
            diff_cell = QTableWidgetItem(diff_str)
            diff_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if diff < 0:
                diff_cell.setForeground(QColor('#ff453a'))
            elif diff > 0:
                diff_cell.setForeground(QColor('#0a84ff'))
            self.table.setItem(r, 3, diff_cell)

            status = '一致' if diff == 0 else ('盘亏' if diff < 0 else '盘盈')
            status_cell = QTableWidgetItem(status)
            status_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if diff != 0:
                status_cell.setForeground(QColor('#ff9f0a'))
            self.table.setItem(r, 4, status_cell)

            date_cell = QTableWidgetItem(str(item.get('created_at', ''))[:10])
            date_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 5, date_cell)

    def _add(self):
        try:
            ingredients = self.api.get_ingredients()
            ingredients = ingredients if isinstance(ingredients, list) else ingredients.get('items', [])
        except Exception:
            ingredients = [{'id': 1, 'name': '东北大米', 'current_stock': 500}]
        dlg = InventoryDialog(self, ingredients=ingredients)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.inventory_check(dlg.get_data())
                QMessageBox.information(self, '成功', '盘点记录已保存')
            except Exception as e:
                QMessageBox.warning(self, '失败', f'保存失败: {e}')
            self.refresh()
