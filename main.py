#!/usr/bin/env python3
# coding: utf-8
"""
DesktopPet —— PyQt5 桌面宠物
• macOS / Apple Silicon / Python 3.8
• 为 PyInstaller 打包加入 rsrc()，自动适配 _MEIPASS
"""

import sys, os, json, threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMenu, QAction,
    QInputDialog, QMessageBox, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt, QSize, QEvent, QTimer
from PyQt5.QtGui import QMovie, QIcon
from openai import OpenAI

# ------------ 打包资源助手 ------------------------------------------
def rsrc(path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, path)
# --------------------------------------------------------------------

# ───────────── 自定义事件 ──────────────
class ChatResponseEvent(QEvent):
    EVENT_TYPE = QEvent.registerEventType()
    def __init__(self, response: str, receiver: QWidget):
        super().__init__(self.EVENT_TYPE)
        self.response, self._receiver = response, receiver
    def receiver(self): return self._receiver


class CustomApplication(QApplication):
    def event(self, ev):
        if ev.type() == ChatResponseEvent.EVENT_TYPE:
            QMessageBox.information(ev.receiver(), "宠物回复", ev.response)
            return True
        return super().event(ev)


# ───────────── 桌面宠物 ──────────────
class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loadConfig()
        self.initUI()
        self.exiting = False

    # ---------- 配置 ----------
    def loadConfig(self):
        cfg = rsrc("config.json")
        if os.path.exists(cfg):
            self.config = json.load(open(cfg, encoding="utf-8"))
        else:
            self.config = {
                "openai_api_key": "",
                "openai_api_base": "https://api.deepseek.com/v1",
                "pet_prompt": "你是一个可爱的桌面宠物小豆泥 …",
                "actions": ["idle", "happy", "sad", "sleep"],
                "model": "deepseek-chat",
                "animation_format": "gif"
            }
            json.dump(self.config, open(cfg, "w", encoding="utf-8"),
                      indent=4, ensure_ascii=False)
        self.client = OpenAI(api_key=self.config["openai_api_key"],
                             base_url=self.config["openai_api_base"])

    # ---------- UI ----------
    def initUI(self):
        # ★ 移除 Qt.Tool，避免失焦后被系统隐藏
        flags = (Qt.FramelessWindowHint |
                 Qt.WindowStaysOnTopHint |     # 始终置顶
                 Qt.WindowDoesNotAcceptFocus)  # 不抢焦点
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        icn_path = rsrc("DesktopPet.icns")
        if os.path.exists(icn_path):
            self.setWindowIcon(QIcon(icn_path))

        central = QWidget(self)
        central.setAttribute(Qt.WA_TranslucentBackground, True)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(central)
        self.label.setStyleSheet("background: transparent; border: none;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setCentralWidget(central)

        self.current_action = "idle"
        self.loadGIF()
        self.resize(200, 200)
        self.draggable, self.offset = False, None

    # ---------- 动画 ----------
    def loadGIF(self):
        if hasattr(self, "movie"):
            self.movie.stop()
            self.label.clear()
            self.movie.deleteLater()

        QTimer.singleShot(100, self._loadNewGIF)

    def _loadNewGIF(self):
        fmt = self.config.get("animation_format", "gif")
        gif = rsrc(f"pic/{self.current_action}.{fmt}")

        if not os.path.exists(gif):
            QMessageBox.warning(self, "错误", f"缺少动画文件: {gif}")
            return

        self.movie = QMovie(gif)
        self.movie.setCacheMode(QMovie.CacheNone)
        self.movie.setScaledSize(QSize(200, 200))
        self.movie.frameChanged.connect(self.updateMask)

        self.label.setMovie(self.movie)
        self.movie.start()
        QTimer.singleShot(0, self.updateMask)

    # ---------- 更新窗口透明遮罩 ----------
    def updateMask(self):
        if not hasattr(self, "movie"):
            return
        pix = self.movie.currentPixmap()
        if not pix.isNull():
            self.setMask(pix.mask())

    def changeAction(self, act):
        self.current_action = act
        self.loadGIF()

    # ---------- 右键菜单 ----------
    def contextMenuEvent(self, ev):
        m = QMenu(self)
        sub = m.addMenu("切换动作")
        for a in self.config["actions"]:
            sub.addAction(QAction(a, self,
                triggered=lambda _, x=a: self.changeAction(x)))
        m.addAction("与宠物对话", self.chatWithPet)
        m.addAction("设置", self.openSettings)
        m.addAction("退出", self.quitApp)
        m.exec_(ev.globalPos())

    # ---------- 退出 ----------
    def quitApp(self):
        self.exiting = True
        self.close()
        QApplication.quit()

    # ---------- 对话 ----------
    def chatWithPet(self):
        txt, ok = QInputDialog.getText(self, "对话", "请输入你想说的话:")
        if ok and txt:
            if not self.config["openai_api_key"]:
                QMessageBox.warning(self, "错误", "请先配置 API 密钥")
                self.openSettings()
                return
            threading.Thread(target=self.processChat, args=(txt,),
                             daemon=True).start()

    def processChat(self, utext):
        try:
            r = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role": "system", "content": self.config["pet_prompt"]},
                          {"role": "user", "content": utext}]
            )
            rep = r.choices[0].message.content
        except Exception as e:
            rep = f"出错了：{e}"
        QApplication.postEvent(QApplication.instance(),
                               ChatResponseEvent(rep, self))

    # ---------- 设置 ----------
    def openSettings(self):
        key, ok = QInputDialog.getText(self, "设置", "请输入 OpenAI API 密钥:",
                                       text=self.config["openai_api_key"])
        if ok:
            self.config["openai_api_key"] = key
            json.dump(self.config, open(rsrc("config.json"), "w",
                                        encoding="utf-8"), indent=4, ensure_ascii=False)
            self.client = OpenAI(api_key=key,
                                 base_url=self.config["openai_api_base"])

    # ---------- 拖拽 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.exiting:
            self.draggable, self.offset = True, e.pos()
    def mouseMoveEvent(self, e):
        if self.draggable:
            self.move(self.pos() + e.pos() - self.offset)
    def mouseReleaseEvent(self, _):
        self.draggable = False


# ───────────── main ──────────────
if __name__ == "__main__":
    app = CustomApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())
