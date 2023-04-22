#!/usr/bin/python3
# -*- coding: UTF-8 -*-
######################################################################
# DMR Callsign/ID Finder using RadioID API: https://radioid.net/api/ #
######################################################################
import sys
import json
import webbrowser
from csv import DictWriter
from os import listdir, remove
from urllib.request import urlopen


from PyQt5.QtCore import (QRegExp, Qt, QUrl, QThread, pyqtSignal, QPointF)
from PyQt5.QtGui import (QColor, QIcon, QRegExpValidator, QCloseEvent,
                         QFont, QPalette, QLinearGradient, QFontDatabase,
                         QPixmap, QGradient)
from PyQt5.QtWidgets import (QMainWindow, QStatusBar, QMenuBar,
                             QGraphicsDropShadowEffect, QMenu, QAction,
                             QActionGroup, QWidget, QVBoxLayout, QGroupBox,
                             QHBoxLayout, QComboBox, QLineEdit, QTableWidget,
                             QPushButton, QFileDialog, QMessageBox, QProgressBar,
                             QTableWidgetItem, QDialog, QApplication, QSplashScreen,
                             QHeaderView, QLabel)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

APP_VERSION = "v1.00"
APP_NAME = "PyRadioID"
APP_TITLE = f"{APP_NAME} {APP_VERSION}"
ICON = "./images/icon.png"
FONTS_DICT = {"Lato": "./font/Lato-Regular.ttf",
              "FreeMono": "./fonts/FreeMono.ttf",
              "Liberation Mono": "./fonts/LiberationMono-Regular.ttf",
              "Noto Mono": "./fonts/NotoMono-Regular.ttf",
              "Quicksand": "./fonts/Quicksand-Regular.ttf"}
FONT_SIZE = 11
BASE_URL = "https://radioid.net/api/"
SHADOW_BLUR = 25
DMR_USER_COMBO_LIST = ["DMR ID of a user",
                       "DMR user callsign",
                       "City",
                       "Country"]
DMR_RPT_COMBO_LIST = ["DMR Repeater ID",
                      "Repeater callsign",
                      "Repeater city",
                      "Repeater country"]
CALLSIGN_REGEXP = QRegExp(r"^[0-9A-Z%]{1,20}$")
ID_REGEXP = QRegExp(r"^[0-9%]{1,7}$")
CITY_REGEXP = QRegExp(r"^[A-Za-z -%]{1,20}$")
COUNTRY_REGEXP = QRegExp(r"^[A-Za-z -%]{1,20}$")
USER_LINK_JSON = "https://radioid.net/static/users.json"
USER_LINK_CSV = "https://radioid.net/static/user.csv"
RPT_LINK_JSON = "https://radioid.net/static/rptrs.json"
DMRID_LINK_DAT = "https://radioid.net/static/dmrid.dat"
QRZ_BASE_URL = "https://www.qrz.com/db/"
GRAY_SHADOW = QColor(40, 40, 40)
DARK_SHADOW = QColor(0, 0, 0)
LIGHT_SHADOW = QColor(150, 150, 150)


def format_combo(combobox):
    for i in range(0, combobox.count()):
        combobox.setItemData(i, Qt.AlignCenter, Qt.TextAlignmentRole)


def open_webbrowser():
    web = WebBrowser("https://radioid.net/")
    web.run()


