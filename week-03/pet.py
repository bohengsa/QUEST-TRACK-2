"""내 캐릭터 데스크톱 펫 (week-03)

지금은 3단계까지: sheet.png 를 네 칸으로 잘라, 화면 오른쪽 아래에 펫 창을 띄운다.

    python pet.py           펫 창 띄우기
    python pet.py --check   잘린 그림을 check/ 폴더에 저장 (눈으로 확인용)
"""
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

HERE = Path(__file__).parent
SHEET = HERE / "art" / "sheet.png"

# 네 칸 이름. sheet.png 의 왼쪽 위 → 오른쪽 위 → 왼쪽 아래 → 오른쪽 아래 순서
FRAME_NAMES = ["1_두발듦", "2_왼발누름", "3_오른발누름", "4_졸기"]
IDLE, LEFT, RIGHT, SLEEP = range(4)

# 투명도가 이 값보다 낮은 점은 흐릿한 얼룩으로 보고 지운다 (0~255)
FAINT = 32

PET_SIZE = 150  # 펫 창 크기 (픽셀)
MARGIN = 8      # 화면 오른쪽·작업 표시줄과 띄우는 간격 (픽셀)


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

        scale = self.screen().devicePixelRatio()
        self.pixmaps = [to_pixmap(f, PET_SIZE, scale) for f in frames]
        self.show_frame(IDLE)
        self.move_to_corner()

    def show_frame(self, index):
        self.setPixmap(self.pixmaps[index])

    def move_to_corner(self):
        # availableGeometry 는 작업 표시줄을 뺀 화면 영역
        area = self.screen().availableGeometry()
        self.move(
            area.right() - PET_SIZE - MARGIN + 1,
            area.bottom() - PET_SIZE - MARGIN + 1,
        )


def save_check_frames():
    out = HERE / "check"
    out.mkdir(exist_ok=True)
    for name, frame in zip(FRAME_NAMES, cut_frames()):
        frame.save(out / f"{name}.png")
        print(f"check/{name}.png  {frame.size[0]}x{frame.size[1]}")


def main():
    app = QApplication(sys.argv)
    pet = Pet(cut_frames())
    pet.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if "--check" in sys.argv:
        save_check_frames()
    else:
        main()
