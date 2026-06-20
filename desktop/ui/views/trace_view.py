"""追溯管理页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QLineEdit, QDialog, QFormLayout, QComboBox, QMessageBox,
    QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class TraceSearchDialog(QDialog):
    def __init__(self, parent=None, ingredients=None, stock_in_list=None):
        super().__init__(parent)
        self.setWindowTitle('生成追溯码')
        self.setFixedSize(440, 280)
        self.ingredients = ingredients or []
        self.stock_in_list = stock_in_list or []
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.ingredient_combo = QComboBox()
        for i in self.ingredients:
            self.ingredient_combo.addItem(i.get('name', ''), i.get('id'))
        layout.addRow('食材 *', self.ingredient_combo)

        self.stockin_combo = QComboBox()
        for s in self.stock_in_list:
            self.stockin_combo.addItem(f"{s.get('batch_no', '')} - {s.get('created_at', '')}", s.get('id'))
        layout.addRow('入库记录 *', self.stockin_combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel = QPushButton('取消')
        cancel.setObjectName('defaultBtn')
        cancel.clicked.connect(self.reject)
        save = QPushButton('生成')
        save.setObjectName('primaryBtn')
        save.clicked.connect(self.accept)
        btn_layout.addWidget(cancel)
        btn_layout.addWidget(save)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'ingredient_id': self.ingredient_combo.currentData(),
            'stock_in_id': self.stockin_combo.currentData(),
        }


class TraceView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 搜索栏
        search_frame = QFrame()
        search_frame.setObjectName('card')
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(20, 16, 20, 16)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入追溯码查询...')
        self.search_input.setFixedWidth(400)
        self.search_input.returnPressed.connect(self._search)
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton('查询')
        search_btn.setObjectName('primaryBtn')
        search_btn.clicked.connect(self._search)
        search_layout.addWidget(search_btn)

        gen_btn = QPushButton('+ 生成追溯码')
        gen_btn.setObjectName('defaultBtn')
        gen_btn.clicked.connect(self._generate)
        search_layout.addWidget(gen_btn)

        search_layout.addStretch()
        layout.addWidget(search_frame)

        # 追溯详情
        self.detail_frame = QFrame()
        self.detail_frame.setObjectName('card')
        self.detail_layout = QVBoxLayout(self.detail_frame)
        self.detail_layout.setContentsMargins(20, 16, 20, 16)
        self.detail_frame.setVisible(False)
        layout.addWidget(self.detail_frame)

        # 记录列表
        list_label = QLabel('最近追溯记录')
        list_label.setObjectName('titleLabel')
        layout.addWidget(list_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['追溯码', '食材', '供应商', '入库日期', '操作'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 80)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        self._load_mock()
        self._render_table()

    def _load_mock(self):
        self.trace_list = [
            {'trace_code': 'TR-20250620-A1B2C3', 'ingredient_name': '东北大米', 'supplier_name': '绿源粮油', 'stock_in_date': '2025-06-18', 'status': 'active'},
            {'trace_code': 'TR-20250619-D4E5F6', 'ingredient_name': '五花肉', 'supplier_name': '鲜肉联', 'stock_in_date': '2025-06-17', 'status': 'active'},
            {'trace_code': 'TR-20250615-G7H8I9', 'ingredient_name': '西红柿', 'supplier_name': '蔬菜基地A', 'stock_in_date': '2025-06-15', 'status': 'consumed'},
        ]

    def _render_table(self):
        self.table.setRowCount(len(self.trace_list))
        for r, item in enumerate(self.trace_list):
            vals = [
                item.get('trace_code', ''),
                item.get('ingredient_name', ''),
                item.get('supplier_name', ''),
                item.get('stock_in_date', ''),
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r, c, cell)
            view_btn = QPushButton('查看')
            view_btn.setObjectName('linkBtn')
            view_btn.clicked.connect(lambda _, i=item: self._show_detail(i))
            self.table.setCellWidget(r, 4, view_btn)

    def _search(self):
        code = self.search_input.text().strip()
        if not code:
            QMessageBox.warning(self, '提示', '请输入追溯码')
            return
        # 查找匹配
        for item in self.trace_list:
            if item['trace_code'] == code:
                self._show_detail(item)
                return
        QMessageBox.information(self, '提示', '未找到该追溯码')

    def _show_detail(self, item):
        self.detail_frame.setVisible(True)
        # 清空旧内容
        while self.detail_layout.count():
            child = self.detail_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        title = QLabel(f'追溯详情 - {item["trace_code"]}')
        title.setObjectName('titleLabel')
        self.detail_layout.addWidget(title)

        # 步骤
        steps_layout = QHBoxLayout()
        steps = ['采购入库', '质检审核', '库存管理', '出库使用']
        for i, step in enumerate(steps):
            step_frame = QFrame()
            step_layout = QVBoxLayout(step_frame)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle = QLabel('✓')
            circle.setStyleSheet('font-size: 24px; color: #30d158;')
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(circle)
            step_label = QLabel(step)
            step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_label.setStyleSheet('font-size: 12px; color: #636366;')
            step_layout.addWidget(step_label)
            steps_layout.addWidget(step_frame)
            if i < len(steps) - 1:
                arrow = QLabel('→')
                arrow.setStyleSheet('font-size: 20px; color: #c7c7cc;')
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                steps_layout.addWidget(arrow)
        self.detail_layout.addLayout(steps_layout)

        # 信息
        info = QLabel(
            f"食材: {item.get('ingredient_name', '')}  |  "
            f"供应商: {item.get('supplier_name', '')}  |  "
            f"入库日期: {item.get('stock_in_date', '')}  |  "
            f"状态: {'有效' if item.get('status') == 'active' else '已消耗'}"
        )
        info.setStyleSheet('color: #636366; font-size: 13px; padding: 12px 0;')
        self.detail_layout.addWidget(info)

    def _generate(self):
        try:
            ingredients = self.api.get_ingredients()
            ingredients = ingredients if isinstance(ingredients, list) else ingredients.get('items', [])
            stock_in = self.api.get_stock_in_list()
            stock_in = stock_in if isinstance(stock_in, list) else stock_in.get('items', [])
        except Exception:
            ingredients = [{'id': 1, 'name': '东北大米'}]
            stock_in = [{'id': 1, 'batch_no': 'RK001', 'created_at': '2025-06-20'}]

        dlg = TraceSearchDialog(self, ingredients=ingredients, stock_in_list=stock_in)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                result = self.api.generate_trace(**dlg.get_data())
                QMessageBox.information(self, '成功', f"追溯码: {result.get('trace_code', '')}")
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, '失败', f'生成失败: {e}')
