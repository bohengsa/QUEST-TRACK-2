"""내 캐릭터 데스크톱 펫 (week-03)

지금은 2단계까지: sheet.png 를 네 칸으로 자른다.
직접 실행하면 잘린 그림을 check/ 폴더에 저장해서 눈으로 확인할 수 있다.
"""
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
SHEET = HERE / "art" / "sheet.png"

# 네 칸 이름. sheet.png 의 왼쪽 위 → 오른쪽 위 → 왼쪽 아래 → 오른쪽 아래 순서
FRAME_NAMES = ["1_두발듦", "2_왼발누름", "3_오른발누름", "4_졸기"]

# 투명도가 이 값보다 낮은 점은 흐릿한 얼룩으로 보고 지운다 (0~255)
FAINT = 32


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


if __name__ == "__main__":
    out = HERE / "check"
    out.mkdir(exist_ok=True)
    for name, frame in zip(FRAME_NAMES, cut_frames()):
        frame.save(out / f"{name}.png")
        print(f"check/{name}.png  {frame.size[0]}x{frame.size[1]}")
