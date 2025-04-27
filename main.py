# main.py
import sys, os, json, threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMenu, QAction,
    QInputDialog, QMessageBox, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt, QSize, QEvent, QTimer
from PyQt5.QtGui import QMovie
from openai import OpenAI

# ───────────── 自定义事件 ──────────────
class ChatResponseEvent(QEvent):
    EVENT_TYPE = QEvent.registerEventType()
    def __init__(self, response: str, receiver: QWidget):
        super().__init__(self.EVENT_TYPE)
        self.response = response
        self._receiver = receiver
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

    # ---------- 配置 ----------
    def loadConfig(self):
        cfg = "config.json"
        if os.path.exists(cfg):
            self.config = json.load(open(cfg, encoding="utf-8"))
        else:
            self.config = {
                "openai_api_key": "",
                "openai_api_base": "https://api.deepseek.com/v1",
                "pet_prompt": "你是一个可爱的桌面宠物小豆泥，性格活泼开朗，说话方式可爱，喜欢用颜文字和表情。请用简短的语言回答用户的问题。",
                "actions": ["idle", "happy", "sad", "sleep"],
                "model": "deepseek-chat",
                "animation_format": "gif"
            }
            json.dump(self.config, open(cfg, "w", encoding="utf-8"), indent=4, ensure_ascii=False)
        self.client = OpenAI(api_key=self.config["openai_api_key"],
                             base_url=self.config["openai_api_base"])

    # ---------- UI ----------
    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        central = QWidget(self)
        central.setAttribute(Qt.WA_TranslucentBackground, True)
        layout  = QVBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)

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
        # 清理旧资源
        if hasattr(self, "movie"):
            self.movie.stop()
            self.movie.disconnect()
            self.label.setMovie(None)
            self.movie.deleteLater()
            del self.movie
            self.label.clear()
            self.label.update()  # 更新界面
            QApplication.processEvents()  # 处理所有待处理的事件，确保UI更新
            self.label.repaint()  # 强制立即重绘

        # 延迟加载新动画
        QTimer.singleShot(100, self._loadNewGIF)  # 增加延迟时间确保资源完全释放

    def _loadNewGIF(self):
        # 确保透明属性
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.centralWidget().setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setStyleSheet("background: transparent; border: none;")

        # 确保标签是空的
        self.label.clear()
        QApplication.processEvents()  # 处理所有待处理的事件

        fmt = self.config.get("animation_format", "gif")
        gif = f"pic/{self.current_action}.{fmt}"
        
        if not os.path.exists(gif):
            QMessageBox.warning(self, "错误", f"缺少动画文件: {gif}")
            return

        # 创建新动画对象
        self.movie = QMovie(gif)
        self.movie.setCacheMode(QMovie.CacheNone)  # 禁用缓存
        self.movie.setScaledSize(QSize(200, 200))
        self.movie.frameChanged.connect(lambda: self.label.repaint())

        # 显示动画
        self.label.setMovie(self.movie)
        self.movie.start()

    def changeAction(self, act): 
        self.current_action = act
        self.loadGIF()

    # ---------- 右键菜单 ----------
    def contextMenuEvent(self, ev):
        m = QMenu(self); sub = m.addMenu("切换动作")
        for a in self.config["actions"]:
            ac = QAction(a, self)
            ac.triggered.connect(lambda _, x=a: self.changeAction(x))
            sub.addAction(ac)
        m.addAction(QAction("与宠物对话", self, triggered=self.chatWithPet))
        m.addAction(QAction("设置", self, triggered=self.openSettings))
        m.addAction(QAction("退出", self, triggered=self.close))
        m.exec_(ev.globalPos())

    # ---------- 对话 ----------
    def chatWithPet(self):
        txt, ok = QInputDialog.getText(self, "对话", "请输入你想说的话:")
        if ok and txt:
            if not self.config["openai_api_key"]:
                QMessageBox.warning(self, "错误", "请先在设置中配置 API 密钥")
                self.openSettings(); return
            threading.Thread(target=self.processChat, args=(txt,), daemon=True).start()

    def processChat(self, utext):
        try:
            r = self.client.chat.completions.create(
                model=self.config["model"],
                messages=[{"role":"system","content":self.config["pet_prompt"]},
                          {"role":"user","content":utext}]
            )
            rep = r.choices[0].message.content
        except Exception as e:
            rep = f"出错了：{e}"
        QApplication.instance().postEvent(
            QApplication.instance(), ChatResponseEvent(rep, self)
        )

    # ---------- 设置 ----------
    def openSettings(self):
        key, ok = QInputDialog.getText(self, "设置", "请输入 OpenAI API 密钥:",
                                       text=self.config["openai_api_key"])
        if ok:
            self.config["openai_api_key"] = key
            json.dump(self.config, open("config.json","w",encoding="utf-8"), indent=4, ensure_ascii=False)
            self.client = OpenAI(api_key=key, base_url=self.config["openai_api_base"])

    # ---------- 拖拽 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.draggable, self.offset = True, e.pos()
    def mouseMoveEvent(self, e):
        if self.draggable: self.move(self.pos() + e.pos() - self.offset)
    def mouseReleaseEvent(self, _): self.draggable = False


# ───────────── main ──────────────
if __name__ == "__main__":
    app = CustomApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = DesktopPet(); pet.show()
    sys.exit(app.exec_())