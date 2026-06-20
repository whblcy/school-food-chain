"""财务统计页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str = '#0a84ff'):
        super().__init__()
        self.setObjectName('statCard')
        self.setFixedHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        lbl = QLabel(label)
        lbl.setObjectName('statLabel')
        layout.addWidget(lbl)
        val = QLabel(value)
        val.setObjectName('statValue')
        val.setStyleSheet(f'color: {color};')
        layout.addWidget(val)


class FinanceView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # 统计卡片
        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.card_month_total = StatCard('本月采购总额', '¥0', '#0a84ff')
        self.card_month_count = StatCard('本月入库笔数', '0', '#30d158')
        self.card_avg_price = StatCard('平均单价', '¥0', '#ff9f0a')
        self.card_supplier_count = StatCard('供应商数量', '0', '#bf5af2')
        cards.addWidget(self.card_month_total)
        cards.addWidget(self.card_month_count)
        cards.addWidget(self.card_avg_price)
        cards.addWidget(self.card_supplier_count)
        layout.addLayout(cards)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel('采购明细'))
        self.year_combo = QComboBox()
        self.year_combo.addItems(['2025', '2024'])
        toolbar.addWidget(self.year_combo)
        toolbar.addStretch()
        export_btn = QPushButton('导出报表')
        export_btn.setObjectName('defaultBtn')
        toolbar.addWidget(export_btn)
        layout.addLayout(toolbar)

        # 明细表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['食材', '品类', '供应商', '数量', '单价', '金额', '入库日期'])
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
        self.card_month_total.findChild(QLabel, 'statValue').setText('¥32,450')
        self.card_month_count.findChild(QLabel, 'statValue').setText('48')
        self.card_avg_price.findChild(QLabel, 'statValue').setText('¥15.80')
        self.card_supplier_count.findChild(QLabel, 'statValue').setText('24')

        self.detail_data = [
            {'ingredient_name': '东北大米', 'category': '粮油', 'supplier_name': '绿源粮油', 'quantity': 500, 'unit_price': 3.20, 'total_amount': 1600, 'date': '2025-06-20'},
            {'ingredient_name': '五花肉', 'category': '肉类', 'supplier_name': '鲜肉联', 'quantity': 100, 'unit_price': 28.00, 'total_amount': 2800, 'date': '2025-06-20'},
            {'ingredient_name': '西红柿', 'category': '蔬菜', 'supplier_name': '蔬菜基地A', 'quantity': 200, 'unit_price': 4.50, 'total_amount': 900, 'date': '2025-06-19'},
            {'ingredient_name': '食用油', 'category': '粮油', 'supplier_name': '绿源粮油', 'quantity': 50, 'unit_price': 65.00, 'total_amount': 3250, 'date': '2025-06-19'},
            {'ingredient_name': '鸡蛋', 'category': '蛋奶', 'supplier_name': '禽蛋批发', 'quantity': 300, 'unit_price': 12.00, 'total_amount': 3600, 'date': '2025-06-18'},
            {'ingredient_name': '草鱼', 'category': '水产', 'supplier_name': '水产批发', 'quantity': 80, 'unit_price': 18.00, 'total_amount': 1440, 'date': '2025-06-18'},
            {'ingredient_name': '土豆', 'category': '蔬菜', 'supplier_name': '蔬菜基地A', 'quantity': 300, 'unit_price': 2.80, 'total_amount': 840, 'date': '2025-06-17'},
            {'ingredient_name': '酱油', 'category': '调味品', 'supplier_name': '调味品商行', 'quantity': 20, 'unit_price': 8.50, 'total_amount': 170, 'date': '2025-06-17'},
        ]

    def _render(self):
        self.table.setRowCount(len(self.detail_data))
        for r, item in enumerate(self.detail_data):
            vals = [
                item.get('ingredient_name', ''),
                item.get('category', ''),
                item.get('supplier_name', ''),
                f"{item.get('quantity', 0)}",
                f"¥{item.get('unit_price', 0):.2f}",
                f"¥{item.get('total_amount', 0):.2f}",
                item.get('date', ''),
            ]
            for c, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 5:
                    cell.setForeground(QColor('#ff453a'))
                self.table.setItem(r, c, cell)
