from db import Database
from login_ui import Ui_Login
from main_window_ui import Ui_MainWindow
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from qt_material import apply_stylesheet


def db():
    return Database()


class BaseWindow(QMainWindow):
    def go_back(self):  # переходит на авторизацию
        self.back = LoginWindow()
        self.back.show()
        self.close()

    def clear_cards(self):  # очистка списка товаров
        while self.ui.verticalLayout_card.count():
            item = self.ui.verticalLayout_card.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def fill_table(self, table, rows):  # универсальное заполнение таблиц (заказов)
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row.values()):
                table.setItem(r, c, QTableWidgetItem(str(val)))

    def load_categories(self, all_label="Все товары"):  # загрузка категорий в комбобокс
        self.ui.comboBox_filtr_prod.addItem(all_label, 0)
        d = db()
        d.cursor.execute('SELECT * FROM categories')
        for cat in d.cursor.fetchall():
            self.ui.comboBox_filtr_prod.addItem(cat['name'], cat['category_id'])

    # --- Новая загрузка поставщиков ---
    def load_suppliers(self, all_label="Все поставщики"):
        self.ui.comboBox_filtr_suppliers.addItem(all_label, 0)
        d = db()
        d.cursor.execute('SELECT * FROM suppliers')
        for sup in d.cursor.fetchall():
            self.ui.comboBox_filtr_suppliers.addItem(sup['name'], sup['supplier_id'])

    def load_data(self):  # фильтрация, поиск и загрузка товаров
        self.clear_cards()
        cid = self.ui.comboBox_filtr_prod.currentData()
        sid = self.ui.comboBox_filtr_suppliers.currentData()  # Получаем ID поставщика напрямую
        search_text = self.ui.lineEdit_search.text().strip()

        d = db()
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if cid != 0 and cid is not None:
            query += " AND category_id = %s"
            params.append(cid)

        # Фильтрация по supplier_id
        if sid != 0 and sid is not None:
            query += " AND supplier_id = %s"
            params.append(sid)

        if search_text:
            query += " AND name LIKE %s"
            params.append(f"%{search_text}%")

        d.cursor.execute(query, tuple(params))
        for product in d.cursor.fetchall():
            self.add_card(product)

    def add_card(self, product):  # создание карточек товара с подсветкой и стилизацией цены
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(frame)

        photo = QLabel()
        photo.setFixedSize(80, 80)
        photo.setPixmap(QPixmap(product['image_path'] or "images/zagl.png").scaled(80, 80))
        layout.addWidget(photo)

        # Обработка цены и скидки
        discount = int(product['discount'] or 0)
        if discount > 0:
            base_price = float(product['price'])
            final_price = base_price * (1 - discount / 100)
            price_text = (
                f"Цена: <span style='text-decoration: line-through; color: red;'>{product['price']} руб.</span> "
                f"<span style='color: black; font-weight: bold;'>{final_price:.2f} руб.</span>")
        else:
            price_text = f"Цена: {product['price']} руб."

        # Проверка наличия на складе
        d = db()
        d.cursor.execute("SELECT SUM(stock_qty) AS total_stock FROM product_variants WHERE product_id = %s",
                         (product['product_id'],))
        res = d.cursor.fetchone()
        total_stock = res['total_stock'] if res and res['total_stock'] is not None else 0

        # Установка цвета фона карточки
        frame.setObjectName("productCard")
        if total_stock == 0:
            frame.setStyleSheet("QFrame#productCard { background-color: #87CEEB; } QLabel { background: transparent; }")
        elif discount > 15:
            frame.setStyleSheet("QFrame#productCard { background-color: #2E8B57; } QLabel { background: transparent; }")

        info_label = QLabel()
        info_label.setText(
            f"<b>{product['name']}</b> | {product['sku']}<br>"
            f"Описание: {product['description']}<br>"
            f"{price_text}<br>"
        )
        layout.addWidget(info_label)

        disc = QLabel(f"Скидка: \n   {product['discount']}%")
        disc.setFixedSize(80, 80)
        layout.addWidget(disc)

        self.add_card_extra(layout, product)
        self.ui.verticalLayout_card.addWidget(frame)

    def add_card_extra(self, layout, product):
        pass


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Login()
        self.ui.setupUi(self)
        self.setWindowTitle('Авторизация магазина "Velo Shop"')
        self.setWindowIcon(QIcon('images/icon.png'))
        self.ui.label_name.setText("<span style='font-size: 22px;'><b>Магазин 'Aba'</b></span>")
        self.ui.label_icon.setPixmap(QPixmap('images/icon.png').scaled(50, 50))

        self.ui.pushButton_guest.clicked.connect(self.go_guest)
        self.ui.pushButton_login.clicked.connect(self.handle_login)

    def handle_login(self):
        login = self.ui.lineEdit_login.text()
        password = self.ui.lineEdit_password.text()
        d = db()

        query = """
            SELECT u.*, r.name AS role 
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s AND u.password_hash = %s
        """

        d.cursor.execute(query, (login, password))
        user = d.cursor.fetchone()

        if user:
            if user['role'] == 'client':
                self.main = ClientWindow(user)
            elif user['role'] in ('manager', 'admin'):
                self.main = AdminWindow(user)
            else:
                QMessageBox.warning(self, "Ошибка", "Недостаточно прав")
                return
            self.main.show()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или passwords")

    def go_guest(self):
        self.guest = GuestWindow()
        self.guest.show()
        self.close()


