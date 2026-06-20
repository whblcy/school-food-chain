"""食材管理页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class IngredientDialog(QDialog):
    def __init__(self, parent=None, data=None, suppliers=None):
        super().__init__(parent)
        self.setWindowTitle('编辑食材' if data else '新增食材')
        self.setFixedSize(480, 400)
        self.data = data or {}
        self.suppliers = suppliers or []
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.name_input = QLineEdit(self.data.get('name', ''))
        self.name_input.setPlaceholderText('食材名称')
        layout.addRow('名称 *', self.name_input)

        self.code_input = QLineEdit(self.data.get('code', ''))
        self.code_input.setPlaceholderText('编码')
        layout.addRow('编码 *', self.code_input)

        self.category_input = QComboBox()
        self.category_input.addItems(['蔬菜', '肉类', '粮油', '调味品', '豆制品', '蛋奶', '水产', '水果', '其他'])
        layout.addRow('品类', self.category_input)

        self.unit_input = QLineEdit(self.data.get('unit', 'kg'))
        self.unit_input.setPlaceholderText('单位')
        layout.addRow('单位 *', self.unit_input)

        self.safety_spin = QDoubleSpinBox()
        self.safety_spin.setRange(0, 99999)
        self.safety_spin.setDecimals(1)
        self.safety_spin.setValue(self.data.get('safety_stock', 0))
        layout.addRow('安全库存', self.safety_spin)

        self.spec_input = QLineEdit(self.data.get('specification', ''))
        self.spec_input.setPlaceholderText('规格说明')
        layout.addRow('规格', self.spec_input)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton('取消')
        cancel_btn.setObjectName('defaultBtn')
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton('保存')
        save_btn.setObjectName('primaryBtn')
        save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)

    def _validate_and_accept(self):
        if not self.name_input.text().strip():
            QMessageBox.warning(self, '提示', '请输入食材名称')
            return
        self.accept()

    def get_data(self):
        return {
            'name': self.name_input.text().strip(),
            'code': self.code_input.text().strip(),
            'category': self.category_input.currentText(),
            'unit': self.unit_input.text().strip(),
            'safety_stock': self.safety_spin.value(),
            'specification': self.spec_input.text().strip(),
        }


class IngredientsView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.ingredients_data = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 工具栏
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索食材名称...')
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._filter)
        toolbar.addWidget(self.search_input)

        self.category_filter = QComboBox()
        self.category_filter.addItem('全部品类')
        self.category_filter.addItems(['蔬菜', '肉类', '粮油', '调味品', '豆制品', '蛋奶', '水产', '水果', '其他'])
        self.category_filter.currentTextChanged.connect(self._filter)
        toolbar.addWidget(self.category_filter)

        toolbar.addStretch()

        add_btn = QPushButton('+ 新增食材')
        add_btn.setObjectName('primaryBtn')
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['名称', '编码', '品类', '单位', '当前库存', '安全库存', '状态', '操作'])
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
            result = self.api.get_ingredients()
            self.ingredients_data = result if isinstance(result, list) else result.get('items', [])
        except Exception:
            self._load_mock()
        self._render_table()

    def _load_mock(self):
        self.ingredients_data = [
            {'id': 1, 'name': '东北大米', 'code': 'DC001', 'category': '粮油', 'unit': 'kg', 'current_stock': 500, 'safety_stock': 200},
            {'id': 2, 'name': '五花肉', 'code': 'RH001', 'category': '肉类', 'unit': 'kg', 'current_stock': 80, 'safety_stock': 50},
            {'id': 3, 'name': '西红柿', 'code': 'SC001', 'category': '蔬菜', 'unit': 'kg', 'current_stock': 30, 'safety_stock': 100},
            {'id': 4, 'name': '食用油', 'code': 'LY001', 'category': '粮油', 'unit': '桶', 'current_stock': 5, 'safety_stock': 20},
            {'id': 5, 'name': '鸡蛋', 'code': 'JD001', 'category': '蛋奶', 'unit': '盘', 'current_stock': 200, 'safety_stock': 50},
            {'id': 6, 'name': '酱油', 'code': 'TW001', 'category': '调味品', 'unit': '瓶', 'current_stock': 3, 'safety_stock': 15},
            {'id': 7, 'name': '土豆', 'code': 'SC002', 'category': '蔬菜', 'unit': 'kg', 'current_stock': 50, 'safety_stock': 100},
            {'id': 8, 'name': '草鱼', 'code': 'SC001', 'category': '水产', 'unit': 'kg', 'current_stock': 20, 'safety_stock': 30},
        ]

    def _filter(self):
        keyword = self.search_input.text().strip().lower()
        category = self.category_filter.currentText()
        filtered = []
        for item in self.ingredients_data:
            if keyword and keyword not in item.get('name', '').lower():
                continue
            if category != '全部品类' and item.get('category') != category:
                continue
            filtered.append(item)
        self._render_table(filtered)

    def _render_table(self, data=None):
        items = data or self.ingredients_data
        self.table.setRowCount(len(items))
        for r, item in enumerate(items):
            fields = ['name', 'code', 'category', 'unit', 'current_stock', 'safety_stock']
            for c, f in enumerate(fields):
                val = str(item.get(f, ''))
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, cell)

            # 状态
            stock = item.get('current_stock', 0)
            safety = item.get('safety_stock', 0)
            if stock <= 0:
                status, color = '缺货', '#ff453a'
            elif stock <= safety * 0.5:
                status, color = '紧急', '#ff453a'
            elif stock <= safety:
                status, color = '偏低', '#ff9f0a'
            else:
                status, color = '正常', '#30d158'
            status_cell = QTableWidgetItem(status)
            status_cell.setForeground(QColor(color))
            status_cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 6, status_cell)

            # 操作按钮
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(4, 0, 4, 0)
            ops_layout.setSpacing(4)

            edit_btn = QPushButton('编辑')
            edit_btn.setObjectName('linkBtn')
            edit_btn.clicked.connect(lambda checked, i=item: self._edit(i))
            ops_layout.addWidget(edit_btn)

            del_btn = QPushButton('删除')
            del_btn.setObjectName('linkBtn')
            del_btn.setStyleSheet('color: #ff453a;')
            del_btn.clicked.connect(lambda checked, i=item: self._delete(i))
            ops_layout.addWidget(del_btn)

            self.table.setCellWidget(r, 7, ops_widget)

    def _add(self):
        dlg = IngredientDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.create_ingredient(dlg.get_data())
            except Exception:
                pass
            self.refresh()

    def _edit(self, item):
        dlg = IngredientDialog(self, data=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.api.update_ingredient(item['id'], dlg.get_data())
            except Exception:
                pass
            self.refresh()

    def _delete(self, item):
        reply = QMessageBox.question(self, '确认', f'确定删除 "{item["name"]}" 吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_ingredient(item['id'])
            except Exception:
                pass
            self.refresh()
