"""내 캐릭터 데스크톱 펫 (week-03)

지금은 5단계까지: sheet.png 를 네 칸으로 잘라, 화면 오른쪽 아래에 펫 창을 띄운다.
펫은 마우스로 끌어서 옮길 수 있고, 오른쪽 클릭하면 메뉴가 뜬다.
키를 누를 때마다 앞발로 키보드를 번갈아 누른다. 어떤 키인지는 보지 않고 횟수만 센다.
6단계: 오른쪽 클릭 메뉴에서 투명도(100% · 70% · 40%)를 고를 수 있다.

    python pet.py           펫 창 띄우기
    python pet.py --check   잘린 그림을 check/ 폴더에 저장 (눈으로 확인용)
"""
import sys
from pathlib import Path

from PIL import Image
from pynput import keyboard
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMenu

HERE = Path(__file__).parent
# exe 로 묶으면 그림은 exe 가 실행될 때 풀리는 임시 폴더(sys._MEIPASS)에 있다
ASSETS = Path(getattr(sys, "_MEIPASS", HERE))
SHEET = ASSETS / "art" / "sheet.png"

# 네 칸 이름. sheet.png 의 왼쪽 위 → 오른쪽 위 → 왼쪽 아래 → 오른쪽 아래 순서
FRAME_NAMES = ["1_두발듦", "2_왼발누름", "3_오른발누름", "4_졸기"]
IDLE, LEFT, RIGHT, SLEEP = range(4)

# 투명도가 이 값보다 낮은 점은 흐릿한 얼룩으로 보고 지운다 (0~255)
FAINT = 32

PET_SIZE = 150  # 펫 창 크기 (픽셀)
MARGIN = 8      # 화면 오른쪽·작업 표시줄과 띄우는 간격 (픽셀)
BACK_TO_IDLE_MS = 100  # 키를 뗀 뒤 ① 로 돌아가기까지 (밀리초, 0.1초)
OPACITY_CHOICES = [100, 70, 40]  # 메뉴에서 고르는 투명도 (%), 저장하지 않음


def cut_frames(sheet_path=SHEET):
    """sheet.png 를 2×2 로 잘라 같은 크기의 정사각형 그림 네 장을 돌려준다.

    네 칸 모두 같은 상자로 잘라서, 키보드가 늘 같은 자리에 오게 한다.
    """
    sheet = Image.open(sheet_path).convert("RGBA")
    half = sheet.width // 2
    cells = [
        sheet.crop((x, y, x + half, y + half))
        for y in (0, half)
        for x in (0, half)
    ]

    # 그림 둘레의 거의 안 보이는 흐릿한 점은 지운다 (바탕 화면에 얼룩처럼 보이지 않게)
    for cell in cells:
        alpha = cell.getchannel("A").point(lambda v: 0 if v < FAINT else v)
        cell.putalpha(alpha)

    # 네 칸의 그림이 있는 부분을 모두 감싸는 상자 하나 (빈 여백 잘라내기)
    boxes = [cell.getchannel("A").getbbox() for cell in cells]
    left = min(b[0] for b in boxes)
    top = min(b[1] for b in boxes)
    right = max(b[2] for b in boxes)
    bottom = max(b[3] for b in boxes)

    # 정사각형이 되도록 짧은 쪽을 늘린다 (창이 정사각형이라서)
    side = max(right - left, bottom - top)
    cx = (left + right) // 2
    left, right = cx - side // 2, cx - side // 2 + side
    top = bottom - side

    frames = []
    for cell in cells:
        frame = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        frame.paste(cell.crop((left, top, right, bottom)), (0, 0))
        frames.append(frame)
    return frames


def to_pixmap(frame, size, scale):
    """Pillow 그림을 펫 창에 넣을 QPixmap 으로 바꾼다.

    화면 배율(예: 125%)만큼 크게 줄여 두어야 흐릿하지 않다.
    """
    px = round(size * scale)
    small = frame.resize((px, px), Image.LANCZOS)
    image = QImage(small.tobytes(), px, px, QImage.Format_RGBA8888).copy()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(scale)
    return pixmap