class AdminWindow(BaseWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Окно Администратора")
        self.ui.label_user.setText(f"Пользователь: {user['full_name']} ({user['role']})")

        self.ui.tabWidget.removeTab(2)
        self.ui.groupOrder_2.hide()

        self.ui.pushButton_cancelOrder.setText("Удалить заказ")
        self.ui.pushButton_cancelOrder.clicked.connect(self.delete_order)

        self.load_categories("Все товары")
        self.ui.comboBox_filtr_prod.currentIndexChanged.connect(self.load_data)

        # Настраиваем комбобокс поставщиков для админа напрямую
        self.load_suppliers("Все поставщики")
        self.ui.comboBox_filtr_suppliers.currentIndexChanged.connect(self.load_data)

        self.load_data()
        self.load_orders()

        self.ui.comboBox_new_stat.addItems(["обработка", "отправлено", "доставлено", "возврат"])
        self.ui.pushButton_editStatus.clicked.connect(self.update_order_status)
        self.ui.pushButton_logout.clicked.connect(self.go_back)

        self.ui.lineEdit_search.textChanged.connect(self.load_data)
        self.ui.lineEdit_search.setPlaceholderText("Поиск по названию...")
        self.load_data()

    def load_orders(self):
        d = db()
        query = """SELECT o.order_id, u.full_name, p.name, pv.size,
                          oi.quantity, o.total_amount, o.status, o.order_date
                   FROM orders o
                   JOIN users u ON o.user_id = u.user_id
                   JOIN order_items oi ON o.order_id = oi.order_id
                   JOIN product_variants pv ON oi.variant_id = pv.variant_id
                   JOIN products p ON pv.product_id = p.product_id"""
        d.cursor.execute(query)
        self.fill_table(self.ui.tableWidget_orders, d.cursor.fetchall())

    def update_order_status(self):
        row = self.ui.tableWidget_orders.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ")
            return
        order_id = self.ui.tableWidget_orders.item(row, 0).text()
        new_status = self.ui.comboBox_new_stat.currentText()
        d = db()
        d.cursor.execute("UPDATE orders SET status = %s WHERE order_id = %s", (new_status, order_id))
        d.connect.commit()
        QMessageBox.information(self, "Успех", f"Статус заказа #{order_id} изменён на '{new_status}'")
        self.load_orders()

    def add_card_extra(self, layout, product):
        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(lambda _, p=product: self.delete_product(p))
        btn_delete.setFixedSize(100, 50)
        layout.addWidget(btn_delete)

    def delete_product(self, product):
        reply = QMessageBox.question(self, "Подтверждение удаления", f"Вы уверены, что хотите полностью "
                                                                     f"удалить товар:\n\"{product['name']}\"?",
                                     QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)

        if reply == QMessageBox.StandardButton.Yes:
            d = db()
            try:
                d.cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (product['product_id'],))
                d.cursor.execute("DELETE FROM products WHERE product_id = %s", (product['product_id'],))
                d.connect.commit()

                QMessageBox.information(self, "Успех", f"Товар \"{product['name']}\" успешно удален.")
                self.load_data()

            except Exception as e:
                d.connect.rollback()
                QMessageBox.critical(self, "Ошибка удаления", f"Не удалось удалить товар из базы данных.\n"
                                                              f"Возможно, данный товар уже есть в заказах пользователей.\n\n"
                                                              f"Техническая ошибка: {e}")

    def delete_order(self):
        row = self.ui.tableWidget_orders.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ в таблице для удаления")
            return

        order_id = self.ui.tableWidget_orders.item(row, 0).text()

        reply = QMessageBox.question(self, "Подтверждение удаления", f"Вы уверены, что хотите безвозвратно "
                                                                     f"удалить заказ #{order_id} и все его позиции?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            d = db()
            try:
                d.cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
                d.cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
                d.connect.commit()

                QMessageBox.information(self, "Успех", f"Заказ #{order_id} успешно удален.")
                self.load_orders()

            except Exception as e:
                d.connect.rollback()
                QMessageBox.critical(self, "Ошибка удаления", f"Не удалось удалить заказ из базы данных."
                                                              f"\nТехническая ошибка: {e}")


class ClientWindow(BaseWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.selected_product = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Окно для Клиента")
        self.ui.label_user.setText(f"Пользователь: {user['full_name']}")

        self.ui.tabWidget.removeTab(2)
        self.ui.tabWidget.removeTab(1)

        # Прячем всё лишнее, включая фильтр поставщиков
        for w in (self.ui.pushButton_editStatus, self.ui.comboBox_new_stat,
                  self.ui.label_3, self.ui.comboBox_filtr_prod, self.ui.pushButton_cancelOrder,
                  self.ui.label_2, self.ui.lineEdit_search, self.ui.comboBox_filtr_suppliers):
            w.hide()

        self.load_categories()
        self.load_data()
        self.load_delivery()

        self.ui.comboVariant.currentIndexChanged.connect(self.update_total)
        self.ui.spinQuantity.valueChanged.connect(self.update_total)
        self.ui.comboDelivery.currentIndexChanged.connect(self.update_total)
        self.ui.pushButton_CreateOrder.clicked.connect(self.create_order)
        self.ui.pushButton_logout.clicked.connect(self.go_back)

    def add_card_extra(self, layout, product):
        btn = QPushButton("Выбрать")
        btn.clicked.connect(lambda _, p=product: self.select_product(p))
        btn.setFixedSize(110, 50)
        layout.addWidget(btn)

    def select_product(self, product):
        self.selected_product = product
        self.ui.label_SelectedProduct.setText(f"{product['name']} | {product['sku']}")
        d = db()
        d.cursor.execute("SELECT * FROM product_variants WHERE product_id = %s", (product['product_id'],))
        self.ui.comboVariant.clear()
        for v in d.cursor.fetchall():
            self.ui.comboVariant.addItem(f"{v['size']} / {v['color']} (в наличии: {v['stock_qty']})", v)
        self.update_total()

    def load_delivery(self):
        d = db()
        d.cursor.execute("SELECT * FROM delivery_methods")
        for m in d.cursor.fetchall():
            self.ui.comboDelivery.addItem(f"{m['name']} — {m['cost']} руб. ({m['delivery_days']} дн.)", m)

    def update_total(self):
        if not self.selected_product:
            return
        variant = self.ui.comboVariant.currentData()
        delivery = self.ui.comboDelivery.currentData()
        if not variant or not delivery:
            return
        base_price = float(self.selected_product['price'])
        modifier = float(variant['price_modifier'])
        discount = int(self.selected_product['discount'])
        price_with_modifier = base_price + modifier
        price_with_discount = price_with_modifier * (1 - discount / 100)
        total = price_with_discount * self.ui.spinQuantity.value() + float(delivery['cost'])
        self.ui.label_TotalValue.setText(f"{total:.2f} ₽")

    def create_order(self):
        if not self.selected_product:
            QMessageBox.warning(self, "Ошибка", "Выберите товар")
            return
        address = self.ui.editShippingAddress.text()
        if not address:
            QMessageBox.warning(self, "Ошибка", "Укажите адрес доставки")
            return

        variant = self.ui.comboVariant.currentData()
        delivery = self.ui.comboDelivery.currentData()
        qty = self.ui.spinQuantity.value()

        if qty > variant['stock_qty']:
            if variant['stock_qty'] == 0:
                QMessageBox.warning(self, "Товар закончился", f"К сожалению, выбранного варианта товара нет в наличии.")
            else:
                QMessageBox.warning(self, "Недостаточно на складе",
                                    f"Вы хотите заказать {qty} шт., но в наличии осталось только {variant['stock_qty']} шт.")
            return

        base_price = float(self.selected_product['price'])
        modifier = float(variant['price_modifier'])
        discount = int(self.selected_product['discount'])
        price_with_modifier = base_price + modifier
        price_with_discount = price_with_modifier * (1 - discount / 100)
        total = price_with_discount * qty + float(delivery['cost'])

        d = db()
        try:
            d.cursor.execute("""
                INSERT INTO orders (user_id, total_amount, status, address, delivery_method_id)
                VALUES (%s, %s, 'обработка', %s, %s)""",
                             (self.user['user_id'], total, address, delivery['delivery_method_id']))
            order_id = d.cursor.lastrowid

            d.cursor.execute("""
                INSERT INTO order_items (order_id, variant_id, quantity, price_at_order)
                VALUES (%s, %s, %s, %s)""", (order_id, variant['variant_id'], qty, price_with_discount))

            d.cursor.execute("""
                UPDATE product_variants 
                SET stock_qty = stock_qty - %s 
                WHERE variant_id = %s""", (qty, variant['variant_id']))

            d.connect.commit()

            QMessageBox.information(self, "Успех", f"Заказ оформлен!")
            self.select_product(self.selected_product)

        except Exception as e:
            d.connect.rollback()
            QMessageBox.critical(self, "Ошибка БД", f"Не удалось оформить заказ. Ошибка: {e}")


class GuestWindow(BaseWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('Окно Гостя')
        self.ui.label_user.setText("Пользователь: Гость")

        # Прячем всё лишнее для гостя
        for w in (
        self.ui.groupOrder_2, self.ui.comboBox_filtr_prod, self.ui.lineEdit_search, self.ui.comboBox_filtr_suppliers):
            w.hide()

        self.ui.tabWidget.removeTab(2)
        self.ui.tabWidget.removeTab(1)

        d = db()
        d.cursor.execute('SELECT * FROM products')
        for product in d.cursor.fetchall():
            self.add_card(product)

        self.ui.pushButton_logout.clicked.connect(self.go_back)


if __name__ == "__main__":
    app = QApplication([])
    apply_stylesheet(app, theme='light_purple.xml', invert_secondary=True)
    myFont = QFont('Comic Sans MS')
    myFont.setPointSize(12)
    app.setFont(myFont)
    window = LoginWindow()
    window.show()
    app.exec()
