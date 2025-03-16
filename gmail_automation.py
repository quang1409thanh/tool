import sys
import random
import time
import logging
from datetime import datetime
from unidecode import unidecode
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit, 
                            QGroupBox, QFormLayout, QSpinBox, QCheckBox, QProgressBar,
                            QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
import traceback

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='gmail_creator.log'
)
logger = logging.getLogger('gmail_creator')

class CustomLineEdit(QLineEdit):
    def __init__(self, placeholder="", *args, **kwargs):
        super(CustomLineEdit, self).__init__(*args, **kwargs)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: #f8f8f8;
                selection-background-color: #0078d7;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
                background-color: white;
            }
        """)

class GmailCreatorThread(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str, str)
    
    def __init__(self, config, max_retries=3):
        super().__init__()
        self.config = config
        self.max_retries = max_retries
        self.driver = None
        
    def log_and_update(self, message, level="info"):
        if level == "info":
            logger.info(message)
        elif level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
            
        self.update_signal.emit(message)
        
    def run(self):
        attempts = 0
        success = False
        email = ""
        password = ""
        
        while attempts < self.max_retries and not success:
            attempts += 1
            try:
                self.log_and_update(f"Lần thử {attempts}/{self.max_retries}")
                self.progress_signal.emit(10)
                
                # Khởi tạo trình duyệt
                self.log_and_update("Đang khởi tạo Chrome...")
                chrome_options = ChromeOptions()
                
                if self.config['headless']:
                    chrome_options.add_argument("--headless")
                    
                chrome_options.add_argument("--disable-infobars")
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-extensions")
                
                self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                self.progress_signal.emit(20)
                
                # Bắt đầu quy trình tạo tài khoản
                success, email, password = self.create_gmail_account()
                
                # Nếu thành công thì dừng vòng lặp
                if success:
                    break
                    
            except Exception as e:
                error_message = f"Lỗi: {str(e)}\n{traceback.format_exc()}"
                self.log_and_update(error_message, "error")
                self.progress_signal.emit(0)
                
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                    
        # Gửi kết quả cuối cùng
        self.finished_signal.emit(success, email, password)
    
    def create_gmail_account(self):
        try:
            # Tạo thông tin tài khoản
            first_name, last_name, username, password = self.generate_account_info()
            email = f"{username}@gmail.com"
            
            # Điền form đăng ký
            self.fill_registration_form(first_name, last_name, username, password)
            
            self.log_and_update(f"Tạo Gmail thành công: {email}", "info")
            return True, email, password
            
        except Exception as e:
            self.log_and_update(f"Không thể tạo Gmail: {str(e)}", "error")
            return False, "", ""
    
    def generate_account_info(self):
        self.log_and_update("Đang tạo thông tin tài khoản...")
        
        if self.config['use_predefined']:
            first_name = self.config['first_name']
            last_name = self.config['last_name']
            username = self.config['username']
            password = self.config['password']
        else:
            # Danh sách tên tiếng Việt
            vietnamese_first_names = [
                "Ánh", "An", "Ánh Tuyết", "Bình", "Cẩm", "Châu", "Chi", "Cẩm Linh", "Cường", "Dũng",
                "Diệu", "Em", "Tuấn", "Phát", "Phong", "Gia Bảo", "Hạnh", "Hiếu", "Bích", "Duy",
                "Giang", "Lâm", "Linh", "Long", "Lan", "Lộc", "Minh Thư", "Mạnh", "Mai", "My",
                "Mạnh Dũng", "Ngọc", "Nam", "Như Ý", "Oanh", "Phúc", "Phước", "Phát", "Rạng", "Nhật",
                "Sương", "Sơn", "Suối", "Thiên", "Thành", "Vinh", "Vy", "Vũ", "Văn", "Yên"
            ]

            vietnamese_last_names = [
                "Lê", "Ngô", "Nguyễn", "Đỗ", "Trần", "Phạm", "Bùi", "Đặng", "Vũ", "Lâm",
                "Phan", "Tạ", "Võ", "Mai", "Đinh", "Cao", "Hồ", "Đoàn", "Lý", "Dương",
                "Huỳnh", "Trịnh", "Lương", "Ninh", "Hà", "Quách", "Chu", "Hứa", "Thái", "Phùng"
            ]

            # Chọn ngẫu nhiên tên và họ
            first_name = random.choice(vietnamese_first_names)
            last_name = random.choice(vietnamese_last_names)
            
            # Tạo username và password
            first_name_norm = unidecode(first_name).lower()
            last_name_norm = unidecode(last_name).lower()
            random_number = random.randint(1000, 9999)
            username = f"{first_name_norm}.{last_name_norm}{random_number}"
            
            if self.config['custom_password']:
                password = self.config['password']
            else:
                # Tạo mật khẩu ngẫu nhiên mạnh
                chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+"
                password = ''.join(random.choice(chars) for _ in range(16))
        
        self.log_and_update(f"Thông tin tài khoản: {first_name} {last_name}, {username}@gmail.com")
        return first_name, last_name, username, password
    
    def fill_registration_form(self, first_name, last_name, username, password):
        # Mở trang đăng ký Gmail
        self.log_and_update("Đang mở trang đăng ký Gmail...")
        self.driver.get("https://accounts.google.com/signup/v2/createaccount?flowName=GlifWebSignIn&flowEntry=SignUp")
        self.progress_signal.emit(30)
        
        # Điền họ tên
        self.log_and_update("Đang điền thông tin cá nhân...")
        wait = WebDriverWait(self.driver, 20)
        
        first_name_field = wait.until(EC.visibility_of_element_located((By.NAME, "firstName")))
        last_name_field = self.driver.find_element(By.NAME, "lastName")
        
        first_name_field.clear()
        first_name_field.send_keys(first_name)
        last_name_field.clear()
        last_name_field.send_keys(last_name)
        
        next_button = self.driver.find_element(By.CLASS_NAME, "VfPpkd-LgbsSe")
        next_button.click()
        self.progress_signal.emit(40)
        
        # Điền ngày sinh
        self.log_and_update("Đang điền ngày sinh...")
        day = wait.until(EC.visibility_of_element_located((By.NAME, "day")))
        
        # Lấy ngày sinh từ cấu hình hoặc dùng mặc định
        birth_day = self.config.get('birth_day', "02")
        birth_month = self.config.get('birth_month', "3")
        birth_year = self.config.get('birth_year', "1989")
        
        # Chọn tháng
        month_dropdown = Select(self.driver.find_element(By.ID, "month"))
        month_dropdown.select_by_value(birth_month)
        
        # Điền ngày và năm
        day_field = self.driver.find_element(By.ID, "day")
        day_field.clear()
        day_field.send_keys(birth_day)
        
        year_field = self.driver.find_element(By.ID, "year")
        year_field.clear()
        year_field.send_keys(birth_year)
        
        # Chọn giới tính
        gender_dropdown = Select(self.driver.find_element(By.ID, "gender"))
        gender_dropdown.select_by_value(self.config.get('gender', "1"))
        
        next_button = self.driver.find_element(By.CLASS_NAME, "VfPpkd-LgbsSe")
        next_button.click()
        self.progress_signal.emit(50)
        
        # Tạo email tùy chỉnh
        self.log_and_update("Đang tạo địa chỉ email...")
        time.sleep(2)
        
        if self.driver.find_elements(By.CLASS_NAME, "uxXgMe"):
            create_own_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[jsname='CeL6Qc']")))
            create_own_option.click()
        
        wait.until(EC.element_to_be_clickable((By.NAME, "Username")))
        username_field = self.driver.find_element(By.NAME, "Username")
        username_field.clear()
        username_field.send_keys(username)
        
        next_button = self.driver.find_element(By.CLASS_NAME, "VfPpkd-LgbsSe")
        next_button.click()
        self.progress_signal.emit(60)
        
        # Điền mật khẩu
        self.log_and_update("Đang thiết lập mật khẩu...")
        password_field = wait.until(EC.visibility_of_element_located((By.NAME, "Passwd")))
        password_field.clear()
        password_field.send_keys(password)
        
        # Điền xác nhận mật khẩu
        confirm_passwd_div = self.driver.find_element(By.ID, "confirm-passwd")
        password_confirmation_field = confirm_passwd_div.find_element(By.NAME, "PasswdAgain")
        password_confirmation_field.clear()
        password_confirmation_field.send_keys(password)
        
        next_button = self.driver.find_element(By.CLASS_NAME, "VfPpkd-LgbsSe")
        next_button.click()
        self.progress_signal.emit(70)
        
        # Xử lý số điện thoại nếu cần
        time.sleep(2)
        if self.driver.find_elements(By.ID, "phoneNumberId"):
            self.log_and_update("Đang nhập số điện thoại xác minh...")
            phone_success = self.handle_phone_verification()
            if not phone_success:
                raise Exception("Không thể xác minh số điện thoại sau nhiều lần thử")
        else:
            # Bỏ qua bước số điện thoại và email khôi phục
            self.log_and_update("Đang bỏ qua xác minh điện thoại...")
            skip_buttons = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button span.VfPpkd-vQzf8d")))
            for button in skip_buttons:
                button.click()
                time.sleep(1)
                
        self.progress_signal.emit(80)
        
        # Đồng ý với điều khoản
        self.log_and_update("Đang hoàn tất quá trình đăng ký...")
        try:
            agree_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button span.VfPpkd-vQzf8d")))
            agree_button.click()
            time.sleep(2)
        except Exception as e:
            self.log_and_update(f"Lỗi khi đồng ý điều khoản: {str(e)}", "warning")
            
        # Kiểm tra xem đã tạo tài khoản thành công hay chưa
        self.progress_signal.emit(100)
        
        return username, password
    def handle_phone_verification(self):
        max_phone_attempts = 5
        phone_attempts = 0
        
        while phone_attempts < max_phone_attempts:
            try:
                phone_attempts += 1
                self.log_and_update(f"Thử số điện thoại lần {phone_attempts}/{max_phone_attempts}")
                
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.element_to_be_clickable((By.ID, "phoneNumberId")))
                phonenumber_field = self.driver.find_element(By.ID, "phoneNumberId")
                phonenumber_field.clear()
                
                # Tạo số điện thoại ngẫu nhiên (tùy chỉnh theo định dạng quốc gia)
                country_code = self.config.get('phone_country_code', '+212')
                random_number = str(random.randint(10000000, 99999999))
                phone_number = f"{country_code}6{random_number}"
                
                phonenumber_field.send_keys(phone_number)
                self.log_and_update(f"Đang thử với số điện thoại: {phone_number}")
                
                next_button = self.driver.find_element(By.CLASS_NAME, "VfPpkd-vQzf8d")
                next_button.click()
                time.sleep(2)
                
                # Kiểm tra lỗi
                if not self.driver.find_elements(By.CLASS_NAME, "AfGCob"):
                    self.log_and_update("Xác minh số điện thoại thành công!")
                    return True
                
                self.log_and_update("Số điện thoại không hợp lệ, thử lại...", "warning")
                
            except Exception as e:
                self.log_and_update(f"Lỗi khi xác minh số điện thoại: {str(e)}", "error")
                
        return False


class GmailCreatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.created_accounts = []
        
    def init_ui(self):
        self.setWindowTitle("Gmail Account Creator Tool")
        self.setMinimumSize(900, 700)
        
        # Widget chính và layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Phần cấu hình
        config_group = QGroupBox("Cấu hình")
        config_layout = QVBoxLayout()
        
        # Tab Layout cho các cấu hình khác nhau
        basic_config_layout = QFormLayout()
        
        # Checkbox sử dụng thông tin cá nhân tùy chỉnh
        self.use_predefined_cb = QCheckBox("Sử dụng thông tin tùy chỉnh")
        self.use_predefined_cb.toggled.connect(self.toggle_custom_info)
        basic_config_layout.addRow(self.use_predefined_cb)
        
        # Thông tin cá nhân
        self.first_name_input = CustomLineEdit(placeholder="Tên")
        self.last_name_input = CustomLineEdit(placeholder="Họ")
        self.username_input = CustomLineEdit(placeholder="tên.họ1234")
        
        self.first_name_input.setEnabled(False)
        self.last_name_input.setEnabled(False)
        self.username_input.setEnabled(False)
        
        basic_config_layout.addRow(QLabel("Tên:"), self.first_name_input)
        basic_config_layout.addRow(QLabel("Họ:"), self.last_name_input)
        basic_config_layout.addRow(QLabel("Tên người dùng:"), self.username_input)
        
        # Mật khẩu
        self.custom_password_cb = QCheckBox("Sử dụng mật khẩu tùy chỉnh")
        self.custom_password_cb.toggled.connect(self.toggle_password)
        basic_config_layout.addRow(self.custom_password_cb)
        
        self.password_input = CustomLineEdit(placeholder="Mật khẩu mạnh")
        self.password_input.setEnabled(False)
        basic_config_layout.addRow(QLabel("Mật khẩu:"), self.password_input)
        
        # Ngày sinh
        birth_layout = QHBoxLayout()
        self.day_input = QSpinBox()
        self.day_input.setRange(1, 31)
        self.day_input.setValue(2)
        
        self.month_combo = QComboBox()
        for i in range(1, 13):
            self.month_combo.addItem(f"Tháng {i}", str(i))
        self.month_combo.setCurrentIndex(2)  # Tháng 3
        
        self.year_input = QSpinBox()
        self.year_input.setRange(1950, 2005)
        self.year_input.setValue(1989)
        
        birth_layout.addWidget(self.day_input)
        birth_layout.addWidget(self.month_combo)
        birth_layout.addWidget(self.year_input)
        basic_config_layout.addRow(QLabel("Ngày sinh:"), birth_layout)
        
        # Giới tính
        self.gender_combo = QComboBox()
        self.gender_combo.addItem("Nữ", "1")
        self.gender_combo.addItem("Nam", "2")
        self.gender_combo.addItem("Không muốn nói", "3")
        self.gender_combo.addItem("Tùy chỉnh", "4")
        basic_config_layout.addRow(QLabel("Giới tính:"), self.gender_combo)
        
        # Mã quốc gia điện thoại
        self.phone_code_input = CustomLineEdit("+212")
        basic_config_layout.addRow(QLabel("Mã quốc gia:"), self.phone_code_input)
        
        # Chế độ headless
        self.headless_mode_cb = QCheckBox("Chế độ ẩn trình duyệt")
        basic_config_layout.addRow(self.headless_mode_cb)
        
        # Số lần thử lại
        self.retry_count = QSpinBox()
        self.retry_count.setRange(1, 10)
        self.retry_count.setValue(3)
        basic_config_layout.addRow(QLabel("Số lần thử lại:"), self.retry_count)
        
        # Thêm layout cấu hình cơ bản vào nhóm cấu hình
        config_layout.addLayout(basic_config_layout)
        config_group.setLayout(config_layout)
        
        # Thêm nhóm cấu hình vào layout chính
        main_layout.addWidget(config_group)
        
        # Nút thao tác
        action_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Bắt đầu tạo")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        self.start_button.clicked.connect(self.start_gmail_creation)
        
        self.stop_button = QPushButton("Dừng")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        self.stop_button.clicked.connect(self.stop_gmail_creation)
        self.stop_button.setEnabled(False)
        
        self.save_button = QPushButton("Lưu tài khoản")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.save_button.clicked.connect(self.save_accounts)
        
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.stop_button)
        action_layout.addWidget(self.save_button)
        
        main_layout.addLayout(action_layout)
        
        # Thanh tiến trình
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Khu vực log
        log_group = QGroupBox("Nhật ký")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # Khu vực tài khoản đã tạo
        accounts_group = QGroupBox("Tài khoản đã tạo")
        accounts_layout = QVBoxLayout()
        
        self.accounts_text = QTextEdit()
        self.accounts_text.setReadOnly(True)
        self.accounts_text.setStyleSheet("""
            QTextEdit {
                background-color: #f0f8ff;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
        accounts_layout.addWidget(self.accounts_text)
        
        accounts_group.setLayout(accounts_layout)
        main_layout.addWidget(accounts_group)
        
        # Thiết lập widget chính
        self.setCentralWidget(main_widget)
        
        # Khởi tạo thread worker
        self.worker_thread = None
        
        # Log khởi động
        self.log("Ứng dụng tạo Gmail đã khởi động")
        
    def toggle_custom_info(self, checked):
        self.first_name_input.setEnabled(checked)
        self.last_name_input.setEnabled(checked)
        self.username_input.setEnabled(checked)
    
    def toggle_password(self, checked):
        self.password_input.setEnabled(checked)
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Cuộn xuống dưới cùng
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
        
    def start_gmail_creation(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("Đang có một tác vụ đang chạy, vui lòng dừng lại trước!")
            return
            
        # Lấy dữ liệu cấu hình
        config = {
            'use_predefined': self.use_predefined_cb.isChecked(),
            'first_name': self.first_name_input.text(),
            'last_name': self.last_name_input.text(),
            'username': self.username_input.text(),
            'custom_password': self.custom_password_cb.isChecked(),
            'password': self.password_input.text(),
            'birth_day': str(self.day_input.value()),
            'birth_month': self.month_combo.currentData(),
            'birth_year': str(self.year_input.value()),
            'gender': self.gender_combo.currentData(),
            'phone_country_code': self.phone_code_input.text(),
            'headless': self.headless_mode_cb.isChecked()
        }
        
        # Kiểm tra dữ liệu đầu vào
        if config['use_predefined']:
            if not config['first_name'] or not config['last_name'] or not config['username']:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ thông tin cá nhân tùy chỉnh!")
                return
                
        if config['custom_password'] and not config['password']:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập mật khẩu tùy chỉnh!")
            return
            
        # Cập nhật UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.log("Bắt đầu tạo tài khoản Gmail...")
        
        # Khởi tạo và chạy thread
        self.worker_thread = GmailCreatorThread(config, self.retry_count.value())
        self.worker_thread.update_signal.connect(self.log)
        self.worker_thread.progress_signal.connect(self.progress_bar.setValue)
        self.worker_thread.finished_signal.connect(self.on_creation_finished)
        self.worker_thread.start()
        
def stop_gmail_creation(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.log("Đang dừng tác vụ...")
            self.worker_thread.terminate()
            self.worker_thread.wait()
            self.log("Tác vụ đã bị dừng")
            
            # Cập nhật UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.progress_bar.setValue(0)
    
def on_creation_finished(self, success, email, password):
    self.start_button.setEnabled(True)
    self.stop_button.setEnabled(False)
    
    if success:
        self.log(f"Tạo tài khoản thành công: {email}")
        account_info = f"Email: {email}\nMật khẩu: {password}\n{'='*30}"
        self.accounts_text.append(account_info)
        
        # Lưu thông tin tài khoản
        self.created_accounts.append({
            'email': email,
            'password': password,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # Hiển thị thông báo
        QMessageBox.information(self, "Thành công", f"Đã tạo thành công tài khoản Gmail:\n{email}")
    else:
        self.log("Không thể tạo tài khoản Gmail sau nhiều lần thử")
        QMessageBox.warning(self, "Thất bại", "Không thể tạo tài khoản Gmail sau nhiều lần thử")

def save_accounts(self):
    if not self.created_accounts:
        QMessageBox.information(self, "Thông báo", "Chưa có tài khoản nào được tạo!")
        return
        
    filename, _ = QFileDialog.getSaveFileName(
        self,
        "Lưu danh sách tài khoản",
        f"gmail_accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        "Text Files (*.txt)"
    )
    
    if not filename:
        return
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== DANH SÁCH TÀI KHOẢN GMAIL ===\n\n")
            for account in self.created_accounts:
                f.write(f"Email: {account['email']}\n")
                f.write(f"Mật khẩu: {account['password']}\n")
                f.write(f"Ngày tạo: {account['created_at']}\n")
                f.write("="*30 + "\n")
        
        self.log(f"Đã lưu danh sách tài khoản vào: {filename}")
        QMessageBox.information(self, "Thành công", f"Đã lưu danh sách tài khoản vào:\n{filename}")
    except Exception as e:
        self.log(f"Lỗi khi lưu file: {str(e)}")
        QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {str(e)}")


def main():
    # Cấu hình logging
    log_filename = f"gmail_creator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Sử dụng style Fusion cho giao diện nhất quán
    
    # Thiết lập stylesheet chung
    app.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 15px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: #0078d7;
        }
        
        QLabel {
            font-weight: bold;
        }
        
        QComboBox, QSpinBox {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        
        QComboBox:focus, QSpinBox:focus {
            border: 1px solid #0078d7;
        }
    """)
    
    # Tạo cửa sổ chính
    main_window = GmailCreatorApp()
    main_window.show()
    
    # Chạy ứng dụng
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()