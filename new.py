from db import Database
from ui.login_ui import Ui_Login
from ui.main_window_ui import Ui_MainWindow
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from qt_material import apply_stylesheet
from dialog_ui import Ui_ProductForm


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

        self.ui.pushButton_cancelOrder.setText("Удалить товар")
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

        btn_edit = QPushButton("Редактировать")
        btn_edit.clicked.connect(lambda _, p=product: self.edit_product(p))
        btn_edit.setFixedSize(150, 50)
        layout.addWidget(btn_edit)

    def edit_product(self, product):
        self.edit_win = ProductFormWindow(product)
        self.edit_win.exec()
        self.load_data()


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


from PyQt6.QtWidgets import QDialog, QFileDialog
from PyQt6.QtGui import QPixmap


class ProductFormWindow(QDialog):  # Обязательно QDialog
    def __init__(self, product):
        super().__init__()
        self.ui = Ui_ProductForm()  # Подключаем твой интерфейс
        self.ui.setupUi(self)

        self.setWindowTitle("Простое редактирование")
        self.product = product
        self.image_path = product['image_path']

        # 1. Просто вставляем текущие данные в поля
        self.ui.lineEdit_name.setText(product['name'])
        self.ui.doubleSpinBox_price.setValue(float(product['price']))

        # 2. Кнопки (если выбрала шаблон Dialog with Buttons, там будет buttonBox)
        self.ui.pushButton_photo.clicked.connect(self.change_photo)
        self.ui.pushButton_save.clicked.connect(self.save)

    def change_photo(self):
        # Самая простая загрузка фото без копирования файлов
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать фото")
        if path:
            self.image_path = path
            # Жестко ставим размер 300x200 прямо тут
            self.ui.label_photo.setPixmap(QPixmap(path).scaled(300, 200))

    def save(self):
        d = db()
        # Тупо обновляем только самое важное
        d.cursor.execute("""
            UPDATE products 
            SET name = %s, price = %s, image_path = %s
            WHERE product_id = %s
        """, (self.ui.lineEdit_name.text(),
              self.ui.doubleSpinBox_price.value(),
              self.image_path,
              self.product['product_id']))
        d.connect.commit()
        self.close()  # Закрываем окно, и главное окно само обновится!

class ClientWindow(BaseWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.selected_product = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Окно для Клиента")
        self.ui.label_user.setText(f"Пользователь: {user['full_name']}")

        # Прячем всё лишнее для гостя
        for w in (
                self.ui.groupOrder_2, self.ui.comboBox_filtr_prod, self.ui.lineEdit_search,
                self.ui.comboBox_filtr_suppliers):
            w.hide()

        self.ui.tabWidget.removeTab(2)
        self.ui.tabWidget.removeTab(1)

        d = db()
        d.cursor.execute('SELECT * FROM products')
        for product in d.cursor.fetchall():
            self.add_card(product)

        self.ui.pushButton_logout.clicked.connect(self.go_back)


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
    apply_stylesheet(app, theme='light_pink_500.xml', invert_secondary=True)
    myFont = QFont('Comic Sans MS')
    myFont.setPointSize(12)
    app.setFont(myFont)
    window = LoginWindow()
    window.show()
    app.exec()