class Pet(QLabel):
    def __init__(self, frames):
        super().__init__()
        # 테두리 없음 + 항상 위 + Tool 창 (작업 표시줄에 안 나옴)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(PET_SIZE, PET_SIZE)

        self.press_count = 0     # 오늘 누른 횟수 (화면에만 보이고 저장하지 않음)
        self.drag_offset = None  # 끄는 중일 때, 마우스와 창 왼쪽 위 사이 거리

        scale = self.screen().devicePixelRatio()
        self.pixmaps = [to_pixmap(f, PET_SIZE, scale) for f in frames]
        self.show_frame(IDLE)
        self.move_to_corner()

        self.next_paw = LEFT  # 다음에 누를 앞발 (② ↔ ③ 번갈아)
        # 키를 뗀 뒤 잠깐 지나면 ① 로 돌아가는 타이머
        self.idle_timer = QTimer(self, singleShot=True, interval=BACK_TO_IDLE_MS)
        self.idle_timer.timeout.connect(lambda: self.show_frame(IDLE))

    def show_frame(self, index):
        self.setPixmap(self.pixmaps[index])

    # --- 키에 맞춰 누르기 ---
    def on_key_down(self):
        self.press_count += 1
        self.idle_timer.stop()
        self.show_frame(self.next_paw)
        self.next_paw = RIGHT if self.next_paw == LEFT else LEFT

    def on_key_up(self):
        self.idle_timer.start()

    def move_to_corner(self):
        # availableGeometry 는 작업 표시줄을 뺀 화면 영역
        area = self.screen().availableGeometry()
        self.move(
            area.right() - PET_SIZE - MARGIN + 1,
            area.bottom() - PET_SIZE - MARGIN + 1,
        )


    # --- 끌어서 옮기기 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None

    # --- 오른쪽 클릭 메뉴 ---
    def build_menu(self):
        menu = QMenu(self)
        count = menu.addAction(f"오늘 누른 횟수: {self.press_count}번")
        count.setEnabled(False)  # 보여 주기만 하는 줄
        menu.addSeparator()

        opacity_menu = menu.addMenu("투명도")
        now = round(self.windowOpacity() * 100)
        for percent in OPACITY_CHOICES:
            action = opacity_menu.addAction(f"{percent}%")
            action.setCheckable(True)
            action.setChecked(percent == now)
            action.triggered.connect(
                lambda _=False, p=percent: self.setWindowOpacity(p / 100)
            )

        menu.addSeparator()
        menu.addAction("끄기", QApplication.quit)
        return menu

    def contextMenuEvent(self, event):
        self.build_menu().exec(event.globalPos())


class KeyCounter(QObject):
    """키를 눌렀다·뗐다는 사실만 펫에게 알려 준다.

    pynput 은 어떤 키인지도 넘겨주지만, 받는 즉시 버린다.
    저장하지도, 화면이나 파일에 찍지도, 어디로 보내지도 않는다.
    """
    key_down = Signal()
    key_up = Signal()

    def start(self):
        # pynput 은 따로 도는 줄(스레드)에서 부르므로, Signal 로 펫 창 쪽에 넘긴다
        self.listener = keyboard.Listener(
            on_press=lambda _: self.key_down.emit(),
            on_release=lambda _: self.key_up.emit(),
        )
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        self.listener.stop()


def save_check_frames():
    out = HERE / "check"
    out.mkdir(exist_ok=True)
    for name, frame in zip(FRAME_NAMES, cut_frames()):
        frame.save(out / f"{name}.png")
        print(f"check/{name}.png  {frame.size[0]}x{frame.size[1]}")


def main():
    app = QApplication(sys.argv)
    pet = Pet(cut_frames())
    keys = KeyCounter()
    keys.key_down.connect(pet.on_key_down)
    keys.key_up.connect(pet.on_key_up)
    keys.start()
    pet.show()
    code = app.exec()
    keys.stop()
    sys.exit(code)


if __name__ == "__main__":
    if "--check" in sys.argv:
        save_check_frames()
    else:
        main()