class MainWindow(QMainWindow):
    """ Main Window """

    def __init__(self, appli, **kwargs):
        super().__init__(**kwargs)

        # ####### Main Window config
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(ICON))
        self.setMouseTracking(True)

        # ####### Variables
        self.app = appli
        self.opacity = 0.00
        self.network_manager = None
        self.about_window = None
        self.parameter_window = None
        self.current_theme = "Light"
        self.lang = "English"
        self.tooltips = False
        self.dl_progressbar = None
        self.downloader = None
        self.qrz = None
        self.reply_dict = dict()

        # ####### StatusBar
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # ####### MenuBar
        self.menubar = QMenuBar(self)
        self.setMenuBar(self.menubar)
        self.shadow_menu = QGraphicsDropShadowEffect()
        self.shadow_menu.setBlurRadius(SHADOW_BLUR)
        self.menubar.setGraphicsEffect(self.shadow_menu)

        self.file_menu = QMenu("Files")
        self.edit_menu = QMenu("Edit")
        self.mode_menu = QMenu("Mode")
        self.about_action = QAction("About")
        self.menubar.addMenu(self.file_menu)
        self.menubar.addMenu(self.edit_menu)
        self.menubar.addMenu(self.mode_menu)
        self.menubar.addAction(self.about_action)
        self.about_action.triggered.connect(self.display_about_win)

        # Actions
        self.parameter_action = QAction("Parameters")
        self.save_as_menu = QMenu("Save results ..")
        self.save_json_action = QAction("in .json")
        self.save_csv_action = QAction("in .csv")
        self.dl_files_menu = QMenu("Download from RadioID ..")
        self.dmrid_dat_action = QAction("dmrid.dat")
        self.rptrs_json_action = QAction("rptrs.json")
        self.users_csv_action = QAction("user.csv")
        self.users_json_action = QAction("users.json")
        self.exit_action = QAction("Exit")

        self.save_json_action.setDisabled(True)
        self.save_csv_action.setDisabled(True)

        self.parameter_action.triggered.connect(self.display_parameter_win)
        self.save_json_action.triggered.connect(self.save_results_json)
        self.save_csv_action.triggered.connect(self.save_results_csv)
        # noinspection PyTypeChecker
        self.exit_action.triggered.connect(self.close)
        self.dmrid_dat_action.triggered.connect(lambda: self.init_download(DMRID_LINK_DAT, "./data_files/dmrid.dat"))
        self.rptrs_json_action.triggered.connect(lambda: self.init_download(RPT_LINK_JSON, "./data_files/rptrs.json"))
        self.users_json_action.triggered.connect(lambda: self.init_download(USER_LINK_JSON, "./data_files/users.json"))
        self.users_csv_action.triggered.connect(lambda: self.init_download(USER_LINK_CSV, "./data_files/user.csv"))

        self.file_menu.addAction(self.parameter_action)
        self.file_menu.addSeparator()
        self.file_menu.addMenu(self.save_as_menu)
        self.save_as_menu.addAction(self.save_json_action)
        self.save_as_menu.addAction(self.save_csv_action)
        self.file_menu.addSeparator()
        self.file_menu.addMenu(self.dl_files_menu)
        self.dl_files_menu.addActions([self.dmrid_dat_action,
                                       self.rptrs_json_action,
                                       self.users_csv_action,
                                       self.users_json_action])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.add_filter_action = QAction("Add filter")
        self.add_filter_action.triggered.connect(self.add_fiter)
        self.remove_filter_action = QAction("Remove filter")
        self.remove_filter_action.triggered.connect(self.remove_filter)
        self.edit_menu.addAction(self.add_filter_action)
        self.edit_menu.addAction(self.remove_filter_action)

        self.remove_filter_action.setDisabled(True)

        self.dmr_user_action = QAction("DMR User")
        self.dmr_rpt_action = QAction("DMR Repeter")
        self.nxdn_user_action = QAction("NXDN User")
        self.cplus_user_action = QAction("C+ User")

        self.dmr_user_action.triggered.connect(self.set_dmr_user_mode)
        self.dmr_rpt_action.triggered.connect(self.set_dmr_rpt_mode)
        self.nxdn_user_action.triggered.connect(self.set_nxdn_user_mode)
        self.cplus_user_action.triggered.connect(self.set_cplus_user_mode)

        self.dmr_user_action.setCheckable(True)
        self.dmr_rpt_action.setCheckable(True)
        self.nxdn_user_action.setCheckable(True)
        self.cplus_user_action.setCheckable(True)
        self.dmr_user_action.setChecked(True)

        self.mode_action_grp = QActionGroup(self.mode_menu)
        self.dmr_user_action.setActionGroup(self.mode_action_grp)
        self.dmr_rpt_action.setActionGroup(self.mode_action_grp)
        self.nxdn_user_action.setActionGroup(self.mode_action_grp)
        self.cplus_user_action.setActionGroup(self.mode_action_grp)

        self.mode_menu.addActions([
            self.dmr_user_action,
            self.dmr_rpt_action,
            self.nxdn_user_action,
            self.cplus_user_action
        ])

        # ####### Central Widget
        self.central_Widget = QWidget()
        self.setCentralWidget(self.central_Widget)

        # ####### Main Layout
        self.main_layout = QVBoxLayout()
        self.central_Widget.setLayout(self.main_layout)

        # ####### Input Layouts
        self.main_input_layout = QVBoxLayout()
        self.main_layout.addLayout(self.main_input_layout)
        # 1
        self.input_1_grp = QGroupBox()
        self.input_1_layout = QHBoxLayout()
        self.input_1_grp.setLayout(self.input_1_layout)
        self.main_input_layout.addWidget(self.input_1_grp)
        self.choice_1_combo = QComboBox()
        self.choice_1_combo.setEditable(True)
        self.choice_1_combo.lineEdit().setReadOnly(True)
        self.choice_1_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.choice_1_combo.addItems(DMR_USER_COMBO_LIST)
        self.choice_1_combo.setMinimumWidth(250)
        self.choice_1_combo.activated.connect(lambda e: self.set_regexp(self.entry_1, "1"))
        format_combo(self.choice_1_combo)
        self.entry_1 = QLineEdit()
        self.entry_1.setMinimumWidth(250)
        self.entry_1.setValidator(QRegExpValidator(ID_REGEXP))
        self.entry_1.setAlignment(Qt.AlignCenter)
        self.entry_1.setPlaceholderText("ID")
        self.entry_1.returnPressed.connect(self.search)
        self.input_1_layout.addWidget(self.choice_1_combo, 1)
        self.input_1_layout.addWidget(self.entry_1, 1)
        self.shadow_1_grp = QGraphicsDropShadowEffect()
        self.shadow_1_grp.setBlurRadius(SHADOW_BLUR)
        self.input_1_grp.setGraphicsEffect(self.shadow_1_grp)
        # 2
        self.input_2_grp = QGroupBox()
        self.input_2_layout = QHBoxLayout()
        self.input_2_grp.setLayout(self.input_2_layout)
        self.main_input_layout.addWidget(self.input_2_grp)
        self.choice_2_combo = QComboBox()
        self.choice_2_combo.setEditable(True)
        self.choice_2_combo.lineEdit().setReadOnly(True)
        self.choice_2_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.choice_2_combo.addItems(DMR_USER_COMBO_LIST)
        self.choice_2_combo.setMinimumWidth(250)
        self.choice_2_combo.activated.connect(lambda e: self.set_regexp(self.entry_2, "2"))
        format_combo(self.choice_2_combo)
        self.entry_2 = QLineEdit()
        self.entry_2.setMinimumWidth(250)
        self.entry_2.setValidator(QRegExpValidator(ID_REGEXP))
        self.entry_2.setAlignment(Qt.AlignCenter)
        self.entry_2.setPlaceholderText("ID")
        self.entry_2.returnPressed.connect(self.search)
        self.input_2_layout.addWidget(self.choice_2_combo, 1)
        self.input_2_layout.addWidget(self.entry_2, 1)
        self.shadow_2_grp = QGraphicsDropShadowEffect()
        self.shadow_2_grp.setBlurRadius(SHADOW_BLUR)
        self.input_2_grp.setGraphicsEffect(self.shadow_2_grp)
        self.input_2_grp.hide()

        # ####### Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                              "State", "Country", "Surname"])
        self.table.setMinimumHeight(380)
        self.main_layout.addWidget(self.table)
        self.shadow_table = QGraphicsDropShadowEffect()
        self.shadow_table.setBlurRadius(SHADOW_BLUR)
        self.table.setGraphicsEffect(self.shadow_table)

        # ###### Right Menu
        self.right_menu = QMenu()
        self.right_click_action = QAction("Search callsign on QRZ.com")
        self.right_menu.addAction(self.right_click_action)

        # Search buttons
        self.search_buttons_layout = QHBoxLayout()
        self.search_api_btn = QPushButton("Search")
        self.search_api_btn.clicked.connect(self.search)
        self.search_buttons_layout.addWidget(self.search_api_btn, 1)
        self.main_layout.addLayout(self.search_buttons_layout, 1)
        self.shadow_api_btn = QGraphicsDropShadowEffect()
        self.shadow_api_btn.setBlurRadius(SHADOW_BLUR)
        self.search_api_btn.setGraphicsEffect(self.shadow_api_btn)

    def save_results_csv(self):
        # noinspection PyTypeChecker
        file_name = QFileDialog.getSaveFileName(self, "CSV file name",
                                                ".", "CSV file (*.csv)")[0]

        if file_name == "":
            return

        if ".csv" not in file_name:
            file_name += ".csv"

        with open(file_name, "w") as file_path:
            if self.dmr_rpt_action.isChecked():
                fieldnames = ["callsign", "id", "city", "state", "country", "frequency"]
            else:
                fieldnames = ["callsign", "id", "city", "state", "country", "surname"]
            writer = DictWriter(file_path, fieldnames=fieldnames)
            writer.writeheader()
            for row in range(0, self.table.rowCount()):
                if self.dmr_rpt_action.isChecked():
                    writer.writerow({'callsign': self.table.item(row, 0).text(),
                                     'id': self.table.item(row, 1).text(),
                                     'city': self.table.item(row, 2).text(),
                                     "state": self.table.item(row, 3).text(),
                                     "country": self.table.item(row, 4).text(),
                                     "frequency": self.table.item(row, 5).text()})
                else:
                    writer.writerow({'callsign': self.table.item(row, 0).text(),
                                     'id': self.table.item(row, 1).text(),
                                     'city': self.table.item(row, 2).text(),
                                     "state": self.table.item(row, 3).text(),
                                     "country": self.table.item(row, 4).text(),
                                     "surname": self.table.item(row, 5).text()})

    def save_results_json(self):
        # noinspection PyTypeChecker
        file_name = QFileDialog.getSaveFileName(self, "JSON file name",
                                                ".", "JSON file (*.json)")[0]

        if file_name == "":
            return

        if ".json" not in file_name:
            file_name += ".json"

        result_dict = dict()
        result_list = list()
        for row in range(0, self.table.rowCount()):
            user_dict = dict()
            user_dict["callsign"] = self.table.item(row, 0).text()
            user_dict["id"] = self.table.item(row, 1).text()
            user_dict["city"] = self.table.item(row, 2).text()
            user_dict["state"] = self.table.item(row, 3).text()
            user_dict["country"] = self.table.item(row, 4).text()
            if self.dmr_rpt_action.isChecked():
                user_dict["frequency"] = self.table.item(row, 5).text()
            else:
                user_dict["surname"] = self.table.item(row, 5).text()

            result_list.append(user_dict)

        result_dict["users"] = result_list

        with open(file_name, "w") as file_path:
            json.dump(result_dict, file_path, indent=4, sort_keys=True, ensure_ascii=False)

    def init_download(self, url, file_name):
        if file_name.replace("./data_files/", "") in listdir("./data_files"):
            dialog = QMessageBox()
            rep = dialog.question(self,
                                  f"Update {file_name.replace('./data_files/', '')}",
                                  f"The file {file_name.replace('./data_files/', '')} is "
                                  f"already in data_files directory.\nWould you like to update it ?",
                                  dialog.Yes | dialog.No)
            if rep == dialog.Yes:
                remove(file_name)
            elif rep == dialog.No:
                return

        self.dl_progressbar = QProgressBar()
        self.statusbar.addWidget(self.dl_progressbar, 1)
        self.downloader = Downloader(url, file_name)
        # noinspection PyUnresolvedReferences
        self.downloader.setTotalProgress.connect(self.dl_progressbar.setMaximum)
        # noinspection PyUnresolvedReferences
        self.downloader.setCurrentProgress.connect(self.dl_progressbar.setValue)
        # noinspection PyUnresolvedReferences
        self.downloader.succeeded.connect(self.download_succeeded)
        self.downloader.finished.connect(lambda: self.download_finished(file_name))
        self.downloader.start()

    def download_succeeded(self):
        self.dl_progressbar.setValue(self.dl_progressbar.maximum())

    def download_finished(self, file_name):
        del self.downloader
        self.statusbar.removeWidget(self.dl_progressbar)
        self.statusbar.showMessage(f"{file_name} downloaded with success")

    def display_parameter_win(self):
        if self.parameter_window is None:
            self.parameter_window = ParameterWindow(self)
            self.parameter_window.show()
            self.parameter_window.resize(self.parameter_window.minimumSizeHint())
        else:
            pass

    def display_about_win(self):
        if self.about_window is None:
            self.about_window = AboutWindow(self)
            self.about_window.show()
            self.about_window.resize(self.about_window.minimumSizeHint())
            self.about_window.setFixedSize(self.about_window.size())
        else:
            pass

    def add_fiter(self):
        if self.input_2_grp.isHidden():
            self.input_2_grp.show()
            self.add_filter_action.setDisabled(True)
            self.remove_filter_action.setEnabled(True)

            combo_list_2 = [self.choice_1_combo.itemText(i) for i in range(self.choice_1_combo.count())]
            combo_list_2.remove(self.choice_1_combo.currentText())
            self.choice_2_combo.clear()
            self.choice_2_combo.addItems(combo_list_2)
            format_combo(self.choice_2_combo)
            self.set_regexp(self.entry_2, "2")

    def remove_filter(self):
        if not self.input_2_grp.isHidden():
            self.input_2_grp.hide()
            self.add_filter_action.setEnabled(True)
            self.remove_filter_action.setDisabled(True)

    def search(self):
        if not self.entry_1.hasAcceptableInput():
            return
        if not self.input_2_grp.isHidden():
            if not self.entry_2.hasAcceptableInput():
                return

        url = self.make_url()
        self.do_request(url)
        self.statusbar.showMessage(f"Requête lancée: {url}")

    def do_request(self, url):
        self.network_manager = QNetworkAccessManager()
        request = QNetworkRequest(QUrl(url))
        self.network_manager.finished.connect(self.display_results)
        self.network_manager.get(request)

    def display_results(self, reply):
        error = reply.error()

        if error == QNetworkReply.NoError:
            rep = reply.readAll()
            self.reply_dict = json.loads(rep.data().decode("ascii"))

            self.table.setRowCount(len(self.reply_dict["results"]))
            i = 0
            for result in range(0, len(self.reply_dict["results"])):
                callsign = self.reply_dict["results"][i]["callsign"]
                dmr_id = self.reply_dict["results"][i]['id']
                city = self.reply_dict["results"][i]["city"].capitalize()
                state = self.reply_dict["results"][i]["state"]
                country = self.reply_dict["results"][i]["country"].capitalize()
                if self.dmr_rpt_action.isChecked():
                    surname = self.reply_dict["results"][i]["frequency"]
                else:
                    surname = self.reply_dict["results"][i]["surname"]

                col_1 = QTableWidgetItem(callsign)
                col_2 = QTableWidgetItem(str(dmr_id))
                col_3 = QTableWidgetItem(city)
                col_4 = QTableWidgetItem(state)
                col_5 = QTableWidgetItem(country)
                col_6 = QTableWidgetItem(surname)

                col_1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                col_1.setTextAlignment(Qt.AlignCenter)
                col_2.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                col_2.setTextAlignment(Qt.AlignCenter)
                col_3.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                col_3.setTextAlignment(Qt.AlignCenter)
                col_4.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                col_4.setTextAlignment(Qt.AlignCenter)
                col_5.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                col_5.setTextAlignment(Qt.AlignCenter)
                col_6.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                col_6.setTextAlignment(Qt.AlignCenter)

                col_1.setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
                col_2.setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
                col_3.setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
                col_4.setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
                col_5.setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)
                col_6.setFlags(Qt.NoItemFlags | Qt.ItemIsEnabled)

                self.table.setItem(i, 0, col_1)
                self.table.setItem(i, 1, col_2)
                self.table.setItem(i, 2, col_3)
                self.table.setItem(i, 3, col_4)
                self.table.setItem(i, 4, col_5)
                self.table.setItem(i, 5, col_6)
                i += 1

            self.statusbar.showMessage(f"Requête OK. Nombre de résultat(s): {len(self.reply_dict['results'])}")
            self.save_json_action.setEnabled(True)
            self.save_csv_action.setEnabled(True)
        else:
            self.statusbar.showMessage(reply.errorString())
            if self.dmr_user_action.isChecked():
                self.table.clear()
                self.table.setRowCount(0)
                self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                                      "State", "Country", "Surname"])
            elif self.dmr_rpt_action.isChecked():
                self.table.clear()
                self.table.setRowCount(0)
                self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                                      "State", "Country", "Frequency"])
            elif self.nxdn_user_action.isChecked():
                self.table.clear()
                self.table.setRowCount(0)
                self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                                      "State", "Country", "Surname"])
            elif self.cplus_user_action.isChecked():
                self.table.clear()
                self.table.setRowCount(0)
                self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                                      "State", "Country", "Surname"])

            self.save_json_action.setDisabled(True)
            self.save_csv_action.setDisabled(True)

    def make_url(self):
        url = BASE_URL
        if self.dmr_user_action.isChecked():
            url += "dmr/user/"
        elif self.dmr_rpt_action.isChecked():
            url += "dmr/repeater/"
        elif self.nxdn_user_action.isChecked():
            url += "nxdn/user/"
        elif self.cplus_user_action.isChecked():
            url += "cplus/user/"

        if self.choice_1_combo.currentText() == "DMR ID of a user" \
                or self.choice_1_combo.currentText() == "DMR Repeater ID":
            url += f"?id={self.entry_1.text()}"
        elif self.choice_1_combo.currentText() == "DMR user callsign" \
                or self.choice_1_combo.currentText() == "Repeater callsign":
            url += f"?callsign={self.entry_1.text()}"
        elif self.choice_1_combo.currentText() == "City" \
                or self.choice_1_combo.currentText() == "Repeater city":
            url += f"?city={self.entry_1.text()}"
        elif self.choice_1_combo.currentText() == "Country" \
                or self.choice_1_combo.currentText() == "Repeater country":
            url += f"?country={self.entry_1.text()}"

        if not self.input_2_grp.isHidden():
            if self.choice_2_combo.currentText() == "DMR ID of a user" \
                    or self.choice_2_combo.currentText() == "DMR Repeater ID":
                url += f"&id={self.entry_2.text()}"
            elif self.choice_2_combo.currentText() == "DMR user callsign" \
                    or self.choice_2_combo.currentText() == "Repeater callsign":
                url += f"&callsign={self.entry_2.text()}"
            elif self.choice_2_combo.currentText() == "City" \
                    or self.choice_2_combo.currentText() == "Repeater city":
                url += f"&city={self.entry_2.text()}"
            elif self.choice_2_combo.currentText() == "Country" \
                    or self.choice_2_combo.currentText() == "Repeater country":
                url += f"&country={self.entry_2.text()}"

        return url

    def set_dmr_user_mode(self):
        self.choice_1_combo.clear()
        self.choice_1_combo.addItems(DMR_USER_COMBO_LIST)
        format_combo(self.choice_1_combo)
        self.entry_1.setPlaceholderText("ID")
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                              "State", "Country", "Surname"])
        self.set_regexp(self.entry_1, "1")
        self.set_regexp(self.entry_2, "2")
        self.save_json_action.setDisabled(True)
        self.save_csv_action.setDisabled(True)

    def set_dmr_rpt_mode(self):
        self.choice_1_combo.clear()
        self.choice_1_combo.addItems(DMR_RPT_COMBO_LIST)
        format_combo(self.choice_1_combo)
        self.entry_1.setPlaceholderText("ID")
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                              "State", "Country", "Frequency"])
        self.set_regexp(self.entry_1, "1")
        self.set_regexp(self.entry_2, "2")
        self.save_json_action.setDisabled(True)
        self.save_csv_action.setDisabled(True)

    def set_nxdn_user_mode(self):
        self.choice_1_combo.clear()
        self.choice_1_combo.addItems(DMR_USER_COMBO_LIST)
        format_combo(self.choice_1_combo)
        self.entry_1.setPlaceholderText("ID")
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                              "State", "Country", "Surname"])
        self.set_regexp(self.entry_1, "1")
        self.set_regexp(self.entry_2, "2")
        self.save_json_action.setDisabled(True)
        self.save_csv_action.setDisabled(True)

    def set_cplus_user_mode(self):
        self.choice_1_combo.clear()
        self.choice_1_combo.addItems(DMR_USER_COMBO_LIST)
        format_combo(self.choice_1_combo)
        self.entry_1.setPlaceholderText("ID")
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(["Callsign", "ID", "City",
                                              "State", "Country", "Surname"])
        self.set_regexp(self.entry_1, "1")
        self.set_regexp(self.entry_2, "2")
        self.save_json_action.setDisabled(True)
        self.save_csv_action.setDisabled(True)

    def set_regexp(self, line_edit, combobox):
        if combobox == "1":
            if self.choice_1_combo.currentText() == "DMR ID of a user" \
                    or self.choice_1_combo.currentText() == "DMR Repeater ID":
                line_edit.setValidator(QRegExpValidator(ID_REGEXP))
                line_edit.setPlaceholderText("ID")
            elif self.choice_1_combo.currentText() == "DMR user callsign" \
                    or self.choice_1_combo.currentText() == "Repeater callsign":
                line_edit.setValidator(QRegExpValidator(CALLSIGN_REGEXP))
                line_edit.setPlaceholderText("CALLSIGN")
            elif self.choice_1_combo.currentText() == "City" \
                    or self.choice_1_combo.currentText() == "Repeater city":
                line_edit.setValidator(QRegExpValidator(CITY_REGEXP))
                line_edit.setPlaceholderText("CITY")
            elif self.choice_1_combo.currentText() == "Country" \
                    or self.choice_1_combo.currentText() == "Repeater country":
                line_edit.setValidator(QRegExpValidator(COUNTRY_REGEXP))
                line_edit.setPlaceholderText("COUNTRY")

            combo_list_2 = [self.choice_1_combo.itemText(i) for i in range(self.choice_1_combo.count())]
            combo_list_2.remove(self.choice_1_combo.currentText())
            self.choice_2_combo.clear()
            self.choice_2_combo.addItems(combo_list_2)
            format_combo(self.choice_2_combo)

            if self.choice_2_combo.currentText() == "DMR ID of a user" \
                    or self.choice_2_combo.currentText() == "DMR Repeater ID":
                self.entry_2.setValidator(QRegExpValidator(ID_REGEXP))
                self.entry_2.setPlaceholderText("ID")
            elif self.choice_2_combo.currentText() == "DMR user callsign" \
                    or self.choice_2_combo.currentText() == "Repeater callsign":
                self.entry_2.setValidator(QRegExpValidator(CALLSIGN_REGEXP))
                self.entry_2.setPlaceholderText("CALLSIGN")
            elif self.choice_2_combo.currentText() == "City" \
                    or self.choice_2_combo.currentText() == "Repeater city":
                self.entry_2.setValidator(QRegExpValidator(CITY_REGEXP))
                self.entry_2.setPlaceholderText("CITY")
            elif self.choice_2_combo.currentText() == "Country" \
                    or self.choice_2_combo.currentText() == "Repeater country":
                self.entry_2.setValidator(QRegExpValidator(COUNTRY_REGEXP))
                self.entry_2.setPlaceholderText("COUNTRY")

        elif combobox == "2":
            if self.choice_2_combo.currentText() == "DMR ID of a user" \
                    or self.choice_2_combo.currentText() == "DMR Repeater ID":
                line_edit.setValidator(QRegExpValidator(ID_REGEXP))
                line_edit.setPlaceholderText("ID")
            elif self.choice_2_combo.currentText() == "DMR user callsign" \
                    or self.choice_2_combo.currentText() == "Repeater callsign":
                line_edit.setValidator(QRegExpValidator(CALLSIGN_REGEXP))
                line_edit.setPlaceholderText("CALLSIGN")
            elif self.choice_2_combo.currentText() == "City" \
                    or self.choice_2_combo.currentText() == "Repeater city":
                line_edit.setValidator(QRegExpValidator(CITY_REGEXP))
                line_edit.setPlaceholderText("CITY")
            elif self.choice_2_combo.currentText() == "Country" \
                    or self.choice_2_combo.currentText() == "Repeater country":
                line_edit.setValidator(QRegExpValidator(COUNTRY_REGEXP))
                line_edit.setPlaceholderText("COUNTRY")

    def closeEvent(self, event):
        """Close event for kill process"""
        dialog = QMessageBox()
        rep = dialog.question(self,
                              "Exit",
                              "Close DMR Callsign Finder ?",
                              dialog.Yes | dialog.No)
        if rep == dialog.Yes:
            pass

        elif rep == dialog.No:
            QCloseEvent.ignore(event)
            return


