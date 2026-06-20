"""概览统计页面"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor


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


class DashboardView(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # 统计卡片
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        self.card_ingredients = StatCard('食材种类', '0', '#0a84ff')
        self.card_stock = StatCard('库存总量', '0', '#30d158')
        self.card_suppliers = StatCard('供应商', '0', '#ff9f0a')
        self.card_alerts = StatCard('低库存预警', '0', '#ff453a')

        cards_layout.addWidget(self.card_ingredients)
        cards_layout.addWidget(self.card_stock)
        cards_layout.addWidget(self.card_suppliers)
        cards_layout.addWidget(self.card_alerts)
        layout.addLayout(cards_layout)

        # 下方区域
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)

        # 最近入库
        recent_frame = QFrame()
        recent_frame.setObjectName('card')
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(20, 16, 20, 16)

        recent_title = QLabel('最近入库记录')
        recent_title.setObjectName('titleLabel')
        recent_layout.addWidget(recent_title)

        self.stock_in_table = QTableWidget()
        self.stock_in_table.setColumnCount(5)
        self.stock_in_table.setHorizontalHeaderLabels(['食材', '数量', '单价', '总额', '日期'])
        self.stock_in_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stock_in_table.setAlternatingRowColors(True)
        self.stock_in_table.setMaximumHeight(300)
        self.stock_in_table.verticalHeader().setVisible(False)
        self.stock_in_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        recent_layout.addWidget(self.stock_in_table)
        bottom_layout.addWidget(recent_frame, 1)

        # 低库存预警
        alert_frame = QFrame()
        alert_frame.setObjectName('card')
        alert_layout = QVBoxLayout(alert_frame)
        alert_layout.setContentsMargins(20, 16, 20, 16)

        alert_title = QLabel('低库存预警')
        alert_title.setObjectName('titleLabel')
        alert_layout.addWidget(alert_title)

        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(4)
        self.alert_table.setHorizontalHeaderLabels(['食材', '当前库存', '安全库存', '状态'])
        self.alert_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alert_table.setAlternatingRowColors(True)
        self.alert_table.setMaximumHeight(300)
        self.alert_table.verticalHeader().setVisible(False)
        self.alert_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        alert_layout.addWidget(self.alert_table)
        bottom_layout.addWidget(alert_frame, 1)

        layout.addLayout(bottom_layout)

    def refresh(self):
        try:
            # 加载食材数据
            ingredients = self.api.get_ingredients()
            items = ingredients if isinstance(ingredients, list) else ingredients.get('items', [])
            self.card_ingredients.card_ingredients = len(items)

            # 加载供应商
            suppliers = self.api.get_suppliers()
            sup_list = suppliers if isinstance(suppliers, list) else suppliers.get('items', [])
            self.card_suppliers.card_suppliers = len(sup_list)

            # 更新表格
            self._update_tables(items)
        except Exception:
            # 使用模拟数据
            self._load_mock_data()

    def _update_tables(self, items):
        # 统计
        total_stock = sum(i.get('current_stock', 0) for i in items)
        low_count = sum(1 for i in items if i.get('current_stock', 0) <= i.get('safety_stock', 0))

        self.card_ingredients.findChild(QLabel, 'statValue').setText(str(len(items)))
        self.card_stock.findChild(QLabel, 'statValue').setText(f'{total_stock:.0f}')
        self.card_alerts.findChild(QLabel, 'statValue').setText(str(low_count))

    def _load_mock_data(self):
        self.card_ingredients.findChild(QLabel, 'statValue').setText('128')
        self.card_stock.findChild(QLabel, 'statValue').setText('3,560')
        self.card_suppliers.findChild(QLabel, 'statValue').setText('24')
        self.card_alerts.findChild(QLabel, 'statValue').setText('5')

        # 最近入库
        stock_data = [
            ('东北大米', '500kg', '3.20', '1,600.00', '2025-06-20'),
            ('五花肉', '100kg', '28.00', '2,800.00', '2025-06-20'),
            ('西红柿', '200kg', '4.50', '900.00', '2025-06-19'),
            ('食用油', '50桶', '65.00', '3,250.00', '2025-06-19'),
            ('鸡蛋', '300盘', '12.00', '3,600.00', '2025-06-18'),
        ]
        self.stock_in_table.setRowCount(len(stock_data))
        for r, row_data in enumerate(stock_data):
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.stock_in_table.setItem(r, c, item)

        # 低库存
        alert_data = [
            ('食用油', '5桶', '20桶', '紧急'),
            ('酱油', '3瓶', '15瓶', '紧急'),
            ('土豆', '50kg', '100kg', '偏低'),
            ('鸡蛋', '20盘', '50盘', '偏低'),
            ('食盐', '2袋', '10袋', '紧急'),
        ]
        self.alert_table.setRowCount(len(alert_data))
        for r, row_data in enumerate(alert_data):
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 3:
                    color = QColor('#ff453a') if val == '紧急' else QColor('#ff9f0a')
                    item.setForeground(color)
                self.alert_table.setItem(r, c, item)
