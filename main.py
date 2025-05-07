#!/usr/bin/env python3
# coding: utf-8
"""
DesktopPet —— PyQt5 桌面宠物
• macOS / Apple Silicon / Python 3.8
"""

import sys, os, json, threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMenu, QAction, QVBoxLayout, QWidget,
    QMessageBox, QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QLineEdit
)
from PyQt5.QtCore import Qt, QSize, QEvent, QTimer
from PyQt5.QtGui import QMovie, QIcon
from openai import OpenAI


# ------------ 打包资源助手 ------------------------------------------
def rsrc(path: str) -> str:
    """在开发环境或 PyInstaller 打包后都可获得资源绝对路径"""
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


# ───────────── 设置对话框 ──────────────
class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 设置")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.ed_key   = QLineEdit(cfg.get("openai_api_key", ""))
        self.ed_base  = QLineEdit(cfg.get("openai_api_base", ""))
        self.ed_model = QLineEdit(cfg.get("model", ""))

        form = QFormLayout()
        form.addRow("API Key:",  self.ed_key)
        form.addRow("API Base:", self.ed_base)
        form.addRow("Model:",    self.ed_model)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(btns)

    def values(self):
        return self.ed_key.text().strip(), self.ed_base.text().strip(), self.ed_model.text().strip()


# ───────────── 桌面宠物 ──────────────
class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        self.loadConfig()
        self.initUI()
        self.exiting = False

    # ---------- 配置 ----------
    def loadConfig(self):
        cfg_path = rsrc("config.json")
        if os.path.exists(cfg_path):
            self.config = json.load(open(cfg_path, encoding="utf-8"))
        else:
            self.config = {
                "openai_api_key": "",
                "openai_api_base": "https://api.deepseek.com/v1",
                "pet_prompt": "你是一个可爱的桌面宠物小豆泥，性格活泼开朗，说话方式可爱。",
                "actions": ["idle"],
                "model": "deepseek-chat",
                "animation_format": "gif"
            }
            json.dump(self.config, open(cfg_path, "w", encoding="utf-8"),
                      indent=4, ensure_ascii=False)

        # **自动扫描 pic 目录，收集所有 gif 动作为 actions**
        self.config["actions"] = self.discoverActions()

        self.client = OpenAI(
            api_key=self.config.get("openai_api_key", ""),
            base_url=self.config.get("openai_api_base", "")
        )

    def discoverActions(self):
        """扫描 pic 文件夹中所有动画文件，返回动作列表"""
        pic_dir = rsrc("pic")
        fmt = self.config.get("animation_format", "gif")
        if not os.path.isdir(pic_dir):
            return self.config.get("actions", [])
        acts = sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(pic_dir)
            if f.lower().endswith(f".{fmt.lower()}")
        )
        return acts or self.config.get("actions", [])

    # ---------- UI ----------
    def initUI(self):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        icon_path = rsrc("DesktopPet.icns")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget(self)
        central.setAttribute(Qt.WA_TranslucentBackground, True)
        lay = QVBoxLayout(central); lay.setContentsMargins(0,0,0,0)
        self.label = QLabel(central); self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:transparent;border:none;")
        lay.addWidget(self.label)
        self.setCentralWidget(central)

        self.current_action = "idle" if "idle" in self.config["actions"] else self.config["actions"][0]
        self.loadGIF()
        self.resize(200,200)
        self.draggable = False

    # ---------- 动画 ----------
    def loadGIF(self):
        if hasattr(self,"movie"):
            self.movie.stop(); self.label.clear(); self.movie.deleteLater()
        QTimer.singleShot(0, self._loadNewGIF)

    def _loadNewGIF(self):
        gif = rsrc(f"pic/{self.current_action}.{self.config.get('animation_format','gif')}")
        if not os.path.exists(gif):
            QMessageBox.warning(self,"错误",f"缺少动画文件: {gif}")
            return
        self.movie = QMovie(gif); self.movie.setScaledSize(QSize(200,200))
        self.movie.frameChanged.connect(self.updateMask)
        self.label.setMovie(self.movie); self.movie.start()
        self.updateMask()

    def updateMask(self):
        if hasattr(self,"movie"):
            pix = self.movie.currentPixmap()
            if not pix.isNull(): self.setMask(pix.mask())

    # ---------- 菜单 ----------
    def contextMenuEvent(self, ev):
        m = QMenu(self)
        sub = m.addMenu("切换动作")
        for a in self.config["actions"]:
            sub.addAction(QAction(a,self,triggered=lambda _,x=a:self.setAction(x)))
        m.addAction("与宠物对话", self.chatWithPet)
        m.addAction("设置", self.openSettings)
        m.addAction("退出", self.quitApp)
        m.exec_(ev.globalPos())

    def setAction(self, act):
        if act != self.current_action:
            self.current_action = act
            self.loadGIF()

    # ---------- 退出 ----------
    def quitApp(self):
        self.exiting=True
        self.close()
        QApplication.quit()

    # ---------- 对话 ----------
    def chatWithPet(self):
        txt, ok = QInputDialog.getText(self,"对话","请输入你想说的话:")
        if ok and txt:
            if not self.config["openai_api_key"]:
                QMessageBox.warning(self,"错误","请先配置 API 设置")
                self.openSettings()
                return
            threading.Thread(target=self._chat, args=(txt,), daemon=True).start()

    def _chat(self, msg):
        try:
            res = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role":"system","content":self.config["pet_prompt"]},
                          {"role":"user","content":msg}]
            )
            rep = res.choices[0].message.content
        except Exception as e:
            rep = f"出错了：{e}"
        QApplication.postEvent(QApplication.instance(), ChatResponseEvent(rep,self))

    # ---------- 设置 ----------
    def openSettings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        key, base, model = dlg.values()
        if key:   self.config["openai_api_key"]  = key
        if base:  self.config["openai_api_base"] = base
        if model: self.config["model"]           = model

        json.dump(self.config, open(rsrc("config.json"),"w",encoding="utf-8"),
                  indent=4, ensure_ascii=False)
        self.client = OpenAI(api_key=self.config["openai_api_key"],
                             base_url=self.config["openai_api_base"])
        QMessageBox.information(self,"提示","配置信息已更新！")

    # ---------- 拖拽 ----------
    def mousePressEvent(self,e):
        if e.button()==Qt.LeftButton and not self.exiting:
            self.draggable=True
            self.offset=e.pos()
    def mouseMoveEvent(self,e):
        if self.draggable:
            self.move(self.pos()+e.pos()-self.offset)
    def mouseReleaseEvent(self,_):
        self.draggable=False


# ───────────── main ──────────────
if __name__=="__main__":
    app = CustomApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())