class Downloader(QThread):

    setTotalProgress = pyqtSignal(int)
    setCurrentProgress = pyqtSignal(int)
    succeeded = pyqtSignal()

    def __init__(self, url, filename):
        super().__init__()
        self._url = url
        self._filename = filename

    def run(self):
        url = self._url
        filename = self._filename
        readBytes = 0
        chunkSize = 1024
        # Open the URL address.
        with urlopen(url) as r:
            # noinspection PyUnresolvedReferences
            self.setTotalProgress.emit(int(r.info()["Content-Length"]))

            with open(filename, "ab") as f:
                while True:
                    chunk = r.read(chunkSize)

                    if chunk is None:
                        continue
                    elif chunk == b"":
                        break

                    f.write(chunk)
                    readBytes += chunkSize
                    # noinspection PyUnresolvedReferences
                    self.setCurrentProgress.emit(readBytes)
        # noinspection PyUnresolvedReferences
        self.succeeded.emit()


class WebBrowser(QThread):
    def __init__(self, url):
        super().__init__()
        self._url = url

    def run(self):
        url = self._url
        webbrowser.open(url)


class AboutWindow(QDialog):
    """ About Window """

    def __init__(self, master, **kwargs):
        super().__init__(**kwargs)

        # ####### Window config
        self.master = master
        self.setModal(True)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setWindowTitle("About")
        self.setWindowIcon(QIcon(ICON))

        self.master.about_action.setDisabled(True)

        # ###### Main Layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.main_grp = QGroupBox()
        self.main_layout.addWidget(self.main_grp)
        self.grp_layout = QVBoxLayout()
        self.main_grp.setLayout(self.grp_layout)

        self.label = QLabelClickable("This script is made with Python3 and the Framework PyQt5.\n"
                                     "It use the RadioID.net API to find records about \n"
                                     "DMR ID/Callsign\n\n"
                                     "https://radioid.net/\n\n")
        # noinspection PyUnresolvedReferences
        self.label.clicked.connect(open_webbrowser)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pixmap_label = QLabel()
        self.pixmap = QPixmap("./images/python3_logo.png")
        self.new_pixmap = self.pixmap.scaledToWidth(300, Qt.SmoothTransformation)
        self.pixmap_label.setPixmap(self.new_pixmap)

        self.grp_layout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)
        self.grp_layout.addWidget(self.pixmap_label, 1, Qt.AlignmentFlag.AlignCenter)

        self.main_grp_shadow = QGraphicsDropShadowEffect()
        self.main_grp_shadow.setBlurRadius(SHADOW_BLUR)
        self.main_grp.setGraphicsEffect(self.main_grp_shadow)
        if self.master.current_theme == "Light":
            self.main_grp_shadow.setColor(LIGHT_SHADOW)
        elif self.master.current_theme == "Gray":
            self.main_grp_shadow.setColor(GRAY_SHADOW)
        elif self.master.current_theme == "Dark":
            self.main_grp_shadow.setColor(DARK_SHADOW)

    def closeEvent(self, event):
        """Close event """
        self.master.about_window = None
        self.master.about_action.setEnabled(True)


class QLabelClickable(QLabel):
    """Clickable QLabel"""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        """Emit a clicked signal if ther is Mouse Press Event"""

        # noinspection PyUnresolvedReferences
        self.clicked.emit()


class ParameterWindow(QDialog):
    """ Parameter Window """

    def __init__(self, master, **kwargs):
        super().__init__(**kwargs)

        # ####### Window config
        self.master = master
        # self.setMinimumSize(350, 100)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setWindowTitle("Parameters")
        self.setWindowIcon(QIcon(ICON))

        self.master.parameter_action.setDisabled(True)

        # ###### Main Layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # ####### Fonts
        self.font_grp = QGroupBox("Fonts")
        self.main_layout.addWidget(self.font_grp, 1)
        self.font_layout = QHBoxLayout()
        self.font_combo = QComboBox()
        self.font_size_combo = QComboBox()
        self.font_layout.addWidget(self.font_combo, 4)
        self.font_layout.addWidget(self.font_size_combo, 1)
        self.font_grp.setLayout(self.font_layout)

        self.font_combo.setEditable(True)
        self.font_combo.lineEdit().setReadOnly(True)
        self.font_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.font_combo.addItems([f for f in FONTS_DICT.keys()])
        self.font_combo.setMinimumWidth(200)
        self.font_combo.activated.connect(self.set_font)
        format_combo(self.font_combo)

        self.font_size_combo.setEditable(True)
        self.font_size_combo.lineEdit().setReadOnly(True)
        self.font_size_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.font_size_combo.addItems([str(s) for s in range(8, 24)])
        self.font_size_combo.setMinimumWidth(70)
        self.font_size_combo.activated.connect(self.set_font)
        format_combo(self.font_size_combo)

        self.font_shadow = QGraphicsDropShadowEffect()
        self.font_shadow.setBlurRadius(SHADOW_BLUR)
        self.font_grp.setGraphicsEffect(self.font_shadow)

        # ####### Theme
        self.theme_lang_layout = QHBoxLayout()
        self.theme_grp = QGroupBox("Theme")
        self.theme_lang_layout.addWidget(self.theme_grp)
        self.main_layout.addLayout(self.theme_lang_layout, 1)
        self.theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_layout.addWidget(self.theme_combo, 1)
        self.theme_grp.setLayout(self.theme_layout)

        self.theme_combo.setEditable(True)
        self.theme_combo.lineEdit().setReadOnly(True)
        self.theme_combo.lineEdit().setAlignment(Qt.AlignCenter)
        self.theme_combo.addItems(["Light", "Gray", "Dark"])
        self.theme_combo.setMinimumWidth(120)
        self.theme_combo.activated.connect(self.set_theme)
        format_combo(self.theme_combo)

        self.theme_shadow = QGraphicsDropShadowEffect()
        self.theme_shadow.setBlurRadius(SHADOW_BLUR)
        self.theme_grp.setGraphicsEffect(self.theme_shadow)

        # ####### Initialisation
        self.font_combo.setCurrentText(self.master.app.font().family())
        self.font_size_combo.setCurrentText(str(self.master.app.font().pointSize()))
        self.theme_combo.setCurrentText(self.master.current_theme)

        self.set_theme()

    def set_font(self):
        self.master.app.setFont(QFont(self.font_combo.currentText(),
                                      int(self.font_size_combo.currentText())))
        self.master.app.processEvents()
        self.master.resize(self.minimumSizeHint())
        self.resize(self.minimumSizeHint())
        self.setFixedSize(self.width(), self.height())

    def set_theme(self):
        palette = QPalette()
        theme = self.theme_combo.currentText()

        if theme == "Gray":
            bg = QLinearGradient(QPointF(0, 0), QPointF(400, 700))
            bg.setColorAt(0.0, QColor(70, 70, 70, 255))
            bg.setColorAt(1.0, QColor(50, 50, 50, 255))

            palette.setBrush(QPalette.Window, QGradient(bg))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)

            palette.setBrush(QPalette.Disabled, QPalette.Window, QGradient(bg))
            palette.setColor(QPalette.Disabled, QPalette.WindowText, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.Base, QColor(25, 25, 25).lighter())
            palette.setColor(QPalette.Disabled, QPalette.AlternateBase, QColor(53, 53, 53).lighter())
            palette.setColor(QPalette.Disabled, QPalette.ToolTipBase, Qt.darkGray)
            palette.setColor(QPalette.Disabled, QPalette.ToolTipText, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.Text, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.Button, QColor(53, 53, 53).lighter())
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Disabled, QPalette.Link, QColor(42, 130, 218).lighter())
            palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(42, 130, 218).lighter())
            palette.setColor(QPalette.Disabled, QPalette.HighlightedText, Qt.darkGray)

            self.font_shadow.setColor(GRAY_SHADOW)
            self.theme_shadow.setColor(GRAY_SHADOW)
            self.master.shadow_menu.setColor(GRAY_SHADOW)
            self.master.shadow_1_grp.setColor(GRAY_SHADOW)
            self.master.shadow_2_grp.setColor(GRAY_SHADOW)
            self.master.shadow_table.setColor(GRAY_SHADOW)
            self.master.shadow_api_btn.setColor(GRAY_SHADOW)

            self.master.current_theme = theme

        elif theme == "Dark":
            bg = QLinearGradient(QPointF(0, 0), QPointF(400, 700))
            bg.setColorAt(0.0, QColor(0, 0, 0, 255))
            bg.setColorAt(1.0, QColor(0, 0, 0, 255))

            palette.setBrush(QPalette.Window, QGradient(bg))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(35, 35, 35))
            palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
            palette.setColor(QPalette.ToolTipBase, Qt.black)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(35, 35, 35))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)

            palette.setBrush(QPalette.Disabled, QPalette.Window, QGradient(bg))
            palette.setColor(QPalette.Disabled, QPalette.WindowText, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.Base, QColor(40, 40, 40).lighter())
            palette.setColor(QPalette.Disabled, QPalette.AlternateBase, QColor(40, 40, 40).lighter())
            palette.setColor(QPalette.Disabled, QPalette.ToolTipBase, Qt.darkGray)
            palette.setColor(QPalette.Disabled, QPalette.ToolTipText, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.Text, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.Button, QColor(35, 35, 35).lighter())
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.gray)
            palette.setColor(QPalette.Disabled, QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Disabled, QPalette.Link, QColor(42, 130, 218).lighter())
            palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(42, 130, 218).lighter())
            palette.setColor(QPalette.Disabled, QPalette.HighlightedText, Qt.darkGray)

            self.font_shadow.setColor(DARK_SHADOW)
            self.theme_shadow.setColor(DARK_SHADOW)
            self.master.shadow_menu.setColor(DARK_SHADOW)
            self.master.shadow_1_grp.setColor(DARK_SHADOW)
            self.master.shadow_2_grp.setColor(DARK_SHADOW)
            self.master.shadow_table.setColor(DARK_SHADOW)
            self.master.shadow_api_btn.setColor(DARK_SHADOW)

            self.master.current_theme = theme

        elif theme == "Light":
            self.font_shadow.setColor(LIGHT_SHADOW)
            self.theme_shadow.setColor(LIGHT_SHADOW)
            self.master.shadow_menu.setColor(LIGHT_SHADOW)
            self.master.shadow_1_grp.setColor(LIGHT_SHADOW)
            self.master.shadow_2_grp.setColor(LIGHT_SHADOW)
            self.master.shadow_table.setColor(LIGHT_SHADOW)
            self.master.shadow_api_btn.setColor(LIGHT_SHADOW)

            self.master.current_theme = theme

        self.master.app.setPalette(palette)

    def closeEvent(self, event):
        """Close event """
        self.master.parameter_window = None
        self.master.parameter_action.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Font
    for font in FONTS_DICT.values():
        # noinspection PyArgumentList
        QFontDatabase.addApplicationFont(font)
    app.setFont(QFont("Lato", FONT_SIZE))

    # Splash Screen
    splash = QSplashScreen(QPixmap(ICON))
    splash.show()
    splash.showMessage(APP_NAME, Qt.AlignmentFlag.AlignHCenter |
                       Qt.AlignmentFlag.AlignBottom, Qt.GlobalColor.black)

    app.processEvents()
    window = MainWindow(app)
    splash.finish(window)
    window.show()
    window.resize(window.minimumSizeHint())
    sys.exit(app.exec_())
